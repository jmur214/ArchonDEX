"""intelligence/analyst/eval_harness.py
========================================
A/T-293 — the analyst PREDICTION-RESOLUTION harness (Info-Layer Lane 3).

Makes every claim the LLM analyst emits SCOREABLE, versioned, and immutable — the
accuracy record IS the future promotion evidence (G0/G1), so this harness carries
the program's honesty.

Runs daily post-prices: resolves EXPIRED predictions via their machine resolvers
(the `resolver/v1` spec — see the T-293 outbox), appends resolution records to the
APPEND-ONLY `data/intel/analyst_predictions.jsonl` (never rewritten), and maintains
rolling Brier + calibration-by-decile + per-category breakdowns → a
dashboard-consumable summary JSON.

FAIL-CLOSED LAW: an expired prediction whose data source is missing/unsettled
resolves to `resolvable=False` with a reason — it NEVER gets a fabricated outcome
and NEVER enters the Brier/calibration pool. (Kalshi/FOMC sources land with
B/T-290; until then those resolvers return `resolvable=False:source_absent`. The
price resolvers work today off `data/processed/<SYM>_1d.csv`.)

Resolvers are pure functions over injectable lookups (price/kalshi/fomc) so the
verification suite resolves synthetic predictions against fixtures.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRED_LOG = ROOT / "data" / "intel" / "analyst_predictions.jsonl"
SUMMARY = ROOT / "data" / "intel" / "analyst_eval_summary.json"
NOTES_DIR = ROOT / "data" / "intel" / "analyst_notes"
PROCESSED = ROOT / "data" / "processed"

RESOLVER_TYPES = {"price_above", "relative_return", "dd_exceeds", "event_occurs"}

# ── injectable lookups (defaults hit disk; tests inject fixtures) ──────────────
PriceFn = Callable[[str], Optional[pd.Series]]
EventFn = Callable[[str, str], Optional[str]]   # (source, event_id) -> settled outcome | None


def _disk_price(symbol: str) -> Optional[pd.Series]:
    f = PROCESSED / f"{symbol}_1d.csv"
    if not f.is_file():
        return None
    d = pd.read_csv(f)
    if "Date" not in d.columns or "Close" not in d.columns:
        return None
    s = pd.Series(d["Close"].astype(float).values, index=pd.to_datetime(d["Date"]))
    return s[~s.index.duplicated(keep="last")].sort_index()


def _disk_event(source: str, event_id: str) -> Optional[str]:
    """Kalshi settlement / FOMC decision lookup. Sources land with B/T-290; until
    then returns None (→ fail-closed resolvable=False past by_date). NEVER guesses."""
    return None


# ── validity: the ONE definition E imports for note-validation ─────────────────
def is_resolvable_spec(r: dict) -> tuple[bool, str]:
    """True iff `r` is a fully-specified, resolvable-in-principle resolver/v1 spec.
    E's note_schema calls this and REJECTS predictions that fail (the design
    pressure that keeps every claim falsifiable)."""
    if not isinstance(r, dict) or r.get("type") not in RESOLVER_TYPES:
        return False, f"type not in {sorted(RESOLVER_TYPES)}"
    t = r["type"]
    try:
        if t == "price_above":
            ok = (isinstance(r.get("symbol"), str) and isinstance(r.get("level"), (int, float))
                  and r.get("direction") in ("above", "below") and _is_date(r.get("by_date"))
                  and r.get("mode", "terminal") in ("terminal", "touch"))
            return (ok, "" if ok else "price_above fields")
        if t == "relative_return":
            ok = (isinstance(r.get("symbol_a"), str) and isinstance(r.get("symbol_b"), str)
                  and _is_date(r.get("end_date")) and r.get("op") in ("gt", "lt")
                  and (r.get("start_date") is None or _is_date(r.get("start_date"))))
            return (ok, "" if ok else "relative_return fields")
        if t == "dd_exceeds":
            ok = (isinstance(r.get("symbol"), str) and isinstance(r.get("threshold_pct"), (int, float))
                  and r["threshold_pct"] > 0 and _is_date(r.get("start_date")) and _is_date(r.get("end_date")))
            return (ok, "" if ok else "dd_exceeds fields")
        if t == "event_occurs":
            ok = (r.get("source") in ("kalshi_settlement", "fomc_calendar")
                  and isinstance(r.get("event_id"), str) and isinstance(r.get("predicate"), dict)
                  and _is_date(r.get("by_date")))
            return (ok, "" if ok else "event_occurs fields")
    except Exception as e:  # noqa: BLE001
        return False, f"malformed:{type(e).__name__}"
    return False, "unknown"


def _is_date(x: Any) -> bool:
    if not isinstance(x, str):
        return False
    try:
        pd.Timestamp(x)
        return True
    except Exception:
        return False


# ── resolution ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Resolution:
    resolvable: bool
    outcome: Optional[int]      # 0|1 when resolvable, else None
    resolve_date: str           # the expiry the harness keyed on
    source: str
    detail: str


def _asof(s: pd.Series, d: pd.Timestamp) -> Optional[float]:
    w = s[s.index <= d]
    return float(w.iloc[-1]) if len(w) else None


def _has_thru(s: pd.Series, d: pd.Timestamp) -> bool:
    return len(s) > 0 and s.index.max() >= d


def resolve(resolver: dict, note_date: str, as_of: str,
            price_fn: PriceFn = _disk_price, event_fn: EventFn = _disk_event) -> Optional[Resolution]:
    """Resolve one prediction as-of `as_of`. Returns None if NOT YET EXPIRED (wait);
    a Resolution otherwise (resolvable True with outcome, or False with a reason —
    NEVER a fabricated outcome)."""
    ok, why = is_resolvable_spec(resolver)
    t = resolver.get("type")
    exp = resolver.get("by_date") or resolver.get("end_date") or ""
    if not ok:
        return Resolution(False, None, exp, "validator", f"invalid_resolver:{why}")
    aod, exp_ts = pd.Timestamp(as_of), pd.Timestamp(exp)

    if t == "price_above":
        if aod < exp_ts:
            return None
        s = price_fn(resolver["symbol"])
        if s is None or not _has_thru(s, exp_ts):
            return Resolution(False, None, exp, "price", "source_absent_or_stale")
        lvl, up = resolver["level"], resolver["direction"] == "above"
        if resolver.get("mode", "terminal") == "touch":
            win = s[(s.index > pd.Timestamp(note_date)) & (s.index <= exp_ts)]
            hit = (win >= lvl).any() if up else (win <= lvl).any()
            out = int(bool(hit))
        else:
            close = _asof(s, exp_ts)
            out = int(close >= lvl) if up else int(close <= lvl)
        return Resolution(True, out, exp, "price", f"close_asof={_asof(s, exp_ts)}")

    if t in ("relative_return", "dd_exceeds"):
        if aod < exp_ts:
            return None
        if t == "relative_return":
            sa, sb = price_fn(resolver["symbol_a"]), price_fn(resolver["symbol_b"])
            if sa is None or sb is None or not (_has_thru(sa, exp_ts) and _has_thru(sb, exp_ts)):
                return Resolution(False, None, exp, "price", "source_absent_or_stale")
            start = pd.Timestamp(resolver.get("start_date") or note_date)
            ra = _asof(sa, exp_ts) / _asof(sa, start) - 1
            rb = _asof(sb, exp_ts) / _asof(sb, start) - 1
            m = resolver.get("margin_bps", 0) / 1e4
            out = int((ra - rb) > m) if resolver["op"] == "gt" else int((ra - rb) < m)
            return Resolution(True, out, exp, "price", f"ra-rb={ra - rb:.4f}")
        # dd_exceeds
        s = price_fn(resolver["symbol"])
        if s is None or not _has_thru(s, exp_ts):
            return Resolution(False, None, exp, "price", "source_absent_or_stale")
        win = s[(s.index >= pd.Timestamp(resolver["start_date"])) & (s.index <= exp_ts)]
        if len(win) < 2:
            return Resolution(False, None, exp, "price", "insufficient_window_data")
        dd = float((win / win.cummax() - 1).min()) * -100.0
        return Resolution(True, int(dd >= resolver["threshold_pct"]), exp, "price", f"maxdd={dd:.2f}%")

    if t == "event_occurs":
        settled = event_fn(resolver["source"], resolver["event_id"])
        if settled is None:
            if aod < exp_ts:
                return None                      # not settled yet, still within horizon → wait
            return Resolution(False, None, exp, resolver["source"], "source_absent_or_unsettled")
        pred = resolver["predicate"]
        want = pred.get("settles") or pred.get("action")
        return Resolution(True, int(str(settled) == str(want)), exp, resolver["source"], f"settled={settled}")
    return Resolution(False, None, exp, "validator", "unhandled_type")


# ── driver: notes -> resolutions -> append-only log -> summary ─────────────────
def _pred_id(note_id: str, i: int, p: dict) -> str:
    return p.get("prediction_id") or f"{note_id}#{i}"


def _load_notes(notes_dir: Path) -> list[dict]:
    out = []
    if not notes_dir.is_dir():
        return out
    for f in sorted(notes_dir.rglob("analyst_note_*.json")):
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            continue
    return out


def _load_log(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


def run(as_of: str, notes: Optional[list[dict]] = None, *, price_fn: PriceFn = _disk_price,
        event_fn: EventFn = _disk_event, pred_log: Path = PRED_LOG, summary: Path = SUMMARY,
        notes_dir: Path = NOTES_DIR) -> dict:
    """Resolve every EXPIRED, not-yet-logged prediction as-of `as_of`; append records
    (idempotent — a prediction_id already in the log is never re-resolved); rewrite
    the summary. Returns the summary dict."""
    notes = notes if notes is not None else _load_notes(notes_dir)
    logged = {r["prediction_id"] for r in _load_log(pred_log)}
    new_records = []
    for note in notes:
        nid = note.get("note_id") or note.get("note_date", "?")
        for i, p in enumerate(note.get("predictions", [])):
            pid = _pred_id(nid, i, p)
            if pid in logged:
                continue                          # idempotent: never double-resolve
            res = resolve(p["resolver"], note.get("note_date", ""), as_of, price_fn, event_fn)
            if res is None:
                continue                          # not yet expired — resolve on a later run
            rec = {
                "prediction_id": pid, "note_id": nid, "note_date": note.get("note_date", ""),
                "model_id": note.get("model_id", ""), "prompt_version": note.get("prompt_version", ""),
                "category": p.get("category") or p["resolver"].get("type"),
                "statement": p.get("statement", ""), "probability": p.get("probability"),
                "resolver": p["resolver"], "resolve_date": res.resolve_date, "resolved_at": as_of,
                "outcome": res.outcome, "resolvable": res.resolvable,
                "resolve_source": res.source, "resolve_detail": res.detail,
            }
            new_records.append(rec)
            logged.add(pid)
    if new_records:
        pred_log.parent.mkdir(parents=True, exist_ok=True)
        with pred_log.open("a") as fh:            # APPEND-ONLY, never rewritten
            for r in new_records:
                fh.write(json.dumps(r) + "\n")
    summ = summarize(_load_log(pred_log))
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps(summ, indent=2))
    return summ


# ── scoring ───────────────────────────────────────────────────────────────────
def _brier(recs: list[dict]) -> Optional[float]:
    scored = [(r["probability"], r["outcome"]) for r in recs
              if r.get("resolvable") and r.get("probability") is not None and r.get("outcome") is not None]
    if not scored:
        return None
    return round(sum((p - o) ** 2 for p, o in scored) / len(scored), 6)


def _calibration_deciles(recs: list[dict]) -> list[dict]:
    out = []
    for lo in [i / 10 for i in range(10)]:
        hi = lo + 0.1
        b = [(r["probability"], r["outcome"]) for r in recs
             if r.get("resolvable") and r.get("probability") is not None
             and (lo <= r["probability"] < hi or (hi == 1.0 and r["probability"] == 1.0))]
        if b:
            out.append({"bin": f"[{lo:.1f},{hi:.1f})", "n": len(b),
                        "mean_pred": round(sum(p for p, _ in b) / len(b), 4),
                        "mean_obs": round(sum(o for _, o in b) / len(b), 4)})
    return out


def summarize(recs: list[dict]) -> dict:
    resolvable = [r for r in recs if r.get("resolvable")]
    cats = sorted({r.get("category") for r in resolvable})
    by_cat = {c: {"n": sum(1 for r in resolvable if r.get("category") == c),
                  "brier": _brier([r for r in resolvable if r.get("category") == c])} for c in cats}
    return {
        "n_records": len(recs), "n_resolvable": len(resolvable),
        "n_unresolvable": len(recs) - len(resolvable),
        "brier": _brier(resolvable),
        "base_rate": round(sum(r["outcome"] for r in resolvable) / len(resolvable), 4) if resolvable else None,
        "calibration_deciles": _calibration_deciles(resolvable),
        "by_category": by_cat,
        "unresolvable_reasons": _reason_counts(recs),
    }


def _reason_counts(recs: list[dict]) -> dict:
    from collections import Counter
    return dict(Counter(r.get("resolve_detail", "?") for r in recs if not r.get("resolvable")))


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Analyst prediction-resolution harness (T-293).")
    ap.add_argument("--as-of", required=True, help="resolution date YYYY-MM-DD (post-prices)")
    args = ap.parse_args()
    summ = run(args.as_of)
    print(json.dumps(summ, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
