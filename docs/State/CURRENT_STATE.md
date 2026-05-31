# CURRENT_STATE — ArchonDEX

**Last reconciled with source docs:** 2026-05-31 (T-095 close)

**If this date is more than 3 days old, read `forward_plan.md`, `health_check.md`, and the latest `docs/Audit/*` before quoting state.** Hard caps below (≤5 per section, exactly 1 next-decision) are the anti-rot discipline — when a slot fills, the oldest item moves to MEMORY or is superseded.

---

## Validated (max 5)

- [none yet — no substrate-robust, factor-adjusted, MBL-clearing positive finding as of 2026-05-31. Corrected baseline Sharpe ~0.81 on 12-yr is **plausibly-real but not formally validated** (`ci_low ~0.33` doesn't clear DSR; window doesn't clear MBL at honest N). See `docs/Audit/baseline_dsr_mbl_foundational_2026_05_30.md`.]

## Recently refuted / superseded (max 5, rolling)

- **T-095 H-Convention (fill-timing artifact hypothesis)** — REFUTED CLEAN. Code-level trace (5 file:line citations) confirms the backtest already fills at t+1 OPEN on signals computed from t-close. Lou-Polk-Skouras 2019 overnight-alpha leak does NOT apply. The ~0.81 baseline is NOT a close-to-close artifact; T-092 can be read at face value with respect to fill timing. Audit: `fill_convention_diagnostic_t095_2026_05_31.md`.
- **T-057 confidence-gated execution (N≥3)** — REFUTED on 12-yr (Δ Sharpe -0.128; p(Δ>0)=32%). 5-yr-Alpaca +0.793 was a substrate-conditional artifact. First measurement to PASS MBL Gate-0. Do NOT flip. Audit: `multi_year_window_harness_t053b_2026_05_25.md`, `confidence_gated_flag_flip_t057b_2026_05_24.md`.
- **T-055e/g/h regime-conditional vol-target** — CLOSED on 12-yr (Δ Sharpe -0.214, CI [-0.688, +0.260]). 5-yr-Alpaca +0.549 "DEFENSIBLE" verdict retired. The whole T-055 arc shows monotone decay (+0.549 → +0.413 → -0.214) as rigor rose. Audit: `vol_target_12yr_verify_t055h_2026_05_29.md`.
- **T-088 risk_per_trade_pct** — confirmed DEAD KNOB on prod (Path A uses `target_weight`; the knob lives only on dead Path B). Audit HIGH-priority downgraded; historical verdicts STAND because the path was never live. Sweep target is `max_pos_value_pct × max_positions`. Audit: `risk_config_keyfix_t088_2026_05_31.md`.
- **2026-05-06 Engine E refutation** — REVERSED by T-087 + T-089. The 5-yr "AUC 0.49, BLOCKED" verdict was a too-short-window false negative; on 12-yr causal path the HMM p_crisis AUC is 0.887 (verified non-leaky by T-089, lookahead inflation bounded +0.006). Engine E regime signal IS predictive. Audit: `engine_e_regime_rediagnosis_t087_2026_05_30.md`, `regime_validator_causal_fix_t089_2026_05_31.md`.

## In flight (max 5)

- **T-092 (Agent A)** — deep-substrate baseline, 16-yr + 26-yr arm0_off, DSR + MBL verdict. Does the base validate on a longer-than-12-yr window? Result determines the next decision below. (T-095 H-Convention closed clean 2026-05-31 — T-092 can be read at face value with respect to fill timing.)

## Next decision (exactly 1)

- **Await T-092 verdict.** T-095 RESOLVED-CLEAN the fill-convention concern (signal-on-t-close already fills at t+1 OPEN; ~0.81 is NOT a close-to-close artifact). T-092 now the sole gate. If base clears DSR + MBL on 26-yr → portfolio-param sweep (`max_pos_value_pct × max_positions`, both LIVE per T-088) + the research's structural skew decision (trend/barbell overlay). If still borderline / collapses → pivot to structural levers (skew overlay / no-trade bands / new alpha) and tax-rate recompute. The 2026-05-31 research's correction-priority list shrinks by one (fill convention crossed off); tax-rate recompute + structural skew remain. See `docs/Sources/Research_2026_05_31/README.md`.

## Standing constraints (max 5)

- **Honest N_trials:** `run_registry` shows **125 rows**; effective ~**260+** including cloud cells not all back-synced into the registry. MBL bar rises with N — every new measurement on the same substrate raises the threshold the next one must clear.
- **MBL at SR ≈ 0.81 base:** ~**17 years required** (Bailey-Borwein-López de Prado-Zhu 2014). 12-yr window had ~12 → borderline. 26-yr (T-092 in flight) is the test. The 5-yr substrate-honest window would require SR ≥ 1.55 to clear DSR — our base cannot.
- **5-yr-window measurements are statistically under-powered at current N** — they are exploratory only, NEVER flag-flip evidence. CLAUDE.md non-negotiable #7 codifies this.
- **Canonical substrate:** extended Stooq + Alpaca dividend-strip merged (T-082b). Survivors to 1962/1970; delisted missing pre-2020 (survivorship caveat). Any positive lift measured on a different substrate (e.g., Alpaca-only) MUST be re-verified on the canonical before flag-flip recommendation (CLAUDE.md #9).
- **Corrected baseline Sharpe ~0.81 (12-yr), ci_low ~0.33** — plausibly-real, NOT formally validated. Bootstrap CI required on every Sharpe headline (CLAUDE.md #6); kill-thresholds compare against `ci_low`, not point-estimate.

---

*Edited at session end. Hard caps per section. When content falls off the rolling cap, move to `MEMORY.md` or supersede with a newer entry. `forward_plan.md` carries the verbose, narrative version of in-flight planning; `CURRENT_STATE.md` is the at-a-glance dashboard.*
