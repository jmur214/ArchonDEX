"""intelligence/analyst/fleet_scoring.py
=========================================
A/T-323 — the FLEET scoreboard: constrained vs agentic A/B, the P2.6 disagreement
channel, and the one-table fleet summary.

Implements EXACTLY the gates pre-stated in
`docs/Audit/fleet_scoring_gates_t323_2026_07_28.md` — written BEFORE the first
agentic note and BEFORE any disagreement data existed. Thresholds here are frozen
copies of that doc; changing one is a NEW pre-registration, not an edit.

Every source is scored by the SAME machinery (eval_harness) — no source gets a
bespoke metric. Scoring is NOT authorization: the G0/G1 ladder remains the
real-money gate (this module never promotes anything).
"""
from __future__ import annotations

from typing import Any, Optional

from intelligence.analyst.eval_harness import (
    _block_boot_ci_low, _order, _recalibrate_inplace, summarize,
)

# ── frozen thresholds (copies of the pre-stated doc; do NOT tune) ──────────────
MIN_PAIRS_AB = 50            # §1.2 minimum eligible pairs for an A/B verdict
MIN_PAIRS_DISAGREE = 30      # §2.2 Q1 minimum HIGH-divergence pairs
MIN_OBS_VOL = 60             # §2.2 Q2 minimum observations
DIVERGENCE_MID = 0.15        # §2.1 bucket edges
DIVERGENCE_HIGH = 0.35
DRIFT_FLOOR = 0.50           # §1.4 eligible pairs must be >=50% of the smaller pool
MDD_TOLERANCE_PP = 5.0       # §1.3 book clears iff MaxDD <= twin + 5pp


def source_of(rec: dict) -> str:
    """Fleet source id for a resolution record. Explicit `source` wins; else inferred
    from the record's shape (event ledger records carry `event:` categories)."""
    s = rec.get("source") or rec.get("fleet_source")
    if s:
        return str(s)
    if str(rec.get("category", "")).startswith("event:"):
        return "event_interpreter"
    return "analyst_constrained"


def _key(rec: dict) -> Optional[tuple]:
    """§1.1 matched-question key: same resolver type + TARGET + resolution date.
    None when the record can't form a comparable key."""
    r = rec.get("resolver") or {}
    t = r.get("type")
    if not t:
        return None
    target = (r.get("symbol") or r.get("event_id")
              or (f"{r.get('symbol_a')}|{r.get('symbol_b')}" if r.get("symbol_a") else None))
    when = r.get("by_date") or r.get("end_date")
    if not target or not when:
        return None
    return (t, target, when)


def matched_pairs(recs_a: list[dict], recs_b: list[dict]) -> list[tuple[dict, dict]]:
    """§1.1 eligible pairs: same question, BOTH resolvable (fail-closed symmetric)."""
    def index(rs):
        out = {}
        for r in rs:
            if not r.get("resolvable") or r.get("probability") is None or r.get("outcome") is None:
                continue
            k = _key(r)
            if k and k not in out:          # first commitment per question
                out[k] = r
        return out
    ia, ib = index(recs_a), index(recs_b)
    return [(ia[k], ib[k]) for k in sorted(set(ia) & set(ib), key=str)]


def _paired_brier_diff(pairs: list[tuple[dict, dict]], use_recal: bool = False,
                       min_pairs: int = MIN_PAIRS_AB) -> Optional[dict]:
    """Paired Brier differential (A − B) with a BLOCK-BOOTSTRAP CI on the resolve-date-
    ordered differential. Positive diff = B better (B's Brier lower). Gimme exclusion
    applies via the baselines when present."""
    def p(r):
        return r.get("_recal_prob", r["probability"]) if use_recal else r["probability"]
    usable = []
    for a, b in pairs:
        ba, bb_ = a.get("baseline_implied"), b.get("baseline_implied")
        for base in (ba, bb_):                      # §1.2 gimme exclusion
            if base is not None and not (0.1 <= float(base) <= 0.9):
                break
        else:
            usable.append((a, b))
    usable.sort(key=lambda ab: (ab[0].get("resolve_date") or "", str(ab[0].get("prediction_id"))))
    if len(usable) < min_pairs:
        return {"n_pairs": len(usable), "verdict": "INSUFFICIENT",
                "min_required": min_pairs, "clears": False}
    d = [((p(a) - a["outcome"]) ** 2) - ((p(b) - b["outcome"]) ** 2) for a, b in usable]
    mean = sum(d) / len(d)
    ci_low = _block_boot_ci_low(d)
    ci_high = -_block_boot_ci_low([-x for x in d])      # two-sided
    if ci_low > 0:
        verdict = "B_WINS"          # B's Brier lower by a margin excluding zero
    elif ci_high < 0:
        verdict = "A_WINS"
    else:
        verdict = "NO_DIFFERENCE_PROVEN"
    return {"n_pairs": len(usable), "mean_diff_a_minus_b": round(mean, 5),
            "diff_ci_low": round(ci_low, 5), "diff_ci_high": round(ci_high, 5),
            "verdict": verdict, "clears": verdict in ("A_WINS", "B_WINS")}


def ab_constrained_vs_agentic(constrained: list[dict], agentic: list[dict]) -> dict:
    """§1 the A/B. Two-sided; a TIE keeps the constrained source (less surface, less
    cost) — absence of evidence never promotes the more complex system."""
    pairs = matched_pairs(constrained, agentic)
    smaller = min(len([r for r in constrained if r.get("resolvable")]),
                  len([r for r in agentic if r.get("resolvable")]))
    drifted = bool(smaller and len(pairs) < DRIFT_FLOOR * smaller)
    # walk-forward recalibration is fit per SOURCE on its own history (never pooled)
    _recalibrate_inplace(_order(constrained))
    _recalibrate_inplace(_order(agentic))
    raw = _paired_brier_diff(pairs)
    recal = _paired_brier_diff(pairs, use_recal=True)
    verdict = raw.get("verdict")
    if drifted:
        verdict = "INCONCLUSIVE_DRIFTED_SETS"           # §1.4 hard override
    tie_break = ("keep_constrained (tie → less attack surface + cost)"
                 if verdict in ("NO_DIFFERENCE_PROVEN", "INSUFFICIENT", "INCONCLUSIVE_DRIFTED_SETS")
                 else None)
    return {"eligible_pairs": len(pairs), "smaller_pool": smaller,
            "question_set_drifted": drifted, "raw": raw, "recalibrated": recal,
            "verdict": verdict, "tie_break": tie_break,
            "note": "A=constrained, B=agentic; positive mean_diff ⇒ agentic better"}


def book_vs_twin(book: dict) -> Optional[dict]:
    """§1.3 directional: a book clears iff Δwealth ci_low > 0 vs its 60/40 twin AND
    MaxDD ≤ twin + 5pp. `book` carries daily paired returns when available."""
    if not book:
        return None
    d = book.get("daily_excess_vs_twin")              # list[float], book_ret − twin_ret
    ci_low = _block_boot_ci_low(list(d)) if d and len(d) >= 20 else None
    mdd, tmdd = book.get("maxdd_pct"), book.get("twin_maxdd_pct")
    mdd_ok = (mdd is not None and tmdd is not None and abs(mdd) <= abs(tmdd) + MDD_TOLERANCE_PP)
    return {"n_days": book.get("n_days"), "book_nav": book.get("book_nav"),
            "twin_nav": book.get("twin_nav"),
            "delta_vs_twin_ci_low": round(ci_low, 6) if ci_low is not None else None,
            "maxdd_pct": mdd, "twin_maxdd_pct": tmdd, "maxdd_within_tolerance": mdd_ok,
            "clears": bool(ci_low is not None and ci_low > 0 and mdd_ok)}


# ── §2 the disagreement channel (P2.6) ────────────────────────────────────────
def _bucket(div: float) -> str:
    return "LOW" if div < DIVERGENCE_MID else ("MID" if div < DIVERGENCE_HIGH else "HIGH")


def disagreement_channel(model_a: list[dict], model_b: list[dict],
                         realized_abs_move: Optional[dict[str, float]] = None) -> dict:
    """§2 Q1/Q2/Q3, pre-stated. Q1: does a side win systematically on HIGH divergence?
    Q2: is divergence informative of realized volatility? Q3: is the simple ensemble
    better than either? Honest priors (doc): Q1 NULL, Q2 LOW-MED, Q3 MED-HIGH."""
    pairs = matched_pairs(model_a, model_b)
    rows = [{"pair": (a, b), "div": abs(a["probability"] - b["probability"]),
             "bucket": _bucket(abs(a["probability"] - b["probability"]))} for a, b in pairs]
    high = [r["pair"] for r in rows if r["bucket"] == "HIGH"]

    q1 = _paired_brier_diff(high, min_pairs=MIN_PAIRS_DISAGREE)
    q1["prior"] = "NULL (two RLHF models on the same bundle are highly correlated)"

    # Q2 — divergence vs realized |move| (rank correlation, block-bootstrap ci_low)
    q2: dict[str, Any] = {"n": 0, "clears": False, "verdict": "INSUFFICIENT",
                          "prior": "LOW-MEDIUM"}
    if realized_abs_move:
        obs = [(r["div"], realized_abs_move.get(str((r["pair"][0].get("resolver") or {}).get("symbol"))))
               for r in rows]
        obs = [(d, m) for d, m in obs if m is not None]
        if len(obs) >= MIN_OBS_VOL:
            n = len(obs)
            rd = {v: i for i, v in enumerate(sorted(d for d, _ in obs))}
            rm = {v: i for i, v in enumerate(sorted(m for _, m in obs))}
            prod = [(rd[d] - (n - 1) / 2) * (rm[m] - (n - 1) / 2) for d, m in obs]
            ci_low = _block_boot_ci_low(prod)
            q2 = {"n": n, "mean_rank_product": round(sum(prod) / n, 4),
                  "ci_low": round(ci_low, 4), "clears": bool(ci_low > 0),
                  "verdict": "DIVERGENCE_PREDICTS_VOL" if ci_low > 0 else "NULL",
                  "prior": "LOW-MEDIUM"}

    # Q3 — the simple ensemble as a third virtual source
    ens = [{**a, "prediction_id": f"ens::{a.get('prediction_id')}",
            "probability": (a["probability"] + b["probability"]) / 2.0} for a, b in pairs]
    q3 = {"vs_a": _paired_brier_diff([(a, e) for (a, _), e in zip(pairs, ens)]),
          "vs_b": _paired_brier_diff([(b, e) for (_, b), e in zip(pairs, ens)]),
          "prior": "MEDIUM-HIGH (averaging correlated-but-imperfect forecasters usually wins)"}

    return {"n_matched": len(pairs),
            "buckets": {b: sum(1 for r in rows if r["bucket"] == b) for b in ("LOW", "MID", "HIGH")},
            "q1_side_wins_on_disagreement": q1, "q2_divergence_predicts_vol": q2,
            "q3_ensemble": q3}


# ── §3 the fleet table ────────────────────────────────────────────────────────
def fleet_table(records: list[dict], books: Optional[dict[str, dict]] = None,
                note_counts: Optional[dict[str, dict]] = None) -> dict:
    """§3 one table, source × metrics — every source scored by the SAME machinery."""
    books = books or {}
    note_counts = note_counts or {}
    by_src: dict[str, list[dict]] = {}
    for r in records:
        by_src.setdefault(source_of(r), []).append(r)
    table = {}
    for src, recs in sorted(by_src.items()):
        s = summarize(recs)
        nc = note_counts.get(src, {})
        g1 = s.get("g1_skill", {}) or {}
        vs_impl = (g1.get("vs_market_implied") or {})
        table[src] = {
            "notes": nc.get("notes"), "valid_pct": nc.get("valid_pct"),
            "resolved": s.get("n_resolvable"), "unresolvable": s.get("n_unresolvable"),
            "brier_raw": g1.get("brier_raw", s.get("brier")),
            "brier_recalibrated": g1.get("brier_recalibrated"),
            "vs_implied_ci_low": vs_impl.get("diff_ci_low"),
            "book": book_vs_twin(books.get(src)),
        }
    return {"sources": table,
            "posture": "scoring != authorization; the G0/G1 ladder remains the real-money gate"}
