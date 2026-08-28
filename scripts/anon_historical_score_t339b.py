"""scripts/anon_historical_score_t339.py — score the frozen T-339 run.

Order matters and is pre-registered: the §5 GATES RUN FIRST and can VOID the run
BEFORE any calibration number is computed or reported.
  (a) leakage holdout >= 5/40 hits  -> VOID
  (b) brilliance tripwire Brier < 0.10 -> suspected leakage -> VOID
Only if both pass do we report the Murphy decomposition + skill vs baselines.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path("/Users/jacksonmurphy/Dev/trading_machine-agent-a")
sys.path.insert(0, str(ROOT))
from intelligence.analyst.eval_harness import _block_boot_ci_low   # noqa: E402

OUT = ROOT / "data" / "research" / "t339b"
LEAKAGE_VOID_AT = 5
BRILLIANCE_VOID_BELOW = 0.10


def murphy(pairs, n_bins: int = 10):
    """BS = reliability - resolution + uncertainty (Murphy 1973).
    reliability LOWER is better (calibration); resolution HIGHER is better
    (discrimination); uncertainty is the SAMPLE's own variance — a property of the
    questions, not the model, reported so an easy sample cannot masquerade as skill."""
    n = len(pairs)
    if n == 0:
        return None
    obar = sum(o for _, o in pairs) / n
    bins = {}
    for p, o in pairs:
        k = min(n_bins - 1, int(p * n_bins))
        bins.setdefault(k, []).append((p, o))
    rel = res = 0.0
    for k, grp in bins.items():
        nk = len(grp)
        pk = sum(p for p, _ in grp) / nk
        ok = sum(o for _, o in grp) / nk
        rel += nk * (pk - ok) ** 2
        res += nk * (ok - obar) ** 2
    rel /= n; res /= n
    unc = obar * (1 - obar)
    bs = sum((p - o) ** 2 for p, o in pairs) / n
    return {"n": n, "brier": round(bs, 5), "reliability": round(rel, 5),
            "resolution": round(res, 5), "uncertainty": round(unc, 5),
            "base_rate": round(obar, 4),
            "decomposition_check": round(rel - res + unc, 5)}


def skill(pairs, baselines, label):
    """Block-bootstrap CI on the per-question Brier DIFFERENTIAL, gimmes excluded."""
    pool = [(p, b, o) for (p, o), b in zip(pairs, baselines)
            if b is not None and 0.1 <= b <= 0.9]
    if len(pool) < 5:
        return {"baseline": label, "n": len(pool), "verdict": "INSUFFICIENT"}
    d = [((b - o) ** 2) - ((p - o) ** 2) for p, b, o in pool]
    mean = sum(d) / len(d)
    ci = _block_boot_ci_low(d)
    return {"baseline": label, "n": len(pool), "mean_brier_improvement": round(mean, 5),
            "diff_ci_low": round(ci, 5), "beats_baseline": bool(ci > 0)}


def main():
    raw = json.loads((OUT / "raw_results.json").read_text())
    recs = [r for r in raw["records"] if r.get("probability") is not None]
    leaks = raw.get("leakage", [])

    # ---- §5 GATE (a): leakage. Runs BEFORE any calibration number exists. ----
    hits = sum(1 for l in leaks if l.get("hit"))
    ent = sum(1 for l in leaks if l.get("hit_entity"))
    dat = sum(1 for l in leaks if l.get("hit_date"))
    gate_a_void = hits >= LEAKAGE_VOID_AT
    out = {"leakage_gate": {"n_holdout": len(leaks), "hits": hits, "entity_hits": ent,
                            "date_hits": dat, "void_threshold": LEAKAGE_VOID_AT,
                            "VOID": gate_a_void}}

    pairs = [(float(r["probability"]), int(r["outcome"])) for r in recs]
    bs = sum((p - o) ** 2 for p, o in pairs) / len(pairs) if pairs else None
    gate_b_void = bs is not None and bs < BRILLIANCE_VOID_BELOW
    out["brilliance_tripwire"] = {"brier": None if bs is None else round(bs, 5),
                                  "void_below": BRILLIANCE_VOID_BELOW, "VOID": gate_b_void}

    if gate_a_void or gate_b_void:
        out["VERDICT"] = "VOID"
        out["reason"] = ("leakage gate failed: anonymization does not hold on our text"
                         if gate_a_void else
                         "brilliance tripwire: implausibly-good Brier ⇒ suspected leakage")
        out["calibration_reported"] = False
        out["note"] = ("NO calibration number is reported from a substrate the model can "
                       "de-anonymize. The N_trial is still consumed. Per §5 this is a "
                       "first-class finding: the exception class does not hold on our text.")
        json.dump(out, open(OUT / "verdict.json", "w"), indent=2)
        print(json.dumps(out, indent=2)); return 0

    # ---- gates passed: report the science (§1) ----
    out["VERDICT"] = "SCORED"
    out["calibration_reported"] = True
    out["murphy"] = murphy(pairs)
    clim = [out["murphy"]["base_rate"]] * len(pairs)
    out["skill_vs_climatological"] = skill(pairs, clim, "climatological")
    impl = [r.get("baseline_implied") for r in recs]
    out["skill_vs_market_implied"] = skill(pairs, impl, "market_implied(realized-vol)")
    by = {}
    for r, (p, o) in zip(recs, pairs):
        by.setdefault(r["type"], []).append((p, o))
    out["by_resolver"] = {k: murphy(v) for k, v in by.items()}
    out["NOT_A_CLAIM"] = ("NOT a skill claim, NOT a promotion path, NOT a trading signal. "
                          "G1's forward-only bar is untouched.")
    json.dump(out, open(OUT / "verdict.json", "w"), indent=2)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
