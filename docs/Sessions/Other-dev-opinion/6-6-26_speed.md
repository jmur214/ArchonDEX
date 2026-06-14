even using the cloud, testing is currently still slow. Any thoughts about how to speed that up even more?

Two things to disentangle first: is the slowness in cloud compute (wall time per cell), in orchestration (build + submit + aggregate cycle), or in interpretation (waiting for human review)? T-053b's time budget showed ~30% compute, ~70% everything else. The highest leverage usually isn't where you think.

That said, here's the prioritized list:

## Tier 1 — basically free, do these first

**1. Cut reps from 5 to 1 + a small determinism canary.** This is the single biggest win available. Post T-057c-det + T-057c-fp-followup, reps produce byte-identical canon_md5. T-053b's audit literally says: "Each arm's 5 reps produced byte-identical trade logs… The rep-axis is reproducibility, not statistical sampling." You're paying 5× compute to prove a thing that's already proven. Replace with: 1 rep per (arm, window) for the result + 1 separate "determinism canary" cell on a tiny window (1 year, single arm, 3 reps) per campaign as a smoke test. That's ~5× compute reduction on every future campaign immediately. Statistical inference already uses block-bootstrap on the daily returns — it doesn't need reps.

**2. Raise the AWS Batch vCPU / max-jobs quota.** T-053b's proof grid was "10 cells parallel, 8 ran first batch, 2 queued." That's a quota wall, not a compute wall. AWS Service Quotas request, free, ~24-hour turnaround. Lets sweeps of 50-100 cells run truly parallel.

**3. Pin the image, kill the per-feature-branch rebuild loop.** T-053b spent 45 min on "docker fix + rebuild + push," most of it daemon recovery. CI OIDC for non-main refs (flagged as open follow-up in the T-053b audit) lets feature branches trigger image builds in GitHub Actions instead of local docker. Also: tag images by code-sha, not `:dev` — so multiple campaigns can target specific image versions without stepping on each other.

## Tier 2 — real engineering, real payoff

**4. Feature-and-substrate cache layer in S3.** Most campaigns repeatedly compute the same things: substrate loading (Stooq+Alpaca merged is now mostly static post-T-082), Foundry features, factor returns, regime labels. Build once per (universe, window), persist to `s3://archondex-cache/<key>/`, lazy-load in every subsequent cell. Same principle as the Discovery Gate 1 caching idea that's been on the health_check HIGH list. Probably **3-10× speedup on multi-cell sweeps** depending on how much of each cell is feature compute. Cheap to verify the upside: profile a single cell, see what fraction is "things every cell recomputes."

**5. Sequential / Bayesian early-stopping for sweeps.** T-055g ran 75 cells of a multiplier sensitivity sweep. Once an arm's running ci_low is clearly above or below the decision threshold, the remaining reps add nothing. Wire a "monitor + cancel" loop: as cells complete, recompute running CIs across all arms, cancel arms that are clearly dispositive. Empirically cuts sweep compute 30-60% for free, because most arms in any sweep are clearly losing or clearly winning early. Sequential analysis literature is mature (Wald SPRT, Bayes factor monitoring).

**6. Polars for the three hottest pandas paths.** Don't rewrite everything. Profile: pick the top 3 pandas hot paths (likely signal compute, factor decomp loop, block-bootstrap resampler). Port just those to polars. 3-5× on those phases. Tier 2 because it's real porting work but bounded scope.

## Tier 3 — structural, biggest theoretical upside

**7. Don't run overlapping windows separately. Run once on the longest, slice the result.** This is the big one if it works. You've now run 5-yr, 12-yr campaigns and have 16-yr/26-yr (T-092) in flight. If a 26-yr backtest emits daily returns + per-trade attribution, you can derive the 12-yr, 5-yr, sub-year metrics by *slicing the result*, not re-running. Difference: 26 years of compute total vs 5+12+16+26 = 59 years of compute for the same evidence. Requires the backtest to be window-deterministic-by-slicing — that needs verification (regime state, governor state, warm-up handling differ between "start at 1999" and "subset to 2014-2019"). But if it holds, you get the deep window for free on every new measurement.

**8. Within-cell year-parallelism for the long windows.** A 12-yr cell takes ~2 hours serially. If you can split the window into year-chunks with proper state-handoff (regime detector warm-start, governor state continuation, equity continuation), you parallelize the slow cells too. The state-handoff is the hard part — the chunks aren't truly independent. But the long cells are now the bottleneck (T-053b needed `--job-timeout 14400` for 12-yr), so the leverage is real.

## Tier 4 — automation of the non-compute part

Time budget says 70% of campaign wall time is *not* compute. That's where leverage you're not asking about lives:

**9. Auto-aggregate + auto-audit-doc skeleton.** T-053b had `scripts/aggregate_t057b.py`, `aggregate_t055e.py`, `aggregate_t057b_cloud.py` — a different aggregator per campaign. Generalize: one aggregator that reads the spec, knows the schema (now that T-091 added PSR/Sortino to the structured producer), writes block-bootstrap CIs, generates an audit-doc skeleton with the verdict pre-filled per CLAUDE.md gates. Saves 30-90 min per campaign of human-driven aggregation + writeup.

**10. The hooks work the other dev was drafting becomes part of this.** Deterministic gates as hooks means the aggregation phase auto-checks PBO/DSR/MBL/factor-decomp without director intervention. Speed and trust at the same time.

## What I'd actually do this week

In order:
1. Cut reps to 1 + add a canary cell pattern (today, config change)
2. File the Batch quota increase (today, fire-and-forget)
3. Profile one cell to confirm where time actually goes (an afternoon)
4. Build the feature/substrate cache if profiling confirms (~1 week)
5. Skip Tier 3 until #4 lands — they're substantial work, and the cache might already get you where you need to be

The first two will probably cut campaign wall time 4-8× by themselves. Don't engineer a polars port until you've taken the free wins.

One honest caveat: speeding up testing is a *good problem to solve, but it solves the wrong constraint right now.* Your bottleneck per CURRENT_STATE is the multi-decade window measurement T-092 — that's *one* in-flight cell that determines the headline question. Speedups help you iterate when there's something to iterate on. Right now there isn't, until T-092 lands. Build the speedups so the *next* campaign moves fast; don't let speed-engineering pull director attention off the verdict-waiting fork.