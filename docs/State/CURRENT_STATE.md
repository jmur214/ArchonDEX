# CURRENT_STATE — ArchonDEX

**Last reconciled with source docs:** 2026-06-06 (T-125 dispatch; wave T-102→T-124 closed)

**⚠️ DETERMINISM FIXED (T-125) — but the 26-yr baseline is in a CODE-SHIFT BISECT (T-126):** T-125 pinned the Docker base by digest → `--runs 3` = **3/3 RESTORED**; cloud substrate is trustworthy again. BUT the re-baseline gave 26-yr **0.446** (bitwise-reproducible) vs T-092's **0.246**, and the pin proved the shift is **CODE-driven** (T-099→T-124 merges), not OS/lib. **T-126 bisect (in flight) decides:** either T-099's determinism fix legitimately re-canonicalized a noisy number (→ 0.446 real, **bull-conditional collapse SOFTENS**) OR an "inert" merge broke at 26-yr depth (→ bug to fix). **Until T-126 returns, do not quote EITHER 0.246 or 0.446 as settled, and the held cloud wave stays held.** (16-yr also unsettled: pinned 0.945 vs T-092 1.018.)

**If this date is more than 3 days old, read `forward_plan.md` (2026-06-06 block = current plan), `health_check.md`, and the latest `docs/Audit/*` before quoting state.** Hard caps below (≤5 per section, exactly 1 next-decision) are the anti-rot discipline — when a slot fills, the oldest item moves to MEMORY or is superseded.

---

## Validated (max 5)

- [none yet — no substrate-robust, factor-adjusted, MBL-clearing positive finding as of 2026-05-31. Corrected baseline Sharpe ~0.81 on 12-yr is **plausibly-real but not formally validated** (`ci_low ~0.33` doesn't clear DSR; window doesn't clear MBL at honest N). See `docs/Audit/baseline_dsr_mbl_foundational_2026_05_30.md`.]

## Recently refuted / superseded (max 5, rolling)

- **T-092 deep-substrate baseline (FINAL, n=5/16-yr, n=4/26-yr)** — refutes "a deeper window will validate the base." Sharpe INVERTS with depth: 5yr 0.60 → 12yr 0.81 → **16yr 1.018 (ci_low 0.560, CAGR 11.0%, MDD -15.4%)** → **26yr 0.246 (ci_low -0.119, CAGR 2.64%, MDD -59.3%)**. 16-yr clears MBL + point-DSR + ci_low>0 (strongest cell ever); 26-yr FAILS every gate (8/26 years negative, worst 2008 -1.28, underperforms buy-hold SPY ~4%/yr). **Strict `ci_low > DSR-benchmark` (0.66) FAILS on EVERY window** (12yr 0.33, 16yr 0.56) — by CLAUDE.md #6 nothing is formally validated. 16-yr is the crisis-free window (excludes 2008+dotcom); base is bull-conditional. Survivor-only → UPPER bounds. **PIVOT SIGNAL.** Also: determinism drift scales with window depth (26yr 0.19, >3-Sharpe per-year swings) — T-057c-det-followup insufficient at long windows. Branch `feature/deep-substrate-baseline-t092` @ 15bdd97. Audit: `deep_substrate_baseline_t092_2026_05_31.md`. **⚠️ UNDER RE-VERIFICATION (T-125, 2026-06-06):** a fresh-image rebuild gave arm0 26yr **0.446 not 0.246** — either library-drift (unpinned image; pinning will restore 0.246) or a non-inert code change in the T-099→T-124 merges (then bisect). If the 26yr base is really ~0.446, the "collapse"/bull-conditional narrative SOFTENS. Verdict pending T-125 re-baseline on the pinned image.
- **T-098 H-Band no-trade bands** — REFUTED at ±20%/±25% on 12-yr (Δ Sharpe +0.008/+0.018, ci_low NEGATIVE both; turnover Δ <2% vs predicted −60-70%; skew mixed, arm2 worse). Band suppresses small rebalances but not the dominant large vol-target ones (Donohue-Yip calibrated to monthly concentrated books, not our daily inverse-vol 30-name). Clean Engine C impl (default-OFF, canon-OFF=baseline, ON-differs, det 3/3) kept additive for a future tighter-band sweep. Branch `feature/h-band-no-trade-t098` @ bf9da13 NOT merged (refuted+inert). Audit: `no_trade_band_h_band_t098_audit_2026_05_31.md`. **B's 12-yr arm0_off Sharpe 1.314 is MEAN-OF-12-ANNUAL, NOT comparable to pooled-full-window 0.81 — director-verified from cell JSON; 0.81 STANDS (same statistic-mismatch as the old Foundation-Gate 1.296 → pooled 0.507).**
- **T-095 fill-convention (H-Convention)** — REFUTED (good outcome): backtest already fills at **t+1 OPEN**, not close-to-close. Lou-Polk-Skouras overnight-alpha-leak does NOT apply; ~0.81 was never fill-inflated. Director-verified `execution_simulator._next_price_for_entry_exit`. Audit: `fill_convention_diagnostic_t095_2026_05_31.md`.
- **T-057 confidence-gated execution (N≥3)** — REFUTED on 12-yr (Δ Sharpe -0.128; p(Δ>0)=32%). 5-yr-Alpaca +0.793 was a substrate-conditional artifact. Do NOT flip. Audit: `multi_year_window_harness_t053b_2026_05_25.md`, `confidence_gated_flag_flip_t057b_2026_05_24.md`.
- **T-055e/g/h regime-conditional vol-target** — CLOSED on 12-yr (Δ Sharpe -0.214). 5-yr-Alpaca +0.549 "DEFENSIBLE" retired; T-055 arc monotone decay (+0.549 → +0.413 → -0.214) as rigor rose. Audit: `vol_target_12yr_verify_t055h_2026_05_29.md`.

<!-- Dropped to honor ≤5 cap (both fully captured in MEMORY.md): T-088 risk_per_trade_pct dead-knob (project_t088_risk_per_trade_dead_knob); T-087/T-089 Engine E reversal — HMM hmm_p_crisis IS predictive (AUC 0.887, 12-yr causal), the validated signal the Path-B kill-switch would use (project_engine_e_reversal_predictive). -->

> **Load-bearing for the decision above:** Engine E's `hmm_p_crisis` is VALIDATED-predictive (T-087/T-089, AUC 0.887) — it's the signal a Path-B HMM kill-switch would gate on. Full entry in MEMORY.

## In flight (max 5)

- **T-125 (Agent B) — CRITICAL PATH.** Pin the cloud image (digest + requirements.lock) → restore `--runs 3` = 3/3 determinism → re-baseline T-092 on the pinned image. **Blocks every cloud A/B below.** Until 3/3, nothing cloud runs trustworthily.
- **T-118 (Agent C) — HELD on T-125.** HMM transition-trigger de-gross overlay; STEP-1 PASS (crisis-model+OFF == baseline 0145c03a bitwise, model-fork verified). Pre-registered lean 52-cell A/B armed; launch waits on the pinned image + 2-cell pre-flight. THE de-gross headline experiment.
- **Spot-sleeve cloud A/B (Agent A) — HELD on T-125.** T-120/T-121 found T-115's analytical "winner" does NOT survive faithful integration (real cause = engine-side capital-scale-dependence ~2.7pp/yr, not coupling). Prior now NEGATIVE; the 16/26-yr integrated A/B is the verdict.
- **T-113 drawdown-lift A/B — HELD on T-125.** The A/B T-106 couldn't run (lift now on Path A via T-111).
- **Fair BAB deep-window re-test — QUEUED (D).** T-123 BAB missed but on its WORST window (2014-25 low-beta headwind, large-cap); the fair deep-window test (incl 2008) is the real alpha referendum — gated on T-125.

## Next decision (exactly 1)

- **THE GATE (2026-06-06): B's T-125 must restore 3/3 cloud determinism + re-baseline T-092 before ANYTHING cloud advances.** Once T-125 lands, two forks open at once: (1) the **de-gross verdict** — C's T-118 HMM transition-trigger overlay A/B (does regime-transition de-gross close the crisis gap?); (2) the **re-baseline interpretation** — if the 26-yr base is really ~0.446 not 0.246, the strategic picture (bull-conditional collapse) softens and may need a forward_plan revision. The alpha track is paused at an **architecture/mission fork** (T-117+T-122+T-123: no edge clears t>2, but BAB's miss was on its worst window → the fair deep-window BAB re-test, also gated on T-125, is the decider). **Plan of record: `forward_plan.md` 2026-06-06 block** (two-track: de-gross overlay + literature edges; PARK Engine D autonomous Discovery). Everything below this bullet is 2026-06-04 sequencing context, partially executed (T-101/T-106/T-111/T-116 done) — retained for the trail, not the current plan.
- _(historical context — 2026-06-04)_ **PATH B IN EXECUTION. MASTER FINDING (T-100, 2026-06-04): the crisis defenses EXIST in code but were STARVED in the backtest — that is why the base drew -59% on 26-yr, NOT an absence of defensive machinery.** B's instrumentation: (a) HMM **not wired** — 0/1174 advisory calls received `hmm_proba` (`hmm_enabled=false` default); (b) 5-axis regime detector **MISSED COVID** (0 crisis bars May–Dec 2020); (c) regime returns None pre-2020 on the local SPY gap (~80% of a local 26-yr run dormant); (d) the Engine-B `risk_scalar` 46% cut the audit flagged lives on **DEAD Path B** (atr-risk, confirms T-088 — prod uses Path A target_weight; the static audit-read was wrong, B's empirical trace is right). **In flight / sequenced:**
  - **T-099 (MERGED 253a96f):** long-window FP-determinism fixed (5 sites; 12-yr `--runs 3` bitwise-identical). Cloud cross-container 26-yr verify still recommended (T-099-verify).
  - **Phase 0+ (T-101 DONE 2026-06-04, Agent B):** `hmm_enabled=true` flipped in `config/regime_settings.json`. Q1' YES — posterior flows (1174/1174 advisory calls). Q2'/Q3' NO change — regime_summary distribution + per-arm gross deltas + 2022 default-cell canon are BITWISE IDENTICAL pre/post-flip. **CAPABILITY failure, not WIRING.** HMM modulates `risk_scalar` on dead Path B; Path A (production target_weight sizing) doesn't consume it. The −59% MDD was never going to be saved by a config flag. Det 3/3 PASS. Flag stays flipped (no-op for trades, observability win). Audit: `hmm_wire_phase0plus_t101_2026_06_04.md`.
  - **Phase 0b (cloud cell):** 2008 + 2000-02 need cloud data (local SPY starts 2020-04) to test crisis response on the real GFC/dotcom regimes.
  - **Phase 1 (Engine B, propose-first, 2nd gate):** binary de-gross to floor=0.25 (cash) — warranted per T-100 outcome (c), but design must REPLACE/COMPOSE-WITH the existing (now-to-be-fed) advisory de-gross, not stack a 5th cut. Returns for review.
  - **Phase 2 A/B (gated on T-099✓ + Phase-0+):** arms off/0.25/0.50/0.0/tiered, 16-yr + 26-yr, bootstrap CI. Adopt iff MaxDD −≥25% AND Sharpe-ci_low not down.
  - **Parallel fast win (APPROVED 2026-06-04):** drawdown kill-switch (already built, default-OFF, warn5/degross10/halt15) — enable + A/B. Plus capability_ledger.md + contract Layer-3 doc-fix (APPROVED). Plus F regime-conditional per-edge kill re-verify+enable (APPROVED).
  - **LAYER 2 — trend sleeve:** scaffold ALREADY EXISTS (`engine_c/sleeves/`, unwired, gauntlet-failed on megacaps) — wire+re-test, don't rebuild.
  - **Path A NOT pursued.** Deprioritized: H-Tax T-097.

## Standing constraints (max 5)

- **Honest N_trials:** `run_registry` shows **125 rows**; effective ~**260+** including cloud cells not all back-synced into the registry. MBL bar rises with N — every new measurement on the same substrate raises the threshold the next one must clear.
- **MBL at SR ≈ 0.81 base:** ~**17 years required** (Bailey-Borwein-López de Prado-Zhu 2014). 12-yr window had ~12 → borderline. 26-yr (T-092 in flight) is the test. The 5-yr substrate-honest window would require SR ≥ 1.55 to clear DSR — our base cannot.
- **5-yr-window measurements are statistically under-powered at current N** — they are exploratory only, NEVER flag-flip evidence. CLAUDE.md non-negotiable #7 codifies this.
- **Canonical substrate:** extended Stooq + Alpaca dividend-strip merged (T-082b). Survivors to 1962/1970; delisted missing pre-2020 (survivorship caveat). Any positive lift measured on a different substrate (e.g., Alpaca-only) MUST be re-verified on the canonical before flag-flip recommendation (CLAUDE.md #9).
- **Corrected baseline Sharpe ~0.81 (12-yr), ci_low ~0.33** — plausibly-real, NOT formally validated. Bootstrap CI required on every Sharpe headline (CLAUDE.md #6); kill-thresholds compare against `ci_low`, not point-estimate.

---

*Edited at session end. Hard caps per section. When content falls off the rolling cap, move to `MEMORY.md` or supersede with a newer entry. `forward_plan.md` carries the verbose, narrative version of in-flight planning; `CURRENT_STATE.md` is the at-a-glance dashboard.*
