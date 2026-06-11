---
task_id: T-2026-06-10-143
title: Crisis-replay harness — the locked T-118b pre-registration as tested code (fixture-only)
date: 2026-06-10
substrate: n/a (analysis harness + synthetic fixtures + SPX TR market data for the derivation check; ZERO contact with campaign artifacts; zero N_trials)
scope: scripts/ + tests/ only; the registration governs — no thresholds invented, ambiguities resolved per its §6 less-favorable rule and documented here
outcome: **Delivered, with a material registration finding.** (1) All 9 locked criteria (v1 i–iv + addendum v2 OOS/terminal-wealth/3×-ratio/GFC-floor) implemented with a values-shown verdict line; primary-config-only gating; 23 fixture tests green incl. the v1-hole regression (net-negative-but-MaxDD-passing overlay now FAILS, and explicitly does not escape to PARTIAL). (2) **STOP-REPORT FINDING: the locked episode list is NOT mechanically derivable from the locked rule on real S&P 500 TR data under ANY consistent reading** — 2011 requires a local-peak reading, every local-peak reading admits the omitted 2010 correction (−15.6% TR) and fragments dotcom/GFC/2022, the strict reading re-dates dotcom's peak to 2000-09, **and a 2025-02→04 episode (−18.7% TR) clears the threshold under every reading but is on no list and predates the registration** (so the §1 auto-append clause does not cover it). The gate ships on the locked set via rule-ambiguity-free month-pinned date-fixing; the director must adjudicate the episode-list defect PRE-unblinding.
---

# T-143 — Crisis-replay harness (T-118b pre-registration → tested code)

## Headline

The post-relaunch analysis is now push-button:

```
python -m scripts.crisis_replay_t118b \
    --on <overlay_on.csv> --off <overlay_off.csv> \
    --spx <sp500_tr.csv> --primary-config
```

prints per-episode ΔMaxDD/ΔTotalReturn/Δvol/days-to-de-gross with
within-episode block-bootstrap CIs (5d and 10d blocks), the
in-sample/OOS split, calm-drag with stationary-bootstrap 90% CI, the
Bayesian credible interval and exact binomial sign-test p (both
descriptive), and a single verdict line showing **every criterion's
value next to its locked threshold**. Implementation cannot quietly
drift from the registration: every threshold is a named constant
transcribed from the locked doc, and 23 fixture tests pin the behavior
— including the regression that proves the addendum closed the v1 hole.

**Zero contact with real campaign artifacts** (T-143 hard constraint):
no S3 reads, no T-118 cell outputs, nothing overlay-related beyond the
registration doc. Inputs were synthetic fixtures plus S&P 500 TR market
data for the episode-derivation check the brief itself mandates. The
first real-data run is director-executed post-relaunch.

## THE FINDING — the locked episode list is not mechanically derivable

The brief: *"must reproduce the locked actionable set … if your
mechanical derivation disagrees with the locked list, STOP and report
(that's a finding about the registration, not something to patch
silently)."* It disagrees, in four compounding ways, verified on BOTH
the on-disk TR proxy (Stooq dividend-adjusted SPY, 2005-02→2026-05) and
the actual S&P 500 TR index (^SP500TR, 1999-01→2026-05; fetched to /tmp
for this check only, nothing committed):

1. **The rule "S&P 500 TR peak-to-trough DD ≥ 15%" is underspecified,
   and no consistent reading yields the locked set.**
   - *Strict all-time-high reading*: 2011 does NOT exist — on a TR
     basis the market had not regained its 2007-10 peak until ~2012, so
     2011's −18.6% nests inside the unrecovered GFC spell. Worse, the
     TR all-time high before the dotcom crash was **2000-09-01**, not
     the locked 2000-03 peak month. Derived set: {dotcom@2000-09, GFC,
     2018Q4, COVID, 2022, 2025}.
   - *Local-peak (zigzag, ±15% confirmation) reading*: admits 2011 ✓
     but also admits the omitted **2010-04→07 correction (−15.6% TR)**,
     and fragments dotcom into four sub-episodes, GFC into three, 2022
     into two (the bear-market rallies of 2001, Nov-2008 and Jun-2022
     all exceeded +15%), re-dating the locked troughs.
2. **2025-02-19 → 2025-04-08 (−18.7% TR) clears the threshold under
   EVERY reading** — and it happened ~14 months BEFORE the
   registration, so §1's "post-registration drawdowns append
   automatically as out-of-sample" clause does not cover it. The
   addendum's "honest re-derivation over 2000-2025" missed it (and
   2010).
3. dotcom is additionally **underivable from on-disk data** (the
   longest local TR-flavored series starts 2005-02; the ^SP500TR check
   required an external fetch).
4. The locked GFC/2022 trough months (2009-03, 2022-10) match the
   strict reading but NOT the local-peak reading (2008-10/2008-11
   splits; 2022-06/2022-10 splits) — so even "which trough" is
   rule-dependent.

**Resolution shipped (lock-respecting, no silent patch):** the
registration's own §1 says the episode SET is locked and only the
*exact trading days* are fixed mechanically at analysis time. The
harness therefore pins dates by **month-anchored day-fixing** — peak =
TR maximum within the locked peak month, trough = TR minimum within the
locked trough month, end = trough + 20 trading days — which is fully
mechanical GIVEN the set and has zero rule ambiguity. On ^SP500TR this
pins all six locked episodes cleanly (dotcom 2000-03-24→2002-10-09
−47.4%, matching the addendum's "~−47%"; GFC −55.3%; 2011 −18.6%;
2018Q4 −19.4%; COVID −33.8%; 2022 −24.5%). The honest-derivation check
(`check_mechanical_derivation`, both rules) runs alongside and prints
any divergence as a finding, never patching the set.

**Director adjudication needed PRE-unblinding** (the campaign is still
blind, so a clarifying amendment is legitimate): (a) amend the
registration to state the set is curated with month-pinned mechanical
date-fixing (drop the claim that the set falls out of the 15% rule);
and (b) decide 2025's status — adding it as a 6th actionable episode
TIGHTENS (more OOS evidence: the overlay's HMM had data through
2025-04; sign test would need re-locking, e.g. ≥5/6) but any change
must happen before unblinding or not at all. 2010 likewise (in-sample,
−15.6%, borderline). The harness takes the episode set as data — it
supports either outcome unchanged.

## What was built

`scripts/crisis_replay_t118b.py` (importable module + CLI):

- **Locked constants block** — every threshold transcribed with its
  registration section reference; `LOCKED_EPISODES` with
  actionable/OOS/blind tags (gate = {GFC, 2011, 2018Q4, COVID, 2022};
  in-sample {GFC, 2011, 2018Q4} vs OOS {COVID, 2022}; dotcom
  reported-blind, never gated).
- `derive_episodes_mechanical(rule="alltime_high"|"local_peak")` — both
  readings of the ambiguous rule (the checker), open in-progress
  drawdowns emitted.
- `pin_locked_episodes` — the month-anchored date-fixing the gate uses.
- `check_mechanical_derivation` — matched/missing/extras report.
- `evaluate_crisis_replay` — §2 per-episode metrics (ΔMaxDD,
  ΔTotalReturn, Δrealized-vol, days-to-de-gross via the T-124
  gross_notional column), §3 aggregation (median; sign-count with exact
  binomial p reported descriptively; within-episode circular block
  bootstrap at 5d AND 10d blocks, never across the full sample;
  conjugate-NIG Bayesian 90% CrI on mean ΔMaxDD, descriptive), §4
  calm-drag (non-episode days = complement of the UNION of all reported
  episode windows — the less-favorable choice; annualized CAGR diff +
  Politis-Romano stationary-bootstrap 90% CI, mean block 10d, seed 0),
  v2 criteria (OOS-both-improve; terminal wealth on ≥ off; 3× ratio;
  GFC ≥ +5pp), and the §5 verdict.
- `format_report` — the values-shown output.

### Operationalizations (registration silent; §6 less-favorable rule applied; all documented in code)

| Choice | Operationalization | Why |
|---|---|---|
| (v2-c) "episode-frequency-annualized crisis benefit" | Σ actionable-episode ΔTotalReturn-pp ÷ full-window years; drag = max(0, −calm diff); drag=0 ⇒ benefit must be ≥ 0 | return units per the addendum's own framing ("return-units benefit floor") |
| (iv) single-episode share | denominator = NET ΣΔMaxDD (harsher than positives-only); net ≤ 0 ⇒ criterion fails outright | less favorable to the overlay |
| PARTIAL vs FAIL | PARTIAL = (i) median + (iii) calm hold AND all v2 co-equal criteria hold (only the trigger-tunable (ii)/(iv) failed). Any failed v2 criterion ⇒ FAIL | the brief's explicit adjudication: the v1-hole must FAIL, not escape to "iterate parameters" |
| days-to-de-gross reference | from episode peak (artifact schema carries no signal column); trigger = gross(on)/gross(off) < 0.75 | mechanism commentary only — never gates |
| calm-day set | excludes the union of ALL reported episodes (incl. blind/extras) | crisis residue may not contaminate the calm-drag estimate |
| "CI excluding −80bps" | 90% CI lower bound > −80bps | the only direction that can co-exist with the −40bps point test |

## Fixture tests (23, all green; right answers known by construction)

- **HELPS** (declines halved, V-recovery kept, de-gross visible, calm
  identical) → PASS, all 9 criteria green, days-to-de-gross detected,
  splits populated, verdict line carries every criterion.
- **BLEEDS** (−7bp/day calm gap, episodes untreated) → FAIL; calm point
  AND CI criteria fail; no episode benefit.
- **V1-HOLE — the key regression**: declines only slightly shallower
  (GFC ΔMaxDD ≈ +6pp; median ≥ +3pp; sign 5/5; calm zero; share ≤ 50% —
  every v1 criterion PASSES) while the overlay sits out every
  +300bp/day V-recovery → window returns and terminal wealth net
  negative. v1 would have PASSED this; under v2 it **FAILS** via
  terminal-wealth + ratio, and asserts it does NOT land on PARTIAL.
  Geometry note: the hole is only constructible when recoveries are
  sharp — the bleed budget inside a window is bounded by the ΔMaxDD
  margin, so the forgone V-recovery is what produces net-negative
  returns. (First construction attempt bled the tail hard and
  ACCIDENTALLY improved terminal wealth — halving a 355-day GFC decline
  dominates any 20-day bleed. The committed fixture uses the correct
  geometry.)
- **PARTIAL**: GFC + both OOS episodes treated, two in-sample episodes
  untreated → sign test 3/5 fails, (i)+(iii)+v2 all hold → PARTIAL.
- **Primary-config rule**: non-primary label → verdict SENSITIVITY,
  metrics still reported, multiplicity note attached.
- **Derivation units**: both rules find exactly the qualifying
  synthetic dips (a 13% dip correctly never qualifies); in-progress
  end-of-data drawdowns emit; +20td window extension exact;
  month-pinning pins all six locked episodes on a covering series and
  reports dotcom uncoverable on a 2005-start series; divergence checker
  reports extras/missing without patching.
- **Determinism**: repeat evaluations bitwise-equal criteria (seeded
  bootstraps); report formatting sections present.

Full suite: **2183 passed**; the same 5 failures as this morning's
T-139/T-141 runs, all pre-existing on origin/main (stash-verified
2026-06-10). Zero new failures.

## What the director runs post-relaunch

1. Export per-bar artifacts (date, equity, gross_notional) for the
   PRIMARY config's overlay-on and overlay-off 26-yr cells.
2. One command (above) with `--spx` pointing at an S&P 500 TR series
   covering 1999→present (note: no on-disk series currently does —
   flagged; the ^SP500TR fetch is one line and should be CACHED into
   the repo data tree as a deliberate substrate addition, or the
   episode dates can be pinned from any covering series once).
3. Read the verdict line; the frozen T-118 gate is still reported
   FIRST; this analysis is the pre-registered second read (§
   "Standing relationship").

## Files

- `scripts/crisis_replay_t118b.py` — NEW; the harness (importable + CLI)
- `tests/test_crisis_replay_t143.py` — NEW; 23 fixture tests
- this audit

## NOT done (out of scope / forbidden)

- Any real-data run (director-executed post-relaunch; unblinding discipline)
- Any registration edit (findings reported for director adjudication)
- Caching the ^SP500TR series into the repo (substrate addition = deliberate, manifest-pinned step)
- Episode-set changes (2025/2010 are the director's pre-unblinding call)
