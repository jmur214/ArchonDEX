---
name: project-t414-o1-stacked-premium-2026-11-20
description: T-414 (O-1, CNDR condor stacked on 100 % equity) CLOSED UNRUN 2026-11-24, 0 trials — the public endpoint pins the mean so t is nearly fixed; my ~2 % P(pass) was mis-specified; later CNDR/BFLY variants carry +1
metadata:
  type: project
---

**CLOSED UNRUN 2026-11-24 by the director, 0 trials.** Nothing was measured, so nothing is refuted.
- Record: `docs/Sources/prereg_o1_stacked_index_premium_t414_CLOSED_UNRUN_2026-11-24.md` (corrections inline, §15 review, §16 author's corrections).
- Code: branch `worktree-agent-a4a994237e4b0208e`, tip `b66b5a2`, not merged. Do not run or fix it.
- The endpoint look is outcome-adjacent: **any later CNDR or BFLY variant carries +1.** PUT and WPUT endpoints, and CNDR's 2020-10-13..19 levels, were displayed too.

**What I got wrong**
- **B1, the pass probability.** I used Φ(E[t] − 2.96) after the endpoint had already fixed the sample mean. Given σ, ρ and cost, t has an sd of 0.10–0.3, not 1. The question becomes "is σ_x below the limit?": c_high 2.0/1.9/1.8 %, c_low 3.35/3.15/3.0 %, zero cost 4.7/4.4/4.1 % (ρ 0/0.2/0.4). The design model says 4.9–6.2 % (the reviewer's says 4.5–5.7 %). Real P(pass) ≈ 0.1 % at c_high, ≤ 1 % at c_low. My "only route to a double-digit chance" cell scored 0/60.
- **B2, the falsifier.** I claimed a FAIL closes premium selling in every wrapper. It could only speak to the monthly 20/5-delta CNDR form, m = 1, best-case tax.
- **R3, κ.** I measured κ on ATM IV and used it on VIX. On VIX it is 1.29–1.33, so $45k has zero condors in ~49.5 % (κ 1.3) to ~73 % (κ 1.6) of rolls.
- **F1.** I demoted the census's worst-month cash buffer to a sensitivity without listing it as a departure. At ≈ 0.5–0.8 %/yr it sets the sign.
- **§1092.** An S&P index position against an S&P core fund is likely related property; deferred losses gave −1.00 %/yr in the reviewer's synthetic case. The modelled tax was a best case.
- **Overclaimed verification.** I reported all 7 controls as proven able to miss; 4 had reversion tests. 22 of 34 mutants survived. I called 45 suite failures environmental before checking (the same 45 fail on main without the code).
- **Incomplete disclosure.** The "what was seen" section omitted index levels I had printed.

**Still true**
- CNDR and BFLY hold bills of 10× the widest wing, so the census's k = 0.10 means m = 1 on the index's excess.
- Cboe's CNDR and BFLY files lack 2020-10-16, a roll day.
- $20k never works; holdable at ~$100k, clean at ~$250k (κ 1.3–1.9).

**Why:** the owner asked to exhaust ideas; O-1 was the census's #2 at "10 %".

**How to apply:**
- When a public endpoint fixes the sample mean, do not attach Φ(E[t] − z) to it. Solve for the σ that reaches the bar and compare it with a design-model σ. If it misses, recommend closing unrun.
- Scope a falsifier to the form tested.
- Count reversion tests before writing "each control can miss". Run a baseline before calling failures environmental.
- List every displayed level of an outcome series in the disclosure.

See [[feedback-displacement-threshold]], [[project-t410-ideas-census-2026-11-20]].
