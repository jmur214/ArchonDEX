---
task_id: RR-1 (alpha-frontier program §3.1)
title: Backtester sizes from a frozen capital figure — repair proposal
date: 2026-09-30
author: Agent C
branch: fix/referee-rr1-sizing-capital
type: REFEREE REPAIR PROPOSAL — propose-only. The referee is never autonomously modified.
route: Agent R (independent review) → director → the USER rules on merge.
n_trials: 0 — a correction, not a hypothesis. Every re-run below is labeled RE-SCORE.
status: MERGED (70837b2). §1-6 COMPLETE. §4 RE-SCORE COMPLETE 2026-10-14 (8/8 cells). Anchor paired ΔSharpe +0.238 [−0.058, +0.508]; the 2012–2024 baseline book −0.324 [−0.696, +0.044]. The sign is not one direction across books, and nothing is established at 95%. §4 is written on docs/rr1-section-4.
---

# RR-1 — the backtester sized every position from a frozen capital figure

## Summary

`BacktestController` set `portfolio.capital` once, to the seed, and never updated it.
Sizing equity was therefore `seed + market value`, not `cash + market value`. Once the book
deployed, it sized from up to **2.5×** its real equity, bought on credit, and ran
**negative cash that was never charged interest** — free leverage in every equity-book
backtest the controller ever produced.

The fix is three lines. What it changes is larger: **31 recorded verdicts** rest on numbers
this controller produced (§5), and the recorded demotion scope is both too narrow and, in
one place, too wide.

---

## §1 — The pre-registered probe

**Pre-registration (brief §3.1 RR-1).** H1: sizing equity diverges from true equity after
the first fill. Refutation: if sizing == cash + MV on every bar, the finding is wrong —
write that and stop.

**Instrument.** `scripts/probe_rr1_sizing_equity.py` drives the **real** golden-master
pipeline — identical fixture and edges, imported from `tests/test_golden_master.py` rather
than restated — and observes every bar in-process through a read-only wrapper on
`_log_snapshot`, which computes true equity the same way the controller reports it. It
mutates nothing. Its verdict detects which side of the fix it is reading, because the same
count means opposite things on the two sides: a probe that printed "REFUTED" on the fixed
branch would tell a reviewer the finding was wrong at the exact moment it was confirmed
repaired.

**Result — H1 CONFIRMED on the unfixed controller:**

```
bars observed: 251   bars where sizing != true equity: 251
first divergence: 2021-01-05   (first bar with a fill = 2021-01-05)
sizing_capital:  min 100,000  max 100,000   <- frozen for the entire year
cash:            min -65,593  max 110,134
sizing/true equity ratio: median 1.369  max 2.508
gross (MV / true equity): median 0.409  max 1.597
bars with NEGATIVE cash: 17     bars with gross > 1.0: 17
```

Worst bar, 2021-10-18: the controller sized from **$275,420** while holding **$109,827** of
equity — $175,420 of stock on $110k, financed by **$65,593 of uncharged credit**.

**Result — the same probe on the branch:**

```
bars observed: 251   bars where sizing != true equity: 0
VERDICT: sizing == cash + MV on every bar. This is the FIXED controller.
sizing/true equity ratio: median 1.000  max 1.000
bars with NEGATIVE cash: 2      bars with gross > 1.0: 2      (see §6.1)
```

251/251 → 0/251 on the same instrument. The unfixed run is the reversion: restoring the old
getter restores the divergence.

**The defect cuts both ways.** Of the 251 divergent bars, 241 are *over*-sized. The other 10
are *under*-sized: when the book was up and mostly in cash (cash peaked at $110,134), the
frozen $100,000 seed sized it *below* its real equity. So the bug is not a pure leverage
bias; it is a sizing error whose sign follows the book's P&L and deployment.

**On the targeted xfail.** `test_backtester_sizing_capital_tracks_deployed_cash` now passes
(marker removed there only, per the brief's rail; the other 15 stay xfail). Reviewers
should know it is a **unit mimic** — it hand-copies the init lines onto a
`__new__`-constructed controller and never drives the real loop, so it proves the getter,
not the integration. The integration evidence is the probe above. A test genre that reads
code rather than running it passed 53 times on a broken line in September; this proposal
does not rest on one.

---

## §2 — The fix

- `get_portfolio_capital()` returns `float(self.portfolio.cash)`.
- The dynamic `portfolio.capital` write is **deleted** at both init sites (`:157-158`,
  `:1435-1436`). The adjacent one-time **cash** init lines are untouched — they run before
  any fill and are not part of the defect.
- Sizing therefore reads `cash + Σ MV` at all three sites (`:647`, `:678`, `:680`) — the
  same definition `_log_snapshot` reports.
- `deployable_cash_account` untouched.

**Blast radius, checked by grep rather than assumed:** the getter's only callers are those
three sizing sites; `portfolio.capital` is read nowhere else in the repository.

**One tightening beyond the brief.** The old fallback, `getattr(self.portfolio, "cash", 0.0)`,
would have sized from **zero equity** had cash ever been missing — a plausible-looking
number in the measurement path. Reading `.cash` directly makes that raise instead
(`[NN-FAIL-CLOSED]`).

**Scope limit, deliberate.** The three sizing sites price positions at bar `ts`;
`_log_snapshot` prices at the next bar. The fix unifies the *definition* (cash + MV), not
the *price source*. Unifying the price source is a separate behavioral change and would
have confounded the golden diff.

---

## §3 — Golden-fixture diff

Regenerated on the branch only, in its own commit, per the golden master's own rule.

**Attributable to RR-1 alone:** `golden_input.sha256` and `golden_signals.csv` are
**unchanged**; only the downstream outputs moved (`golden_equity.csv`, `golden_trades.csv`,
`golden_summary.txt`). Same inputs, same signals — the diff is sizing and nothing else.
The golden test passes on the branch.

| metric | before (bug) | after (fix) | Δ |
|---|---|---|---|
| Sharpe | 0.0495 | 0.2138 | +0.1644 |
| trades | 171 | 166 | −5 |
| turnover (notional) | $4,047,969 | $3,529,395 | −12.8% |
| max position (notional) | $47,957 | $34,461 | −28.1% |
| total return | −0.28% | +1.85% | +2.13pp |
| max drawdown | −11.98% | −10.30% | 1.68pp shallower |

**This contradicts the brief's expected direction.** The review expected the free leverage
to have *flattered* bull-year Sharpe and CAGR. 2021 is a bull year, and removing the
leverage *improved* Sharpe, return and drawdown together: on this fixture the bug
amplified a weak book's losing bets, not its winners.

**This is not a measurement.** One year, twelve names, a regression pin with no CI. It must
not be quoted as a headline (`[NN-SHARPE-CI]`). It establishes only that the expected
direction is not guaranteed — which is why the 26-year RE-SCORE in §4 matters.

**The golden master is excluded from the default test tier.** It is marked `slow`, and
`pytest.ini` sets `addopts = -m "not slow"`, so it runs only when selected explicitly. Every
"full suite passes" figure quoted in the program's history excludes it. The acceptance runs
here select it explicitly.

**Test tiers on the branch:** default 3,943 passed / 0 failed (18 xfailed, 22 skipped); slow
tier 4/4 passed. The only golden-pinned test is the golden master itself, regenerated and
passing.

---

## §4 — RE-SCORE — **COMPLETE** (8/8 cells, 2026-10-14 12:35)

### Result — the 26-year anchor pair

**The fix moves every number in the right direction, but the paired test does not establish the
direction.** The two arms differ only by RR-1. Both are canonical, and both ran on
code-identical commits (see *Provenance* below).

| | before (bug) | after (fix) | Δ |
|---|---|---|---|
| Sharpe — point [CI] | 0.605 [0.245, 1.018] | 0.843 [0.437, 1.227] | +0.238 |
| Sortino — point (ci_low) | 0.796 (0.321) | 1.139 (0.571) | +0.342 |
| CAGR | 6.27% | 9.18% | +2.91pp |
| Max drawdown | −45.73% | −33.83% | 11.90pp shallower |
| days with negative cash | 9.3% | 7.2% | |
| trades canon md5 | `92f6a52e…` | `f72672f4…` | arms differ |
| census | CANONICAL † | CANONICAL † | |
| bootstrap | block 19, n 500 ‡ | block 19, n 500 ‡ | |
| run · commit · started | `4e963bf3` · `0f54716` · 09-30 19:55 | `0a36df9a` · `5c05b65` · 10-08 19:28 | |

**The paired test** was pre-registered before it was computed
(`docs/Measurements/2026-09/rr1_rescore/PAIRED_TEST_PREREG.md`, N_trials 0). It is a moving-block
bootstrap with the **same** resampled block starts applied to both arms: block 19, 1,000
iterations, seed 0. The two per-arm CIs overlap, and overlapping CIs say nothing about the
difference; only a paired resample does. **Sanity gate first:** each arm's recomputed Sharpe
and Sortino reproduce the recorded values to 6 decimals, so these are the controller's own
series.

| statistic | point | 95% CI | resamples with Δ ≤ 0 |
|---|---|---|---|
| ΔSharpe (after − before) | **+0.238** | **[−0.058, +0.508]** | 6.1% |
| ΔSortino | +0.342 | [−0.062, +0.723] | 5.4% |

**What this says.** On this book, over 26 years, the point estimates favor the fix on Sharpe,
Sortino, CAGR and drawdown together. That agrees in sign with the 2021 fixture (§3) and runs
**against** the brief's expectation that free leverage had flattered the numbers. Under
`[NN-SHARPE-CI]` the direction is **not established**: both CIs include zero.

**What it does not say.** It is one cell. It does not rehabilitate 0.751 or quote either arm
as a headline (*On the anchor*). It does not convert any §5 verdict back from UNTESTED. And it
does not explain the mechanism: why correct sizing raised a 26-year Sharpe was not decomposed
here, and no cause is asserted.

**Secondary check: the June cloud anchor.** The local before arm does **not** reproduce
`158fe678` (0.751 / ci_low 0.382 / CAGR 7.3% / MDD −33% on 2026-06-14). As stated under *Why
"before" is re-run*, this cannot separate substrate drift from a local-versus-cloud difference,
and it does not affect the pair.

Analysis: `scripts/rr1_paired_delta.py anchor` → `anchor26_paired_delta.json`.

### Result — the three T-196 feature pairs (2012 → 2024)

**No feature-pair difference is established at 95%. The baseline book moves the opposite way
from the anchor.** All six cells ran on `12708e9` and finished `ok`, each with one error-free
row and the candidate census PASSED. The baseline book is identical in every cell of an arm
(1.2443 before, 0.9207 after), as it must be.

| feature (registry id) | baseline Sharpe | with-candidate Sharpe | contribution | first failed gate |
|---|---|---|---|---|
| `triple_witching_premium` | 1.244 → 0.921 | 1.336 → 1.113 | +0.091 → **+0.192** | gate 1 → **gate 3** |
| `january_effect` | 1.244 → 0.921 | 1.224 → 0.971 | −0.020 → +0.051 | gate 1 → gate 1 |
| `mom_12_1` | 1.244 → 0.921 | 0.877 → 0.856 | −0.367 → −0.064 | gate 1 → gate 1 |

The paired test is Part 2 of the pre-registration, written before any series existed. It uses
the same block starts for all four series of a pair (block 19, 1,000 iterations, seed 0) over
3,269 common days. **Sanity gate first:** all twelve series reproduce their recorded Sharpe to
6 decimals.

| pair | Δ with-candidate Sharpe | Δ contribution |
|---|---|---|
| `triple_witching_premium` | −0.223 [−0.565, +0.126] · 88.2% ≤ 0 | +0.101 [−0.267, +0.505] · 30.6% ≤ 0 |
| `january_effect` | −0.253 [−0.669, +0.146] · 88.4% ≤ 0 | +0.071 [−0.251, +0.378] · 34.4% ≤ 0 |
| `mom_12_1` | −0.021 [−0.321, +0.301] · 55.9% ≤ 0 | +0.302 [−0.182, +0.792] · 9.9% ≤ 0 |
| **Δ baseline Sharpe** (the same book in all three) | **−0.324 [−0.696, +0.044]** · 95.0% ≤ 0 | |

**What this says.**

1. **The 2012–2024 baseline book moves DOWN under the fix**: −0.324, with the CI's upper end at
   +0.044. That is the opposite sign to the 26-year anchor (+0.238), and, like the anchor, it is
   not established at 95% (only just). **The direction of RR-1's effect on Sharpe is not one sign
   across the two measured books.** The two differ in window (2000–2025 against 2012–2024) and in
   harness: `run_isolated`'s book against `validate_candidate`'s baseline book, built by
   `run_backtest_pure`. Whether the two are the same edge set was not checked here. These records
   therefore cannot say whether the window or the book explains the disagreement, and no cause
   is asserted. The pre-registered test below holds the window fixed: the window is the likelier
   explanation, not established.
2. **All three contributions rise, but that is not three confirmations.** Δcontribution =
   Δwith − Δbaseline, and the −0.324 baseline term is shared, so most of each rise is the
   baseline falling. No contribution Δ is established.
3. **RR-1 alone changes how far one feature gets.** `triple_witching_premium` clears Gate 1 and
   robustness (survival 0.975) under the fix and dies at Gate 3, where it died at Gate 1 under the
   bug. This is a fact about the gauntlet's path, not a verdict. Gate 4 remains RR-2-affected, and
   these runs precede RR-3 (DSR at N_trials 1). It does show that the T-196 record is
   sizing-sensitive in at least one case of three, consistent with its demotion to UNTESTED (§5).
   It says nothing about the other 32 features.

### Window vs book — the anchor pair on the feature pairs' days

This test was motivated by the disagreement above. It was pre-registered and committed
**before** it was computed (`WINDOW_VS_BOOK_PREREG.md`, `748cc4c`, director ruling 2026-10-14).
It holds the window fixed: the anchor's recorded series restricted to the feature pairs' 3,269
days, against the foundry baseline book on the same days. All four series share the same block
starts (block 19, 1,000 iterations, seed 0). N_trials 0.

**Gates, all passed.** Both anchor arms reproduce their recorded Sharpe to 6 decimals. The foundry
baseline column is identical across the three cells in each arm and reproduces its recorded
Sharpe. All 3,269 days are present in both anchor arms; none is missing.

| statistic | point | 95% CI | resamples ≤ 0 |
|---|---|---|---|
| **D** = ΔSharpe_anchor(window) − ΔSharpe_foundry | **+0.256** | **[−0.192, +0.793]** | 11.1% |
| ΔSharpe_anchor on the 3,269 days | −0.068 | [−0.473, +0.422] | 54.6% |
| ΔSharpe_foundry (check: equals §4's −0.324) | −0.324 | [−0.696, +0.044] | 95.0% |

**Reading: row 3 of the pre-registered order, applied mechanically.** D's CI includes 0, and
the anchor's point on the window is ≤ 0. **The window is the likelier explanation:** on
2012–2024 the anchor book no longer moves up under the fix. Its +0.238 over 26 years owes
something to the years outside 2012–2024. Not established at 95%.

**Observation, not a reading.** "Moves the same way" is weak here. The anchor's Δ on the window
is close to zero, with 54.6% of resamples ≤ 0, not comparable to the foundry book's −0.324. The
point gap D (+0.256) is not established either. Which years outside 2012–2024 carry the anchor's
positive Δ, and why, was not measured; no mechanism is asserted.

Analysis: `scripts/rr1_window_vs_book.py` → `window_vs_book.json`.

Analysis: `scripts/rr1_paired_delta.py feature` → `<cell>_paired_delta.json`. The proof of
hook inertness, the uncaptured proof record (row identical to the captured re-run, `wall_s`
excepted), is in `inertness_proof/`.

### Acceptance evidence — read this before any 26-year number

**The harness would have faked a null result, and this is how it was ruled out.**
`run_isolated.main()` re-execs itself: its first line (`:397`) is
`_reexec_if_hashseed_unset()`, which calls `os.execv` unless `PYTHONHASHSEED=0` and four
BLAS pins are already set. An exec *replaces* the process, so it discards everything done
in-process — including the before arm's restored getter — and the new process loads the
**fixed** controller from disk. Without the environment set, the before arm silently runs
the after code, the two arms come out identical, and the RE-SCORE reports **"the fix changes
nothing"**: a confident null manufactured by the harness, not the measurement.

It surfaced when two calibration records vanished with no traceback — the driver's
`finally` did not run, `atexit` did not run, and neither `os._exit` nor `sys.exit` was called,
because the process had been replaced rather than exited. The driver now **refuses** (exit 4)
unless the full environment is present, and the campaign exports it before Python starts.
Refuse, not warn: this failure reads as a result.

**Proven by execution inside a real `run_isolated` cell (Q1 2021):**

| run | Sharpe | CAGR | trades canon md5 |
|---|---|---|---|
| after #1 | 0.675 | 15.34% | `9930382f…` |
| **before** | **0.646** | **15.42%** | **`8df37066…`** |
| after #2 | 0.675 | 15.34% | `9930382f…` |

- **The arms differ** — distinct trade logs — so the before patch takes effect. Had the
  re-exec fired, these rows would be identical.
- **Determinism ×2 holds on both arms**: the two after runs are bitwise identical, and the
  before canon `8df37066` reproduced on a separate run.
- **The before arm is `main`**: a patched run reproduces `main`'s golden master
  bit-for-bit (Sharpe `0.04946327837452345`, 171 trades, identical turnover and max position),
  pinned in a slow test against constants.

Determinism ×2 was run on this short cell, **not** on the 26-year cells — at ~4h per cell a
full ×2 there was not affordable locally. That is stated here rather than implied for all.

### The cells

| cell | harness | before (bug) point / ci_low | after (fix) point / ci_low | census | bootstrap n |
|---|---|---|---|---|---|
| 26-yr baseline (2000-01-01 → 2025-12-31) | `run_isolated` | 0.605 / 0.245 | 0.843 / 0.437 | † CANONICAL | 500 ‡ |
| T-196 `triple_witching_premium` (2012 → 2024) | foundry harness | contrib +0.091 | contrib +0.192 | † PASSED | paired, 1,000 |
| T-196 `january_effect` | foundry harness | contrib −0.020 | contrib +0.051 | † PASSED | paired, 1,000 |
| T-196 `mom_12_1` | foundry harness | contrib −0.367 | contrib −0.064 | † PASSED | paired, 1,000 |

The feature ids are the registry's own. This table first named two of them `triple_witching`
and `january`, which select **nothing**; see *The feature cells' first attempt* below. The cell
labels (`t196_triple_witching`, `t196_january`) keep the short names so records stay findable.
The foundry harness reports point Sharpes only, with no per-arm CI. Each feature pair gets the
same pre-registered paired test as the anchor (Part 2 of the pre-registration).

† **Each cell runs under `CENSUS_EXPECTED_DORMANT=news_sentiment_edge`.** For the baseline
cell, the verdict reads "CANONICAL under CENSUS_EXPECTED_DORMANT=news_sentiment_edge" or
"NON-CANONICAL under …", taken from `run_isolated`'s own exit code. **For feature cells, the
exit code is not a verdict.** The foundry harness returns 0 unconditionally. What runs on that
path is `validate_candidate`'s Gate-1 *candidate* census, whose failure raises and lands as a
row error. A feature record therefore reads "candidate census PASSED (validate_candidate
Gate-1 assert_census …)" only when every row is error-free; the full-book census does not run
there. The condition travels with the number. It is the
census's own documented per-run switch (`core/census.py:25,93`), used for these eight cells
only: not a standing exemption and not an allowlist edit, and both arms carry it identically.

The justification is that the edge is **trade-inert**, shown from run `b3f03d85`
(after-arm, calendar 2021):

- `edge_signal_counts` contains `'news_sentiment_edge': 0` and **no `news_sentiment_v2`
  entry at all** — the edge runs under neither name;
- **0** rows of `trades.csv` attribute to it.

The cause is defect N-10: `alpha_settings.json` weights `news_sentiment_edge`, but the only
class declares `EDGE_ID = "news_sentiment_v2"`. Four other zero-signal edges
(`growth_sales_v1`, `macro_real_rate_v1`, `value_deep_v1`, `value_trap_v1`) are already on the
expected-dormant allowlist; this is a fifth, missing from it. **Correcting N-10 is not
neutral** — it would turn the edge live at weight 0.5 and change trades — so N-10 stays
untouched until all eight cells finish.

‡ **The controller's bootstrap runs at 500 iterations**, overriding the 1,000 default in
`MetricsEngine.bootstrap_distribution` (`backtest_controller.py:1176,1180`);
`[NN-SHARPE-CI]` names 1,000 as the standard. This is precision, not bias, and both arms share
it, so the pair stays valid. It is deliberately **not** changed here — that would confound
the RE-SCORE — and has its own item, sequenced after this campaign and bundled with RR-5.

**The T-196 cells measure RR-1's effect on the features' numbers only.** Their gauntlet
pass/fail verdicts remain affected by RR-2 (Gate 4 forced false), which this branch does not
fix. Read the numbers, not the verdicts.

### Execution

**Local and sequential — a recorded deviation from CLAUDE.md's cloud default.** The
documented path builds two ~8 GB images; after the 2026-09-30 restart Docker was down and the
disk was at 95% (11 GB free), and this host has broken a config restore by filling its disk
before. The director ruled local. Both harnesses write this worktree's live governor files on
entry, so cells run strictly one at a time. Each runs under `caffeinate -i`; the campaign
stops on any non-zero exit and refuses to start a cell below 5 GB free. A cell writes about
1.9 MB per simulated year, so the campaign itself is no disk risk.

Driver: `scripts/rescore_rr1.py` · campaign: `scripts/run_rr1_rescore_campaign.sh` · records:
`docs/Measurements/2026-09/rr1_rescore/` · logs: `data/logs/rr1_rescore/` in C's worktree. The
campaign was first logged under `/tmp/rr1_rescore_logs/`, which macOS purges after three days;
that path is stale.

### Provenance — who ran what, on which code

The campaign ran in C's worktree (`trading_machine-agent-c`) throughout, but not always under C:

| when | cell | run by | commit |
|---|---|---|---|
| 09-30 19:55 → 22:34 | anchor26 / before | C | `0f54716` |
| 09-30 → 10-08 | *stopped* — the host disk filled (iOS Simulator runtimes); no agent window existed for the week | — | — |
| 10-08 19:28 → 22:23 | anchor26 / after | the director, as caretaker of C's campaign | `5c05b65` |
| 10-08 22:23 | t196_triple_witching / before — **FAILED**, 0 features | the director | `5c05b65` |
| 10-13 20:02 | the same cell re-run — **FAILED** identically, log now persistent | the director | `5c05b65` |
| 10-13 20:08 → 22:22 | proof cell, corrected id, no capture: one error-free row | C | `5c05b65` |
| 10-13 22:22 → 10-14 00:30 | the same cell WITH capture: row identical bit for bit, so the hook is inert | C | `12708e9` |
| 10-14 00:30 → 12:35 | the remaining five feature cells: all `ok` | C | `12708e9` |

**One code state throughout.** `0f54716` and `5c05b65` differ from each other only in docs. The
feature cells after the proof run on `12708e9` (branch `rr1/rescore-series-capture`, off
`5c05b65`), whose diff is `scripts/rescore_rr1.py` alone: capture plus record-labelling (below).
On `main`, that file arrives as `130f2fa`, a byte-identical cherry-pick.
It is **proven inert by execution**: the captured re-run's scalar row must equal the uncaptured
proof row bit for bit, or the campaign stops. The runs import C's tree, not `main`. The driver
puts its own repo first on `sys.path`, and the shared venv has no editable install. RR-3's
merged changes (`mbl_gate`, `discovery`, `mode_controller`) are deliberately **not** in these
runs, so the eight cells share one code state.

### The feature cells' first attempt — a manufactured null, refused

The first feature cell asked the foundry harness for `triple_witching`. No registry feature
has that id (`triple_witching_premium` does), and the harness's filter selects by exact id, so
it swept **zero** features. It then printed `VERDICT: H0 — explored, nothing cleared (honest
null)` and exited 0. **A confident null over nothing.** The driver refused it only because it
required at least one harness row. The `CANONICAL` stamp on that record is itself a defect
(§6.7). Both failed records and the 10-13 log are kept, unedited, as the example
(`docs/Measurements/2026-09/rr1_rescore/failed_first_attempt/`).

Two driver changes, made before any feature result existed (`12708e9`):

- **Series capture.** The harness records only scalars. Its backtests run in memory and
  leave no run directory. Without the daily series, the paired test cannot run. The driver now
  wraps the gauntlet's first `treatment_effect_returns` call (`discovery.py:1377`), which is
  exactly (with-candidate, baseline). It saves both to `<cell>_<arm>.series.csv` and returns the
  original's result unchanged.
- **A feature cell is `ok` only** with rows > 0, every row error-free, and a series captured.
  The driver refuses to start if the cell's jsonl already exists, because the harness
  *appends*, and a re-run would silently double the rows.

### Why "before" is re-run, not copied

The anchor was measured on 2026-06-14, and the substrate has moved since (PIT universe, TR
reconciliation, T-306). Re-running both arms on today's substrate makes the pair differ only by
the fix; copying the June number would compare the fix plus four months of drift.

**The pair is the measurement.** Whether the local before arm reproduces the cloud canon
`158fe678` is a *secondary* check, reported as a labeled side-finding. If it does not, that
alone cannot separate substrate drift from a local-versus-cloud difference, and it does not
affect the pair.

### On the anchor

The 0.751 figure was later found survivorship-inflated (the honest base is ≈0.1–0.3). The
RE-SCORE of that cell measures **what the fix does to the historical anchor**. It does not
rehabilitate 0.751 as a headline, and neither of its numbers should be quoted as one.

---

## §5 — The verdict list

**Do not edit `TASK_LEDGER.md` from this list; the director does.** Every row below was
**read**, not keyword-matched. A first automated pass classified T-196 — the headline H0 the
director had already ruled UNTESTED — as "unaffected determinism" because its row mentions
bitwise reproducibility. That classifier was discarded.

### Method

A verdict is affected if its evidence is a performance number (Sharpe, ci_low, CAGR, MDD, or a
Δ of these) that was **produced by `BacktestController` or computed from a curve it
produced**. Two tests, and the second one matters:

1. **Does the harness run the controller?** — traced for every script named in the ledger.
2. **Does the verdict consume a curve the controller produced?** — a harness that never calls
   the controller can still inherit the defect by reading its output. Test 1 alone missed
   two rows (T-170, T-206).

**Paired comparisons do not cancel the defect.** It is tempting to read an overlay-vs-base A/B
as immune, since both arms share the bug. They do not share it equally: the free leverage
equals the amount deployed, so an arm that changes exposure changes the bug's contribution.
The probe shows the inflation swinging from 1.05× to 2.51× with deployment. A Δ between two
arms is the lever's effect **plus** the difference in free leverage.

**Mechanism verdicts survive.** A finding about whether code fired ("the overlay never
armed", "a dead knob", "inert when OFF", bitwise reproducibility) is invariant to sizing —
the defect is deterministic, and it does not change what executes.

### UNTESTED under corrected sizing — the controller produced the number (29)

| group | rows |
|---|---|
| Anchors and baselines | T-066, T-092, T-126, T-140 †, T-140-fu3✓ †, T-180 |
| Levers and overlays on the book (paired Δ) | T-055c, T-055d, T-055e, T-055g, T-055h, T-057, T-057b, T-109, T-118-rerun, T-120, T-121, T-128r, T-154, T-162, T-174 |
| Discovery and gauntlet verdicts | T-041b, T-122, T-129, T-144, T-145, T-196, T-241 ‡ |
| Composition | T-211 ¶ |

† **Split verdict.** The determinism claim (bitwise-unanimous N=5) survives; the anchor
**numbers** do not.
‡ **No ledger row exists** — see the scope notes.
¶ Branch-only evidence (`feature/phase1-composition-t211`); classed as affected because the
composition is applied to the book. Worth a reviewer's confirmation.

### UNTESTED by consumption — the harness is independent, the input is not (2)

| row | how it inherits the defect |
|---|---|
| **T-170** | The DBMF recommend-to-paper verdict blends DBMF against *"the T-128r 26-yr arm0 curve"* — a controller product. DBMF's crisis benefit was judged against drawdowns the free leverage deepened. |
| **T-206** | Factor decomposition takes `--book portfolio_snapshots.csv`, the file `_log_snapshot` writes. Its β +0.33 / α +2.26%/yr decomposes the inflated book. |

**T-170 is the one with live consequences:** it is the backtest rationale behind the DBMF
forward shadow now running (T-316). The shadow's own forward gates are live measurements and
stand on their own. The backtest recommendation that justified arming it does not.

### Unaffected

- **Mechanism, determinism, infra (claim invariant to sizing):** T-038-CONT, T-054, T-055,
  T-057c-det, T-069, T-103, T-106, T-116, T-118, T-118fc, T-124, T-125, T-127, T-128,
  T-128-CO, T-131, T-133, T-140-fu2, T-140-fu3, T-142, T-143, T-147, T-153, T-155, T-156,
  T-158, T-163, T-164, T-165, T-167, T-175, T-176, T-177, T-179, T-181, T-183, T-184, T-187,
  T-188, T-190, T-194, T-195, T-197, T-199, T-200, T-212, T-217, T-218.
- **Independent harness, consumes no controller output:** T-204 (trend overlay), T-213
  (industry momentum), T-239 (moonshot re-score — reads raw price files), and the
  T-306-substrate family — the sleeve (T-255, T-311), tilts (T-318, T-320) and offense (T-294,
  T-294b, T-298, T-312, T-315). **The director's ruling that these survive is confirmed at
  code level and passes the consumption test:** they run on the multi-decade substrate built
  from FF, DGS10 and LBMA data and read no equity-book curve.

### Needs a reviewer's reading (7)

T-136 (survivor-inflation quantification — harness unconfirmed), T-148 (the tax-vs-cost
channel ratio may rest on book turnover), T-166 (conditional-shelf entries may cite controller
numbers), T-169 (cites 0.751 as context), T-172 (regime OOS), T-214 and T-220 (trend-sleeve
extensions, likely independent). I did not resolve these to a confidence I would put my name
to, and would rather say so than guess.

### Scope notes — three corrections to the recorded scope

1. **Too narrow.** CURRENT_STATE records the demotion as *"T-196/215/239/241 and the
   equity-book rows of the **T-255→272** sweep."* The brief says **T-002…T-272**. The code
   shows controller-produced verdicts across T-041b→T-211 — including the 0.751 anchor itself,
   several refutations, and T-170. The T-255→272 wording appears to be a transcription
   narrowing; nearly all of the affected verdicts sit before T-255.
2. **Too wide.** **T-239** is on the recorded list but its harness is independent: it reads raw
   price files and the trend overlay, not the controller or its output. Demoting it discards a
   valid verdict. It should come off the list.
3. **Rows that do not exist.** **T-239** and **T-241** have no ledger rows. Their verdicts live
   only in scripts and audit docs, so neither can be marked UNTESTED in the ledger as written.

---

## §6 — Findings beyond the brief

### 6.1 The fix does not eliminate negative cash

17 negative-cash bars become **2** (min −$21,889, gross 1.197) — with the sizing ratio at exactly
1.000, so the survivors come from a **different mechanism**. The configured cap is
`max_gross_exposure = 1.0`, so this is a defect, not design.

Two candidates are visible **read-only** in Engine B; neither is diagnosed or touched (Engine B is
off-limits to this brief):
- The gross guard checks each order against **pre-bar** gross, so orders that each pass can sum
  past 1.0 when they fill together.
- The guard sits in a `try/except: pass` that **fails open**, logged only under a debug flag.

The brief attributes the over-gross to inflated equity. That explains **15 of the 17 bars**, not all
of them. Both residual bars (2021-10-01, 2021-10-18) were **among the original 17** — verified by an
in-memory reversion of the getter, not inferred — so there are 17 distinct bars in total, and the fix
removed 15. The remaining two want their own propose-first brief in Engine B's lane.

**Correction to commit `908518d`:** its message says the fix "explains 17 of 19 bars". That is wrong:
there is no set of 19. It is 15 of 17. The commit cannot be amended without approval (history
rewrites are propose-first), so the correct figure is recorded here, where reviewers will read it.

### 6.2 The golden master does not run by default

Covered in §3: it is `slow`-marked and deselected by `pytest.ini`. A regression gate that does
not run by default is a gate the program has been assuming rather than exercising.

### 6.3 `run_isolated`'s docstring is false

It says the re-exec is *"called only from `__main__` so importing the module (e.g. from tests)
does not trigger a re-exec."* The call is the first line of `main()`. Importing is safe;
**calling** is not. That false sentence is how this proposal nearly ran both arms on the fixed
code (§4). It is referee infrastructure, so it is not edited here; it goes to RR-7's
record-correction list.

### 6.4 The controller bootstraps at half the stated standard

See §4 ‡. Every ci_low the controller has produced — the 0.751 / 0.382 anchor included — ran at
500 iterations against the 1,000 that `[NN-SHARPE-CI]` specifies.

### 6.5 The RE-SCORE's direction is genuinely open

The fixture contradicts the brief's expectation (§3). Nothing here predicts the 26-year sign.

**Update 2026-10-13 — still open at 95%.** The 26-year anchor's point estimate agrees with the
fixture (ΔSharpe +0.238), but its paired 95% CI is [−0.058, +0.508] (§4). An early reading
recorded the sign as simply "UP". That was a point-estimate claim, and it was withdrawn under
`[NN-SHARPE-CI]`.

**Update 2026-10-14 — and not one sign.** The T-196 cells' baseline book over 2012–2024 moves the
other way: −0.324 [−0.696, +0.044] (§4). Neither direction is established on either book. The
question this section posed now has a sharper form: does the window or the book explain the
disagreement? §4 tests that directly.

**Update 2026-10-14, later — the window, more likely than the book.** The pre-registered
window-vs-book test (§4) puts the anchor book at −0.068 [−0.473, +0.422] on the foundry book's
2012–2024 days. That is pre-registered row 3: the window is the likelier explanation, not
established, with D = +0.256 [−0.192, +0.793].

### 6.6 The foundry harness fails open on an unknown feature id

`scripts/run_foundry_eval_t195.py` filters the registry by `T195_FEATURES`. An id that matches
nothing yields a zero-feature sweep, an "honest null" verdict and exit 0 (§4, *first attempt*).
Any consumer that trusts the exit code or the verdict line reads a refutation that never ran.
**Approved fix, after this campaign:** an unknown id exits 2, naming it; a zero-feature sweep
exits 3; plus a test. It goes on its own branch off `main`, so the campaign keeps one code
state. It is recorded as HIGH sub-item (18) on the alpha-frontier row, owned by C, with R
reviewing before merge.

### 6.7 The RE-SCORE driver labelled feature cells by an exit code that is always 0

My defect, in my own driver. The record's census label came from the harness's exit code,
which `run_isolated` sets meaningfully and the foundry harness never does. So a zero-row record
read `CANONICAL`. Worse, `validate_candidate`'s candidate census raises on failure, and the
harness catches every exception into `row["error"]`, so a census-failed candidate would also
have read `ok` and `CANONICAL`. Fixed in `12708e9` before any feature result existed. The two
FAILED records keep their wrong labels as archived examples; they are not corrected in place.

---

## §7 — Provenance: the duplicate-session incident

A restart on 2026-09-30 resumed this task in two windows at once. The fix commit (`908518d`) and
the golden regeneration (`1dba3f1`) were made by the **other** instance, after the stand-down
order. On being named owner, I re-read the tree from scratch and verified both commits **cold**,
as a stranger's work, rather than on the strength of their messages:

- the fix diff read line by line (getter returns cash; zero `capital` writes remain; cash init
  kept at both sites; xfail marker removed on the targeted test only);
- the probe re-run on HEAD (0/251 divergent; the 2 residual bars reproduced exactly);
- the golden test run **explicitly** on HEAD (passes), with the input hash and signals confirmed
  unchanged;
- the default tier (3,943 / 0 failed) and slow tier (4/4) both run.

Both commits hold. The other instance's rewrite of the probe — a verdict that detects which side
of the fix it is reading — is kept, per the director's ruling. The before/after probe logs in §1
come from runs this instance observed directly.
