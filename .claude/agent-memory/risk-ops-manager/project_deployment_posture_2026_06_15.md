---
name: deployment-posture-borderline-base-2026-06-15
description: Risk-ops deployment-posture verdict on the borderline-real base (0.751/ci_low 0.382, -33% MDD, Roth-only) after BOTH in-house crisis-defense levers were refuted; safe_f sizing gotcha.
metadata:
  type: project
---

# Deployment posture on the borderline base (2026-06-15)

**State of record (do not re-derive — VERIFIED, T-167 re-anchor + T-118r + T-128r):**
- 26yr Sharpe **0.751 / ci_low 0.382** (just UNDER the 0.40 CI-aware kill line; ≪ ~1.55 MBL bar at honest-N), CAGR 7.3%, **MDD −33%**. NOT a collapse (3.2× the old 0.237 substrate artifact), NOT validated.
- 16yr 1.162 / ci_low 0.676 — clears DSR+MBL on its window but crisis-light + survivor-biased = **bull-machine, not all-weather**.
- After-tax taxable Sharpe **0.093** → **Roth-only-deployable**. Taxable killed by ST-tax/turnover (T-141 tax>profit, T-148 tax channel 29× cost, T-151 taxable safe_f 0.273 oversized 73%).
- BOTH in-house crisis-defense levers REFUTED on the clean substrate: HMM de-gross overlay (T-118r — hurts 0.751→0.680, family CLOSED, STRUCTURAL: Δ-trigger misses fast crashes + HMM blind to the dotcom DD that dominates the 26yr MDD) and the spot-ETF sleeve (T-128r — 2-7% MDD cut not 16%, worse in 2008; @25% a soft return-DIVERSIFIER lifting standalone ci_low to 0.501, NOT a hedge).

**THE LOAD-BEARING SIZING FACT (verify before any sizing recommendation):**
The only published safe_f = **1.602 (Roth, +60% headroom)** is on the **BENIGN 2024 SINGLE-YEAR record** (no 20%+ episode). T-151 audit (`safef_car25_t151_2026_06_11.md`) explicitly warns: **the deep-window (26yr, MDD record) safe_f "would bind FAR lower — likely safe_f < 1 pre-tax too."** That deep-window number **DOES NOT EXIST YET** — flagged "one command, zero new compute" on a multi-decade run dir. **Do not quote 1.602 as the deployable Roth sizing fraction.** The honest pre-deploy gate is: run `backtester/safef_car25.py` on the 26yr run dir at P(MaxDD>20%)≤5% FIRST.
**Why:** safe_f is record-conditional by construction (it's a MC over the supplied daily-return record). A -33% MDD book sized off a +60%-headroom benign-year number is the classic edge-case where the position-sizing math is "wrong on the edge cases."
**How to apply:** any time someone proposes leverage/sizing off safe_f 1.602, block until the deep-window safe_f is computed. Expect it < 1.0; size at min(1, safe_f_deepwindow) and NEVER >1.0 (no leverage) on an equity book with no working crisis-defense.

**Deployment verdict (risk-ops lens):**
1. **Paper-trade NOW, do not wait.** The machine is ready and the gate is operational, not edge-validity. Paper validates the MACHINE (fills, reconciliation, kill-monitors), which is the only thing 60 days CAN reveal — alpha + tax are NOT paper-learnable at 60d (forward_plan 2026-06-13 boundary). Waiting buys nothing; the in-house crisis-defense well is dry (both levers dead).
2. **ci_low 0.382 < 0.40 does NOT forbid SMALL-LIVE; it forbids SIZE and the "validated" label.** The 0.40 line is a kill/gating threshold for capital-commitment decisions, not a paper/observation gate. At $5K retail the dollar risk is bounded (a -33% MDD = ~$1,650 paper-loss-equivalent), the purpose is machine-validation not return-harvest, and the borderline metric counsels minimum size + Roth-only + no leverage. It is a real-money path → propose-first, user ratifies.
3. **A -33%-MDD bull-conditional book IS deployable Roth-only at $5K IF AND ONLY IF:** (a) deep-window safe_f computed and sizing capped at min(1, that) — expect <1; (b) the kill-monitors are ARMED (not shadow) before any live $; (c) the owner has consciously accepted the -33% MDD as the unhedged tail (no working crisis-defense exists); (d) Roth-only enforced by the T-141 router. The book is bull-conditional → it WILL ride the full equity drawdown in a 2008/dotcom event. That is the accepted risk, not a hidden one.

**What real-money paths are touched:** `paper_trader/` (PR-3, armed-paper, proven on live PAPER account), the T-141 Roth-first router, the T-152 kill-monitors (currently SHADOW — must arm before live $), Engine B sizing (read-only in paper). PR-4 (archive `live_trader/` stub + move deployment boundary) is HARD-GATED.

**Rollback path:** paper is reversible by construction (no real $). Go-live rollback = FLATTEN via the kill-action + halt new submits (the cash/position-drift halt is the only auto-halt class today; reconciliation refuses new submits until clean). Broker-disconnect-mid-trade: the idempotent client_order_id + torn-journal replay + zero-double-POST-across-restart (T-163 proven) is the disconnect-resilience primitive — verified, not theoretical.

Cross-refs: [[project_t159_paper_readiness_design_2026_06_12]] (auto-memory), T-151/T-141/T-152 audits, conditional_shelf.md entry #3 (the base as bull-machine-missing-a-switch).
