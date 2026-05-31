# CURRENT_STATE — ArchonDEX

**Last reconciled with source docs:** 2026-05-31

**If this date is more than 3 days old, read `forward_plan.md`, `health_check.md`, and the latest `docs/Audit/*` before quoting state.** Hard caps below (≤5 per section, exactly 1 next-decision) are the anti-rot discipline — when a slot fills, the oldest item moves to MEMORY or is superseded.

---

## Validated (max 5)

- [none yet — no substrate-robust, factor-adjusted, MBL-clearing positive finding as of 2026-05-31. Corrected baseline Sharpe ~0.81 on 12-yr is **plausibly-real but not formally validated** (`ci_low ~0.33` doesn't clear DSR; window doesn't clear MBL at honest N). See `docs/Audit/baseline_dsr_mbl_foundational_2026_05_30.md`.]

## Recently refuted / superseded (max 5, rolling)

- **T-057 confidence-gated execution (N≥3)** — REFUTED on 12-yr (Δ Sharpe -0.128; p(Δ>0)=32%). 5-yr-Alpaca +0.793 was a substrate-conditional artifact. First measurement to PASS MBL Gate-0. Do NOT flip. Audit: `multi_year_window_harness_t053b_2026_05_25.md`, `confidence_gated_flag_flip_t057b_2026_05_24.md`.
- **T-055e/g/h regime-conditional vol-target** — CLOSED on 12-yr (Δ Sharpe -0.214, CI [-0.688, +0.260]). 5-yr-Alpaca +0.549 "DEFENSIBLE" verdict retired. The whole T-055 arc shows monotone decay (+0.549 → +0.413 → -0.214) as rigor rose. Audit: `vol_target_12yr_verify_t055h_2026_05_29.md`.
- **T-088 risk_per_trade_pct** — confirmed DEAD KNOB on prod (Path A uses `target_weight`; the knob lives only on dead Path B). Audit HIGH-priority downgraded; historical verdicts STAND because the path was never live. Sweep target is `max_pos_value_pct × max_positions`. Audit: `risk_config_keyfix_t088_2026_05_31.md`.
- **T-095 fill-convention (H-Convention)** — hypothesis REFUTED (good outcome): the backtest already fills at **t+1 OPEN**, not close-to-close. The Lou-Polk-Skouras overnight-alpha-leak (~0.55 Sharpe if momentum-dominated) does NOT apply; ~0.81 was never fill-inflated. Verified by director spot-check of `execution_simulator._next_price_for_entry_exit`. Audit: `fill_convention_diagnostic_t095_2026_05_31.md`.
- **2026-05-06 Engine E refutation** — REVERSED by T-087 + T-089. The 5-yr "AUC 0.49, BLOCKED" verdict was a too-short-window false negative; on 12-yr causal path the HMM p_crisis AUC is 0.887 (verified non-leaky by T-089, lookahead inflation bounded +0.006). Engine E regime signal IS predictive. Audit: `engine_e_regime_rediagnosis_t087_2026_05_30.md`, `regime_validator_causal_fix_t089_2026_05_31.md`.

## In flight (max 5)

- **T-092 (Agent A) — PARTIAL verdict in (n=4 on 16-yr, n=1 preview on 26-yr; final commit pending 5 cells).** Sharpe INVERTS with depth: 5yr 0.60 → 12yr 0.81 → **16yr 1.02 (ci_low 0.56, MDD -15.4%)** → **26yr 0.44 (ci_low 0.05, MDD -48%)**. 16-yr clears MBL + point-DSR; 26-yr fails both. The strict `ci_low > DSR-benchmark` (0.66) gate FAILS on EVERY window — by CLAUDE.md #6 nothing is formally validated. 16-yr is the crisis-free window (excludes 2008 + 2000-02); 26-yr per-year shows all pre-2009 bear/vol regimes hurt → base ensemble is bull-conditional. Survivor-only universe → numbers are UPPER bounds. Audit: `deep_substrate_baseline_t092_2026_05_31.md` (drafting).

## Next decision (exactly 1)

- **USER DECISION PENDING — T-092 Path A vs Path B.** **Path A:** treat 16-yr as the validation substrate, green-light overlay work (vol-target / confidence-gate / T-088 param sweep on a 16-yr A/B). **Path B:** treat the 26-yr collapse as a pivot-signal — the base 6-edge set is bull-conditional, so build crisis-regime robustness FIRST (HMM-gated kill switch using T-087's validated `hmm_p_crisis`, Engine D gene-encoding unblock, or the parked LLM-analyst path) before more overlays. **Director read (not user-ratified):** rigorous reading leans Path B — anointing the best-scoring window (16-yr excludes 2008+dotcom) is specification search; the strict CI gate fails everywhere; survivorship strengthens the pivot. A's own headline #5 converges here. NOT decided autonomously. (B mid-flight on T-098 H-Band; H-Tax T-097 staged.) See A's outbox + `docs/Sources/Research_2026_05_31/README.md`.

## Standing constraints (max 5)

- **Honest N_trials:** `run_registry` shows **125 rows**; effective ~**260+** including cloud cells not all back-synced into the registry. MBL bar rises with N — every new measurement on the same substrate raises the threshold the next one must clear.
- **MBL at SR ≈ 0.81 base:** ~**17 years required** (Bailey-Borwein-López de Prado-Zhu 2014). 12-yr window had ~12 → borderline. 26-yr (T-092 in flight) is the test. The 5-yr substrate-honest window would require SR ≥ 1.55 to clear DSR — our base cannot.
- **5-yr-window measurements are statistically under-powered at current N** — they are exploratory only, NEVER flag-flip evidence. CLAUDE.md non-negotiable #7 codifies this.
- **Canonical substrate:** extended Stooq + Alpaca dividend-strip merged (T-082b). Survivors to 1962/1970; delisted missing pre-2020 (survivorship caveat). Any positive lift measured on a different substrate (e.g., Alpaca-only) MUST be re-verified on the canonical before flag-flip recommendation (CLAUDE.md #9).
- **Corrected baseline Sharpe ~0.81 (12-yr), ci_low ~0.33** — plausibly-real, NOT formally validated. Bootstrap CI required on every Sharpe headline (CLAUDE.md #6); kill-thresholds compare against `ci_low`, not point-estimate.

---

*Edited at session end. Hard caps per section. When content falls off the rolling cap, move to `MEMORY.md` or supersede with a newer entry. `forward_plan.md` carries the verbose, narrative version of in-flight planning; `CURRENT_STATE.md` is the at-a-glance dashboard.*
