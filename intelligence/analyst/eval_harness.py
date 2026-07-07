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
from dataclasses import dataclass
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


KALSHI_SNAP = ROOT / "data" / "macro_data" / "alt" / "kalshi_kxfed_snapshots.parquet"
FRED_PATH = ROOT / "data" / "macro_data" / "alt" / "fred_rate_path.parquet"
_KALSHI: Optional[pd.DataFrame] = None
_FRED: Optional[pd.DataFrame] = None


def _kalshi() -> Optional[pd.DataFrame]:
    """KXFED snapshots (B/T-290). Cached; None if absent → fail-closed."""
    global _KALSHI
    if _KALSHI is None and KALSHI_SNAP.is_file():
        _KALSHI = pd.read_parquet(KALSHI_SNAP)
    return _KALSHI


def _fred() -> Optional[pd.DataFrame]:
    global _FRED
    if _FRED is None and FRED_PATH.is_file():
        _FRED = pd.read_parquet(FRED_PATH)
    return _FRED


def _naive(x) -> pd.Timestamp:
    """Timestamp with tz dropped (Kalshi expiration_time is tz-aware '...Z')."""
    t = pd.Timestamp(x)
    return t.tz_convert(None) if t.tz is not None else t


def _fred_asof(series: str, d: pd.Timestamp) -> Optional[float]:
    f = _fred()
    if f is None:
        return None
    s = f[(f["series"] == series) & (pd.to_datetime(f["observation_date"]) <= d)]
    return float(s.sort_values("observation_date").iloc[-1]["value"]) if len(s) else None


def _disk_event(source: str, event_id: str) -> Optional[str]:
    """Real settlement (B/T-290). kalshi_settlement: the KXFED strike ticker settles
    via realized FRED DFEDTARU vs the ticker's strike after its expiration.
    fomc_calendar: the meeting's action = sign of the DFEDTARU change across it.
    None (→ fail-closed resolvable=False past by_date) if data absent/unsettled. Never guesses."""
    if source == "kalshi_settlement":
        k = _kalshi()
        if k is None:
            return None
        row = k[k["ticker"] == event_id]
        if not len(row):
            return None
        r = row.iloc[-1]
        exp = r.get("expiration_time")
        strike = r.get("floor_strike")
        if pd.isna(exp) or strike is None or pd.isna(strike):
            return None
        realized = _fred_asof("DFEDTARU", _naive(exp))
        if realized is None:                       # FRED not past expiration → unsettled
            return None
        if r.get("strike_type") == "greater":
            return "yes" if realized > float(strike) else "no"
        return None
    if source == "fomc_calendar":
        d = pd.Timestamp(event_id)
        before = _fred_asof("DFEDTARU", d - pd.Timedelta(days=1))
        after = _fred_asof("DFEDTARU", d + pd.Timedelta(days=7))
        if before is None or after is None:
            return None
        return "cut" if after < before else ("hike" if after > before else "hold")
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


# ── G1 baselines (amended gate: beat market-implied + persistence per category) ──
def market_implied_prob(resolver: dict, note_date: str) -> Optional[float]:
    """Kalshi-implied YES probability for a KXFED `event_occurs` prediction, as of the
    NOTE's input-bundle date (PIT — the store accrues 2026-07-07 forward, so the
    baseline is 'implied prob at note time', no backfill). The market-implied baseline
    the amended G1 requires rate-path claims to beat."""
    if resolver.get("type") != "event_occurs" or resolver.get("source") != "kalshi_settlement":
        return None
    k = _kalshi()
    if k is None:
        return None
    row = k[(k["ticker"] == resolver["event_id"]) & (k["snap_date"].astype(str) == str(note_date))]
    if not len(row):
        return None                                # no PIT snapshot at note date → no baseline
    r = row.iloc[-1]
    yb, ya = r.get("yes_bid"), r.get("yes_ask")
    if pd.notna(yb) and pd.notna(ya):
        return float((float(yb) + float(ya)) / 2)  # yes mid
    lp = r.get("last_price")
    return float(lp) if pd.notna(lp) else None


def persistence_prob(resolver: dict, note_date: str, price_fn: PriceFn = _disk_price) -> Optional[float]:
    """Driftless random-walk P(outcome) for a `price_above` prediction, from the price
    at note_date + trailing-63d vol — a no-skill persistence baseline the model must beat."""
    if resolver.get("type") != "price_above":
        return None
    import math
    from statistics import NormalDist
    s = price_fn(resolver["symbol"])
    if s is None:
        return None
    nd = pd.Timestamp(note_date)
    p0 = _asof(s, nd)
    hist = s[s.index <= nd].pct_change().dropna().tail(63)
    if p0 is None or p0 <= 0 or len(hist) < 20:
        return None
    days = max(1, (pd.Timestamp(resolver["by_date"]) - nd).days)
    sigma = float(hist.std()) * math.sqrt(days)
    if sigma <= 0:
        return None
    z = math.log(resolver["level"] / p0) / sigma
    p_above = 1.0 - NormalDist().cdf(z)
    return p_above if resolver["direction"] == "above" else (1.0 - p_above)


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
                "baseline_implied": market_implied_prob(p["resolver"], note.get("note_date", "")),
                "baseline_persistence": persistence_prob(p["resolver"], note.get("note_date", ""), price_fn),
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


import random as _random

MIN_RECAL_HISTORY = 30   # walk-forward: no recalibration until this much resolved history


def _order(recs: list[dict]) -> list[dict]:
    """Resolvable records in serial (resolve_date) order — the structure the BLOCK
    bootstrap respects (nearby predictions cover overlapping horizons → correlated)."""
    good = [r for r in recs if r.get("resolvable") and r.get("probability") is not None
            and r.get("outcome") is not None]
    return sorted(good, key=lambda r: (r.get("resolve_date") or "", str(r.get("prediction_id") or "")))


def _block_boot_ci_low(d: list[float], seed: int = 0, n_iter: int = 1000) -> float:
    """Circular moving-block bootstrap (Politis-Romano) ci_low of the MEAN of a serial
    series `d`. Block length ~ n**(1/3) (project-standard block bootstrap, NOT iid)."""
    n = len(d)
    L = max(1, round(n ** (1.0 / 3.0)))
    rng = _random.Random(seed)
    nb = -(-n // L)                              # ceil(n/L) blocks
    means = []
    for _ in range(n_iter):
        idx: list[int] = []
        for _ in range(nb):
            st = rng.randrange(0, n)
            idx.extend((st + k) % n for k in range(L))
        idx = idx[:n]
        means.append(sum(d[j] for j in idx) / n)
    means.sort()
    return means[int(0.025 * len(means))]


def _recalibrate_inplace(ordered: list[dict]) -> None:
    """WALK-FORWARD isotonic recalibration: each prediction's recalibrated prob is the
    isotonic map fit on ALL EARLIER resolved predictions applied to it (never in-sample).
    RLHF models hedge to 0.5; recalibrated Brier is the honest discrimination read. Stores
    `_recal_prob` per record (= raw prob until ≥ MIN_RECAL_HISTORY history exists)."""
    from sklearn.isotonic import IsotonicRegression
    for i, r in enumerate(ordered):
        hist = ordered[:i]
        if len(hist) >= MIN_RECAL_HISTORY:
            iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            iso.fit([h["probability"] for h in hist], [h["outcome"] for h in hist])
            r["_recal_prob"] = float(iso.predict([r["probability"]])[0])
        else:
            r["_recal_prob"] = r["probability"]


def _brier_skill(recs: list[dict], baseline: str, use_recal: bool = False) -> Optional[dict]:
    """Model-vs-baseline Brier with a BLOCK-BOOTSTRAP CI on the DIFFERENTIAL (2nd G1
    amendment) + GIMME EXCLUSION (drop near-certain predictions, baseline >0.9/<0.1).
    baseline ∈ {'base_rate','implied','persistence'}. Amended-G1 clears iff the mean
    Brier improvement's `diff_ci_low > 0` — calibration is necessary-not-sufficient, and
    a base-rate hedger cannot pass (vs its own base rate the differential ≈ 0). With
    `use_recal` the model's recalibrated probs are scored (the honest discrimination read)."""
    good = _order(recs)
    def mp(r): return r.get("_recal_prob", r["probability"]) if use_recal else r["probability"]
    if baseline == "base_rate":
        base = sum(r["outcome"] for r in good) / len(good) if good else None
        pool = [(mp(r), base, r["outcome"]) for r in good] if base is not None else []
    else:
        key = f"baseline_{baseline}"
        pool = [(mp(r), float(r[key]), r["outcome"]) for r in good if r.get(key) is not None]
    pool = [(p, b, o) for (p, b, o) in pool if 0.1 <= b <= 0.9]   # gimme exclusion
    if len(pool) < 5:
        return None
    bm = sum((p - o) ** 2 for p, _, o in pool) / len(pool)
    bb = sum((b - o) ** 2 for _, b, o in pool) / len(pool)
    diff = [(b - o) ** 2 - (p - o) ** 2 for (p, b, o) in pool]    # per-pred Brier improvement (>0 = model better)
    mean_diff = sum(diff) / len(diff)
    ci_low = _block_boot_ci_low(diff)
    return {"n": len(pool), "brier_model": round(bm, 5), "brier_baseline": round(bb, 5),
            "skill": round(1 - bm / bb, 4) if bb > 0 else None,
            "mean_brier_diff": round(mean_diff, 5), "diff_ci_low": round(ci_low, 5),
            "clears": bool(ci_low > 0)}


def _g1_block(recs: list[dict]) -> dict:
    ordered = _order(recs)
    _recalibrate_inplace(ordered)
    raw_brier = _brier(ordered)
    recal_brier = (round(sum((r["_recal_prob"] - r["outcome"]) ** 2 for r in ordered) / len(ordered), 5)
                   if ordered else None)
    return {
        "vs_base_rate": _brier_skill(ordered, "base_rate"),
        "vs_market_implied": _brier_skill(ordered, "implied"),
        "vs_persistence": _brier_skill(ordered, "persistence"),
        "brier_raw": raw_brier, "brier_recalibrated": recal_brier,
        "recalibrated": {                                        # honest discrimination read
            "vs_base_rate": _brier_skill(ordered, "base_rate", use_recal=True),
            "vs_market_implied": _brier_skill(ordered, "implied", use_recal=True),
            "vs_persistence": _brier_skill(ordered, "persistence", use_recal=True),
        },
    }


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
        # amended-G1: calibration necessary-not-sufficient; skill = beat market-implied
        # + persistence + base-rate per category at ci_low>0, gimmes excluded.
        "g1_skill": _g1_block(resolvable),
        "g1_skill_by_category": {c: _g1_block([r for r in resolvable if r.get("category") == c]) for c in cats},
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
