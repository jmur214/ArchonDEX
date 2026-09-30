---
task_id: RR-1 (alpha-frontier program §3.1)
title: Backtester sizes from a frozen capital figure — repair proposal
date: 2026-09-30
author: Agent C
branch: fix/referee-rr1-sizing-capital
type: REFEREE REPAIR PROPOSAL — propose-only. The referee is never autonomously modified.
route: Agent R (independent review) → director → the USER rules on merge.
n_trials: 0 — a correction, not a hypothesis. Every re-run below is labeled RE-SCORE.
status: §1-3, §5, §6 COMPLETE. §4 RE-SCORE PENDING (cloud campaign, not yet run).
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

## §4 — RE-SCORE — **PENDING (not yet run)**

Nothing in this section is a result. The table exists so the cells are fixed before any
number arrives.

| cell | config | before (bug) point / ci_low | after (fix) point / ci_low |
|---|---|---|---|
| 26-yr equity baseline | `158fe678` (the GOAL.md 0.751 / 0.382 anchor, T-140-fu3✓) | — | — |
| T-196 foundry: `triple_witching` | T-196 harness, `run_isolated.py` | — | — |
| T-196 foundry: `january` | T-196 harness | — | — |
| T-196 foundry: `mom_12_1` | T-196 harness | — | — |

**Why "before" is re-run, not copied.** The anchor was measured on 2026-06-14. The
substrate has moved since (PIT universe, TR reconciliation, T-306). A paired comparison
re-runs both arms on the current substrate, differing only by the fix; copying the June
number would compare the fix plus four months of substrate drift.

**Execution.** Eight cells (four configs × before/after), each a long backtest — above the
CLAUDE.md threshold, so the campaign goes to AWS Batch via `scripts/submit_substrate_run.py`
per `docs/Cloud/CLOUD_USAGE.md`, on the research queue (not the paper fleet).

**On the anchor.** The 0.751 figure was later found survivorship-inflated (the honest base is
≈0.1–0.3). The RE-SCORE of that cell measures **what the fix does to the historical
anchor**. It does not rehabilitate 0.751 as a headline, and neither of its numbers should be
quoted as one.

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

### 6.3 The RE-SCORE's direction is genuinely open

The fixture contradicts the brief's expectation (§3). Nothing here predicts the 26-year sign.

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
