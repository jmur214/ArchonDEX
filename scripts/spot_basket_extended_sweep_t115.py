"""T-115 — extend the T-112 spot-basket sweep to {25%, 30%} on the deep
17.9yr 2008-inclusive window. Resolves the T-112 evidence tension
(KMLM @10% strict-gate-pass on 5.1yr thin history vs spot basket @20%
closest-miss on deep history).

Per inbox: spot-basket-only extension. Do NOT re-litigate KMLM/DBMF.
Same harness as T-112 (analytical capital-partition + block-bootstrap CI).

Watch for the Pareto turn:
- where does the spot basket's calm-Sharpe HELP invert to drag?
- where does the Sharpe ci_low start dropping?
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.managed_futures_sleeve_phase1_t112 import (  # noqa: E402
    analyze_sleeve, evaluate_arm,
    load_base_returns, load_spot_basket_returns,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out-json",
        default=str(REPO / "docs/Measurements/2026-06/t115_spot_basket_extended.json"),
    )
    args = ap.parse_args()

    # Extended sweep: include T-112's 10/15/20 for context + new 25/30.
    allocations = [0.00, 0.10, 0.15, 0.20, 0.25, 0.30]

    print(f"[T-115] Loading base equity (T-092 arm0_off 26yr canonical rep1)...")
    base_26yr = load_base_returns("26yr")
    print(f"   base: {base_26yr.index.min().date()} → {base_26yr.index.max().date()}  n={len(base_26yr)}")

    print(f"\n[T-115] Re-running T-108 spot 8-ETF basket harness (~30-60s)...")
    spot_rets = load_spot_basket_returns()
    print(f"   spot: {spot_rets.index.min().date()} → {spot_rets.index.max().date()}  n={len(spot_rets)}")

    print(f"\n[T-115] === Spot 8-ETF basket extended sweep: alloc ∈ {[int(a*100) for a in allocations]}% ===")
    spot_analysis = analyze_sleeve(
        "Spot 8-ETF basket", base_26yr, spot_rets,
        allocations, "T-092 arm0_off 26yr (2000-2025)",
    )

    # Decision-gate eval per allocation
    base_arm = spot_analysis["arms"][0]
    gate_rows = []
    for arm in spot_analysis["arms"][1:]:
        ev = evaluate_arm(arm, base_arm)
        # Absolute MDD pp = base - arm (both negative; we want pp REDUCTION).
        abs_mdd_pp = abs(base_arm["max_drawdown"]["point"]) - abs(arm["max_drawdown"]["point"])
        gate_rows.append({
            "allocation": arm["allocation"],
            "mdd_reduction_rel": ev["mdd_reduction_pct"],
            "mdd_reduction_abs_pp": abs_mdd_pp,
            "sharpe_ci_low_arm": arm["sharpe"]["ci_low"],
            "sharpe_ci_low_base": base_arm["sharpe"]["ci_low"],
            "sharpe_ci_low_delta": arm["sharpe"]["ci_low"] - base_arm["sharpe"]["ci_low"],
            "sharpe_ci_low_not_down": ev["sharpe_ci_low_not_down"],
            "calmar": arm["calmar"]["point"],
            "calm_sharpe": arm["calm_year_sharpe"],
            "calm_sharpe_delta": ev["calm_sharpe_delta"],
            "calm_drag_bounded": ev["calm_drag_bounded"],
            "crisis_sharpe": arm["crisis_period_sharpe"],
            "passes_decision_gate": ev["passes_decision_gate"],
        })

    print(f"\n[T-115] === GATE TABLE (spot basket, 17.9yr base, deep window) ===")
    print(f"   alloc | MDD rel | MDD abs pp | Sharpe ci_low | calm-Δ | passes?")
    for r in gate_rows:
        print(
            f"   {r['allocation']*100:>4.0f}% |"
            f" {r['mdd_reduction_rel']*100:>+6.1f}% |"
            f" {r['mdd_reduction_abs_pp']*100:>+6.2f}pp |"
            f" {r['sharpe_ci_low_arm']:>+7.4f} (Δ {r['sharpe_ci_low_delta']:+.3f}) |"
            f" {r['calm_sharpe_delta']:>+6.3f} |"
            f" {'YES' if r['passes_decision_gate'] else ' no'}"
        )

    # Pareto turn analysis
    print(f"\n[T-115] === Pareto-turn analysis ===")
    arms_with_meta = [(r["allocation"], r) for r in gate_rows]
    sharpe_ci_low_seq = [r["sharpe_ci_low_arm"] for _, r in arms_with_meta]
    calm_delta_seq = [r["calm_sharpe_delta"] for _, r in arms_with_meta]

    # First allocation where calm-Δ goes negative
    calm_invert_alloc = None
    for a, r in arms_with_meta:
        if r["calm_sharpe_delta"] < 0:
            calm_invert_alloc = a
            break
    # First allocation where sharpe ci_low decreases vs previous
    sharpe_decrease_alloc = None
    prev = base_arm["sharpe"]["ci_low"]
    for a, r in arms_with_meta:
        if r["sharpe_ci_low_arm"] < prev - 1e-6:
            sharpe_decrease_alloc = a
            break
        prev = r["sharpe_ci_low_arm"]

    print(f"   Calm-Sharpe-Δ across allocations 10→30%: {[f'{x:+.3f}' for x in calm_delta_seq]}")
    print(f"   First allocation where calm-Δ < 0: "
          f"{f'{calm_invert_alloc*100:.0f}%' if calm_invert_alloc else 'never (calm-help survives entire sweep)'}")
    print(f"   Sharpe ci_low across allocations 10→30%: {[f'{x:+.4f}' for x in sharpe_ci_low_seq]}")
    print(f"   First allocation where Sharpe ci_low drops vs prior: "
          f"{f'{sharpe_decrease_alloc*100:.0f}%' if sharpe_decrease_alloc else 'never (monotonic non-decreasing)'}")

    # Find lowest passing allocation per inbox rule (lowest = less capital diverted)
    passing = [(r["allocation"], r) for r in gate_rows if r["passes_decision_gate"]]
    if passing:
        passing.sort(key=lambda x: x[0])
        winner_alloc, winner_row = passing[0]
        verdict = (
            f"RECOMMEND spot 8-ETF basket @ {winner_alloc*100:.0f}% "
            f"(MDD reduction +{winner_row['mdd_reduction_rel']*100:.1f}% rel / "
            f"+{winner_row['mdd_reduction_abs_pp']*100:.2f}pp abs)"
        )
    else:
        # Pick highest-MDD-reduction among non-passing for the "closest miss" framing
        closest = max(gate_rows, key=lambda r: r["mdd_reduction_rel"])
        verdict = (
            f"NONE — spot basket plateaus below 15% gate even at 30% allocation. "
            f"Best arm: spot @ {closest['allocation']*100:.0f}% with "
            f"MDD reduction +{closest['mdd_reduction_rel']*100:.1f}% rel / "
            f"+{closest['mdd_reduction_abs_pp']*100:.2f}pp abs. "
            f"Director-decision tension persists: spot @ 20-30% (deep, calm-help, 13-?%) "
            f"vs KMLM @ 10% (thin 5.1yr history, 15.4%)."
        )
    print(f"\n[T-115] VERDICT: {verdict}")

    out = {
        "task": "T-2026-06-06-115",
        "allocations": allocations,
        "spot_basket_analysis": spot_analysis,
        "gate_table": gate_rows,
        "pareto_turn": {
            "first_calm_delta_negative_alloc": calm_invert_alloc,
            "first_sharpe_ci_low_drop_alloc": sharpe_decrease_alloc,
            "calm_delta_sequence": calm_delta_seq,
            "sharpe_ci_low_sequence": sharpe_ci_low_seq,
        },
        "verdict": verdict,
    }
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n[T-115] wrote {out_path}")


if __name__ == "__main__":
    main()
