---
name: t396-lifecycle-leverage-note
description: T-396 pre-run note (2026-11-14) — lifecycle leverage is a risk-preference decision, not a testable edge; T-315's static arms carry a phantom 1.29%/yr cost; LEAPS are not the cheap vehicle at $10k
metadata:
  type: project
---

T-396 (design note, N_trials 0; `docs/Sources/design_note_lifecycle_leverage_t396_2026-11-14.md`, branch `research/lifecycle-leverage-note-t396`) concluded: hold 1×, correct T-315, cohort study optional and descriptive only.

**Why:** three things that are not obvious from the record.
- **Untimed index leverage cannot clear the deflated gate by construction.** Its best possible t-stat is t(μ − σ²): 2.04 on 1968–2025, 2.63 on 1926–2025 (Newey-West), against E[max] 2.96 at N_eff 371. Realistic arms (levered-ETF blend, 1.25–2×) sit at 0.7–2.0. The premium's SE is ~2.1 pp, so Kelly is known only to ± 0.75.
- **T-315's static arms are understated** until someone re-runs it: `static_arm` in `scripts/offense_campaign_t312_t315.py` uses `PeriodIndex.shift(1)` as if it were positional, so the annual 0.51 bp cost is charged daily (~1.29 %/yr). "1.25× significantly LOSES" and "the glide wins the accumulation race" both rest on it; "no arm CI-beats" should survive. It also charges SSO's ER on the whole balance at L < 2 and uses a CAGR gap where Kelly needs the arithmetic mean (7.10 % vs 6.12 %, 1968–2025).
- **The lifecycle gain sits in years 5–24 on a $45–120k levered amount**, not in the small-balance years (years 0–4 ≈ a tenth of it). A flat 1.25× has about the same expected gain with half the dispersion against 1×.

**How to apply:** do not quote T-315's 1.25× loss or its regime split as evidence; check the ledger for a corrected re-run first. When leverage comes up again, price it per borrowed dollar (UPRO+SPY 0.96 %, SSO+SPY 1.37 %, B-5 spreads) and state the forward-premium haircut — one pp of premium moves a 40-year lifecycle outcome by ~11 % of terminal wealth. Any LEAPS claim needs option prices; none are on disk, and one SPY contract (~$71k notional) fits a 2× target only above ~$36k. Related: [[b5-route-c-closed-correlation-regime-bet]].
