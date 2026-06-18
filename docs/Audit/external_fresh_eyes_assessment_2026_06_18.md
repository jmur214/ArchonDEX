# External Fresh-Eyes Gap Assessment (2026-06-18)

**Provenance:** independent code-verified audit by an external developer given full repo access
but NO prior context (commissioned via `docs/Sources/external_briefs_2026_06_18/gap_analysis_fresh_eyes.md`).
Deliberately non-leading prompt — the assessor was NOT shown the builders' conclusions. Director
independently re-verified its two hardest technical claims (both hold — see §Verification).

## One-line verdict (the assessor's)
> A rigorously-instrumented, honestly-measured, **risk-managed beta machine with no validated
> alpha** — and its own instruments say exactly that. "Significantly outperform the market" is,
> with high confidence, **unreachable in this design space**, and the project has already done
> the expensive work of proving it. The money should stay in the robo. The interesting question
> is no longer "where's the edge" — it's "why is a \$5–50K account carrying 153K lines of code."

## What's actually live (production path, prod defaults)
A static, hand-tuned weighted-sum of ~20 daily-bar equity edges + inverse-vol sizing + ATR stops
+ an honest execution sim (next-bar-open, ADV-bucketed slippage, real fees/borrow). **The
"autonomous" machinery is inert:** ML/MetaLearner OFF (+ refuted T-149); HMM `p_crisis` computed
every bar but consumed by nothing (only the default-OFF transition overlay touches it);
`regime_conditional_enabled=false` since Apr (regime_gate fed empty dicts); the Governor is reset
to an identity transform in the measured path; Discovery has promoted nothing (T-196 0/35);
~631 governance lines dead; "news/LLM" = a VADER lexicon. The adaptive parts change almost no
trades.

## Capability gaps (assessor's, prioritized)
1. **No validated alpha — the book is closet beta.** 12/13 dense edges factor-negative (T-117);
   the 3 flow edges carrying ~94% of PnL (volume_anomaly/STR/gap_fill) are ALL factor-negative.
   Sharpe = market/momentum/size beta + risk-mgmt + survivorship.
2. **Risk model is a stub** — `factor_analysis.py` never called by `risk_engine.py`; no
   factor-neutrality/VaR/ES; the one validated signal (HMM p_crisis) isn't wired to sizing.
3. **Signal breadth is wide but entirely in the most-arbitraged corner** (daily-bar, x-sec,
   equity, price/volume/calendar). No orthogonal modality is live; 5 positioning parquets + 641
   insider files have zero consumers.
4. **The "autonomous" loop is open at nearly every joint** — hand-driven in production.
5. **No conditional structure is live** — the single most-defensible idea (fork the bull-
   conditional book by the validated HMM) has never been run with the validated input.
6. **Survivorship un-quantified on the headline** — PIT ships default-OFF, the A/B stalled 4×;
   0.751 is an upper bound (mercy: survivorship hits CAGR hard but Sharpe only ~−6%, so the
   no-alpha verdict is robust to it).
7. **A real measurement defect:** Discovery's Gate-6 factor-α screen uses homoskedastic OLS SEs,
   not HAC (`core/factor_decomposition.py:209-213`) → inflated t-stats → the gate is MORE
   permissive than advertised; the honest HAC path exists separately and disagrees in the
   dangerous direction.

## The level-up blind spots (what the builders/director couldn't see)
1. **The measurement apparatus has become the product** — a world-class instrument whose
   headline finding is "no edge," reachable at ~10% of the effort. The rigor is justifying its
   own continuation (sunk-cost/identity loop); each rigorous step is locally correct.
2. **The "surviving" avenues are the hardest place on Earth to find alpha**, not home turf —
   and the MBL arithmetic says even a found 0.1–0.2 Sharpe can't clear honest-N. The open doors
   stay open because closing them = writing down that the goal is unreachable.
3. **Two known biases BOTH point up, un-netted** (survivorship + optimistic small-cap costs);
   CI discipline guards against noise straddling a threshold, not systematic directional bias.
   So 0.751's honest value is probably **below** the 0.40 kill line, not straddling it. Beautiful
   defenses against the wrong failure mode.
4. **The benchmark silently encodes the answer** — beating a low-cost, tax-managed, diversified
   robo net-of-cost AND after-tax with an actively-traded small equity book (that generates ST
   gains) requires alpha we've shown we don't have. Applied honestly, the gate is near
   self-refuting.
5. **"6 engines = a hedge fund" is an org metaphor doing architectural work** — it faithfully
   modeled the part of a hedge fund that DOESN'T generate returns (the org chart), producing
   153K LOC of complexity instead of edge.

## Overbuild (assessor's estimate: ~30K archivable, ~8K closed-out, ~4K duplication)
`scripts/` (170 files, 42K LOC) > all 8 engines combined; ~132/170 imported by nothing; 65 T-xxx
one-off harnesses = 13.8K LOC never archived (violates our own "archive never delete" rule);
`path_c_synthetic_compounder.py` (1,672 LOC orphaned); ~7.6K-LOC closed-negative sleeve cluster;
14 scripts with private Sharpe reimplementations bypassing `core/metrics_engine`; `CLAUDE.md`
guards `live_trader/` which does not exist (paper code is `paper_trader/`).

## The 5 highest-leverage moves (assessor's; #1–2 are decisions, not code)
1. **Run the leave-one-out 26yr attribution as a KILL-GATE (~\$20), not a research step** — the
   cheapest decisive truth; T-117 all but guarantees "beta." Then formally CLOSE the equity-alpha
   hunt rather than leaving doors ajar.
2. **Resolve the goal in writing to ONE honest target** — the single highest-leverage change.
   Either (a) "risk-managed beta delivery vs the robo, money-stays-in-robo accepted," or (b) "a
   falsification/research platform, no real-money pretense." The current goal is unreachable and
   is what drives continued spend.
3. **If continuing technically, exactly one push: wire the validated HMM `p_crisis` to DE-RISK in
   crisis — as beta-quality control, NOT alpha.** The −33% MDD (not the return) is what loses to
   the robo; the HMM is the only validated signal and is consumed by nothing. Re-run with the HMM,
   not the coarse 5-axis advisory that failed in April.
4. **Run the cleanup our own rules already mandate** — archive the one-offs/dead governance/sleeve
   cluster; collapse the 14 private Sharpe reimpls onto core; fix the Gate-6 OLS→HAC defect;
   delete the `live_trader/` guard ghost.
5. **Quantify the two upward biases before quoting any headline again** — finish the stalled PIT
   survivor-vs-PIT A/B + net realistic small-cap costs into the anchors. Until then 0.751 is an
   upper bound that is probably under the kill line.

## Verification (director, independent)
- **Gate-6 OLS-not-HAC defect — CONFIRMED.** `core/factor_decomposition.py:200-213` computes
  `Var(β)=σ²·(X'X)⁻¹` with no Newey-West/`cov_type`/`maxlags` → understates SEs on autocorrelated
  returns → inflates the alpha t-stat. Real measurement-integrity defect; in the silent-fail-open
  class the whole arc has fought. (Did not bite T-196 — H0 means nothing passed anyway — but
  latent.)
- **HMM `p_crisis` unwired — CONFIRMED.** Referenced only by `regime_transition_overlay.py`
  (default-OFF). The only validated predictive signal touches nothing in the live sizing path.

## Director's note
Largely correct and the most clarifying input of this arc. Two context nuances: (1) "money stays
in the robo" was already the user's accepted position (fork resolution 2026-06-15) — this is a
harder-edged independent confirmation, sharpened to "probably not even close (below the kill line),
and the benchmark gate is near self-refuting." (2) The "153K LOC on a \$5–50K account" question's
honest answer is that this has implicitly also been a build/learn/craft project — which is
legitimate, but only if NAMED (exactly the assessor's #2). The HMM-as-risk-control (#3) is the
regime-conditional door reframed honestly: it can't manufacture alpha, but it can cut the MDD that
actually loses to the robo. The goal-resolution is the user's call.
