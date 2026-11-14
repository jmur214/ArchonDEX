# Proposal: a distribution guard in the `era_tr` writer (T-393) — v5 = v4 + the guard

**For:** the director, then **the USER** (the user adopted (a′) v4 on 2026-11-12; v5 corrects it —
`[NN-SUBSTRATE-REVERIFY]`). **Status:** §1 PRE-DECLARED, committed alone before any code. **N_trials: 0.**

**The defect** (health HIGH, main `d170129`; found by T-390, confirmed by its reviewer by execution):
`engines/data_manager/era_tr.py` adds a reference dividend whenever the probe reads m ≥ 0.5. It has no
upper bound on m and never checks that the reference's own `close` fell. yfinance applies some spin-offs as
a split in `close` AND as a dividend in `adj_close`, so the writer adds distributions that never reduced
the price (DHR 2016: v4 +75.38 % against raw Stooq +12.75 % and T-265 +12.71 %).

---

## §1. The rule and its acceptance — PRE-DECLARED

### 1.0 What was measured before this section (design inputs; no v5 file, no acceptance run)

On v4's 34,575 labelled ex-dates (11,096 added), the pinned yfinance cache and raw Stooq:

- **m of the measured "missed" labels (9,602) is tight around 1.** Quantiles: 1 % 0.873, 5 % 0.946,
  median 1.000, 95 % 1.052, 99 % 1.110, 99.9 % 1.569. Twenty exceed 1.25 and ten exceed 1.5: ADBE
  2005-03-24 (1.76), ATO 2010-08-23 (1.83), STE 2010-08-20 (1.87), ADM 2006-05-17 (1.88), TGT 2007-08-16
  (1.88), ABT 2004-05-03 (1.93), CNP 2002-10-01 (2.62), XRX 2017-01-03 (4.01), SPG 2009-08-13 and
  2009-11-12 (4.77, 4.75). 34 lie in [0.5, 0.75).
- **The close's ex-day move is calibrated for ordinary dividends, and powerless for small ones.**
  q = −log(1 − D/P_prev); r = the reference close's log return on the ex-date bar; σ = the robust daily σ
  of that close's returns away from ex-dates (±127 bars, 1.4826 × median |r|).
  - Where q is 1–5 σ, the median market-relative move is −0.93 to −1.03 q: a real dividend shows its drop.
  - But 99 % of added dividends have q < 2.3 σ. A bare "the drop is rejected" test (z = (r + q)/σ > 3)
    refuses 31 dividends, 27 of them small ordinary ones on a strong up-day (TGT 2009, JNJ 2003, PFE 2006,
    CAT 2003 …). So the test must state its own power.
- **Where q ≥ 4 σ (23 added distributions) the ex-day evidence splits in two, with a gap.** f = r/q:
  - **f ≥ −0.10 (the close did not fall):** MMM 1996-07-16 (−0.10, z 4.0), SRE 2006-09-06 (0.00, z 5.2),
    HPQ 1972-10-04 (+0.05, z 6.8), DHR 2016-07-05 (+0.08, z 77), ETN 2001-01-02 (+0.18, z 11.7),
    ABT 2004-05-03 (+0.38, z 8.4), XRX 2017-01-03 (+1.30, z 26).
  - **f ≤ −0.38 (the close fell by a third to all of D/P):** SPGI 2012 (−0.38), **PEP 1997-10-07 (−0.44,
    z 2.4)**, BAX 1996 (−0.55), VRSN 2011 (−0.56), **AN 1995-04-27 (−0.61, z 2.1)**, HPQ 2000 (−0.67),
    JCI 2016 (−0.72), A 2006 (−0.73), WYNN 2010 (−0.74), XOM 1982 (−0.75), AIG 2011 (−0.89), then
    PGR 2007, BBWI, HCA, TDG at −1.0 to −1.45.
- **This contradicts three of the brief's nine named cases, and one of my own T-390 rows.**
  - **PEP 1997** sits between SPGI 2012 and VRSN 2011, both real cash specials, and next to JCI 2016,
    whose drop T-265 confirms. On the ex-day its close fell 3.64 % against a D/P of 7.96 %. A rule that
    refuses PEP refuses real cash dividends.
  - **AN 1995**: the close fell 9.35 % on the ex-day (61 % of D/P). T-390's R3 called it a double count
    from a 3-day window that included an 11 % rebound. That was noise. It is not a pure double count.
  - **BAX 2000-04-03**: q = 4.4 % but σ = 2.26 % (q = 1.96 σ). The close fell 0.8 %. "Fell by D/P" and
    "did not fall" are 1.6 σ and 0.35 σ away. No rule decides it.
- **CNP 2002-10-01** is likewise not decidable by the close (q = 2.2 σ) but is far outside the m band.

### 1.1 The rule

A reference ex-date that the labels call missed is ADDED only if it passes (a) and (b). Otherwise it is
**not added** and is recorded as `refused_distribution` with its m, the close's ex-day move, σ and the
reason. Nothing is guessed in its place.

**(a) m is inside [0.5, 1.5]** (measured labels only; an unmeasured label has no m to test).
- 0.5 is the existing cut: the midpoint between "captured" (0) and "missed" (1).
- 1.5 is its mirror: the midpoint between "Stooq lacks one dividend" (1) and "Stooq lacks two" (2). Above
  it, the probe is not measuring this dividend.
- The measured distribution supports both: 99 % of missed labels lie in [0.873, 1.110].
- A measured label above 1.5 still counts as "missed" when it lends its label to an unmeasured neighbour,
  as today. Stooq did miss something there.

**(b) the reference's own close does not contradict the drop.** With q, r and σ as in §1.0:
- the ex-date is **testable** iff q ≥ 4 σ (the two hypotheses "the close fell by q" and "the close did not
  fall" are at least 4 σ apart);
- a testable ex-date is **refused** iff r > −q/2 (the close is nearer "no drop" than "the drop") AND
  (r + q)/σ > 4 (the drop is rejected at 4 σ);
- an untestable ex-date passes (b). For it, (a) is the evidence.
- There is NO size threshold. The rule is the same formula at every D/P; what varies is the name's own
  noise. MMM 1996 is refused at D/P 3.75 %; BAX 2000 is untestable at 4.33 %.
- (b) applies to every label that would be added, measured or not.

**A third label, with no price effect:** `unresolved_distribution` — an ADDED ex-date with q ≥ 2 σ whose
drop is doubtful at 2 σ ((r + q)/σ > 2) and that (b) does not refuse. It is recorded with the same
measurements so the census can say which large adds rest on a partial drop.

**The write record** of each file gains `refused_distributions` and `unresolved_distributions` (lists of
{ex_date, day, D, P_prev, m, close_move, sigma, z_drop, reason}).

### 1.2 What the rule predicts for the nine named cases (declared before any build)

| case | prediction | why |
|---|---|---|
| DHR 2016-07-05 | **refused (b)** | close +3.6 % on D/P 35.7 %, z 77 |
| ETN 2001-01-02 | **refused (b)** | close +3.1 %, z 11.7 |
| XRX 2017-01-03 | **refused (a) and (b)** | m 4.01; close +18 % |
| CNP 2002-10-01 | **refused (a)** | m 2.62; (b) untestable (q = 2.2 σ) |
| SRE 2006-09-06 | **refused (b)** | close 0.00 % on D/P 5.0 %, z 5.2 |
| HPQ 1972-10-04 | **refused (b)** | close +0.5 % on D/P 10 %, z 6.8 (a neighbour label; (a) not applicable) |
| AN 1995-04-27 | **ADDED, labelled unresolved** | the close fell 9.35 % (61 % of D/P), z 2.1 |
| PEP 1997-10-07 | **ADDED, labelled unresolved** | the close fell 3.64 % (44 % of D/P), z 2.4; same band as real cash specials |
| BAX 2000-04-03 | **ADDED, no label** | untestable: q = 1.96 σ, z 1.6 |

The brief asked that PEP and BAX be caught "by the rule, not by a cutoff", and listed AN as a pure double
count. The measured evidence does not support refusing them (§1.0). They are reported as the rule's limit,
not tuned for.

**Other label changes the rule makes, listed and justified (9 ex-dates):**
- by (b): **MMM 1996-07-16** (Imation; close −0.4 % on D/P 3.75 %, z 4.0), and ABT 2004-05-03 (Hospira;
  also (a), m 1.93);
- by (a) only, ordinary dividends whose m says Stooq lacks about two dividends, not one: ADBE 2005-03-24
  (D/P 0.02 %), ATO 2010-08-23 (1.17 %), STE 2010-08-20 (0.50 %), ADM 2006-05-17 (0.23 %), TGT 2007-08-16
  (0.24 %), SPG 2009-08-13 and 2009-11-12 (0.19 %, 0.17 %; m 4.8 — SPG paid mostly in stock that year).
  Refusing them removes an add of 0.02–1.2 % each from a bar where the probe's reading is not one
  dividend. They are labelled, and whichever way they go they stay wrong by about one dividend until
  the residual is explained.

So the rule changes **15 ex-dates** (6 named + 9) on 14 files (SPG has two), and no other label among
the 11,096.

### 1.3 The acceptance

1. **T-384 §1.1–§1.2, unchanged** (thresholds, populations, verdict), computed in memory on v5 through
   T-384's own acceptance code, reported beside v4's. Expected: still FAIL, with DHR 2016 fixed in (i).
2. **The nine named cases resolve exactly as §1.2 predicts.**
3. **Exactly the 15 ex-dates of §1.2 change label**; every other file is byte-identical to v4
   (`MANIFEST.md5`). Any other change is a failure of this unit.
4. The step audit holds on v5 (daily returns differ from raw Stooq only at v5's added ex-dates).

### 1.4 Out of scope, stated now

- **Unapplied spin-offs.** After the guard, XRX 2017, CNP 2002 and ABT 2004 are raw Stooq at those
  dates: "Stooq spin-off not applied, nothing added". Repairing them is T-390's table.
- **Partial double counts** (PEP, AN and the f ≈ −0.4 to −0.75 band): yfinance's D for a spin-off
  overstates the price drop by an amount this evidence cannot size. Labelled `unresolved`, not changed.
- The merge script, `_merge_meta.json`, post-seam rows.

---

## §2. What was built

- **The guard** is `era_tr.distribution_guard`, run at the end of `era_tr.label_exdates`. The cutover writer
  (`tr_writer.era_tr_rewrite`) and the T-384 script reach it through the same call, so there is one
  implementation. `probe_exdates` now also measures the reference close's ex-day return and its robust σ.
- **The write record** gains `refused_distributions` and `unresolved_distributions`.
- **Tests:** `tests/test_era_tr_distribution_guard_t393.py`, 10 locks. Eight plant the cases on a synthetic
  name through the real probe (pure double count, zero-move day, mis-sized spin-off, ordinary dividend on
  a 5σ up-day, real large distribution, partial drop). Each was proven by reverting its rule (8 reversion
  runs, all fail for the intended reason).
- **The byte-identity statement is restated, not deleted.** The identity "the writer equals v4 on all 575
  files" was a measurement (T-387), not a test in the suite. It now reads: 561 files equal v4's
  `MANIFEST.md5`; 14 are the declared new bytes in `config/era_tr_v5_delta_t393.json`. Two locks hold it:
  one on the config, one that rebuilds an unaffected file (KO) and an affected one (DHR) where the
  candidate is on disk.
- **Measurement:** `python scripts/era_tr_v5_delta_t393.py run` rebuilds all 575 files in memory and writes
  only the 14 changed ones to `~/Dev/_substrate_candidates/era_tr_v5_delta_t393/` (29 MB).

## §3. The result against §1.3

**Acceptance items 2, 3 and 4 hold exactly as declared.**
- 575 files rebuilt; **561 byte-identical to v4; 14 changed**: ABT, ADBE, ADM, ATO, CNP, DHR, ETN, HPQ,
  MMM, SPG, SRE, STE, TGT, XRX.
- **15 labels changed, the 15 of §1.2, and no other** among 34,575.
- The nine named cases resolve as predicted (§1.2).
- Step audit on v5: 11,081 expected steps (v4: 11,096), 0 unexpected, max deviation 9.4e-16.

**The 15 refused ex-dates:**

| file | ex-date | D/P | m | close move | σ | z | reason |
|---|---|---|---|---|---|---|---|
| DHR | 2016-07-05 | 35.7 % | 1.00 | +3.6 % | 0.62 % | 76.6 | (b) |
| ETN | 2001-01-02 | 16.0 % | 0.95 | +3.1 % | 1.76 % | 11.7 | (b) |
| SRE | 2006-09-06 | 5.0 % | 1.00 | 0.00 % | 0.98 % | 5.2 | (b) |
| MMM | 1996-07-16 | 3.75 % | 1.00 | −0.4 % | 0.85 % | 4.0 | (b) |
| HPQ | 1972-10-04 | 10.0 % | (neighbour) | +0.5 % | 1.62 % | 6.8 | (b) |
| XRX | 2017-01-03 | 13.0 % | 4.01 | +18.1 % | 1.22 % | 26.2 | (a) and (b) |
| ABT | 2004-05-03 | 6.9 % | 1.93 | +2.7 % | 1.17 % | 8.4 | (a) and (b) |
| CNP | 2002-10-01 | 10.0 % | 2.62 | +5.9 % | 4.68 % | 3.5 | (a) |
| ATO | 2010-08-23 | 1.17 % | 1.83 | −0.8 % | 0.83 % | 0.5 | (a) |
| STE | 2010-08-20 | 0.50 % | 1.87 | −1.8 % | 1.42 % | −0.9 | (a) |
| ADM | 2006-05-17 | 0.23 % | 1.88 | −4.5 % | 2.42 % | −1.8 | (a) |
| TGT | 2007-08-16 | 0.24 % | 1.88 | +2.8 % | 1.98 % | 1.5 | (a) |
| SPG | 2009-08-13 | 0.19 % | 4.77 | +0.9 % | 2.96 % | 0.4 | (a) |
| SPG | 2009-11-12 | 0.17 % | 4.75 | −0.7 % | 2.69 % | −0.2 | (a) |
| ADBE | 2005-03-24 | 0.02 % | 1.76 | +0.4 % | 1.54 % | 0.3 | (a) |

MMM passes the 4σ line by 0.02σ. It is the rule's most marginal refusal.

**12 ex-dates are ADDED and labelled `unresolved`** (a partial drop): AN 1995-04-27, PEP 1997-10-07,
BAX 1996-10-01, HPQ 2000-06-05, JCI 2016-10-31, VRSN 2011-05-05, SPGI 2012-12-14, WRB 2012-12-20,
DUK 2005-08-10, MAT 2004-12-01, AEE 2003-12-08, XOM 1984-08-07. BAX 2000-04-03 carries no label (untestable).

**Acceptance item 1 — T-384's unchanged test, v4 beside v5: still FAIL.**

| test | v4 | v5 |
|---|---|---|
| (i) failing name-years (strict passes) | 59 (1,741) | **58 (1,742)** |
| (ii) years passing | 15 of 16 (2013 p95 0.350) | 15 of 16, every year's verdict unchanged |
| (iii)(a) / (b) / (c) | 110 of 110 / 6 names fail / 14 of 14 | identical |
| (iv) bytes | 575 of 575 | 575 of 575 |

- **(i), 2 name-years move.** DHR 2016: +44.21 → +0.03 pp, now passes. XRX 2017: −27.87 → −41.74 pp,
  still fails; v5 is raw Stooq there, with the Conduent spin-off unapplied and nothing added.
- **(ii), 10 name-years move, all AWAY from yfinance**, because the reference is the series that counts
  twice or the guard declined to add: ETN 2001 (+0.83 → −16.65), CNP 2002 (−17.13 → −27.66), ABT 2004
  (−6.66 → −13.82), SRE 2006 (−0.01 → −5.17), ATO 2010 (−0.99 → −2.17), STE 2010 (−0.44 → −0.94),
  SPG 2009 (−1.35 → −1.71), ADM 2006 (−0.01 → −0.24), TGT 2007 (0.00 → −0.24), ADBE 2005 (0.00 → −0.02).
  The largest p95 change is 2006: 0.037 → 0.041.
- So the guard **costs** agreement with (ii)'s reference and **gains** agreement with (i)'s. That is the
  expected direction when the defect is the reference's.

## §4. What the evidence does not support — for the user

1. **PEP 1997, AN 1995 and BAX 2000 are not refused, against the brief.** Their closes fell 44 %, 61 %
   and 18 % of D/P on the ex-day. PEP and AN sit in the band where known-real distributions sit (SPGI
   2012 at 38 %, VRSN 2011 at 56 %, JCI 2016 at 72 % with T-265 confirming its drop). BAX 2000 is inside
   its own noise. v5 keeps v4's add for all three; PEP and AN are labelled unresolved. If they are partial
   double counts, v5 still over-counts PEP by up to 4.6 pp and AN by up to 6 pp in those years. No source
   on disk sizes it.
2. **The (a)-only refusals are a judgement the user should see.** For ATO, STE, ADM, TGT, SPG ×2 and ADBE
   the probe says Stooq lacks about two dividends where yfinance lists one. v4 added one; v5 adds none and
   labels the ex-date. Each of these name-years moves further from yfinance by one dividend (0.02–1.2 pp).
   The alternative is to add one and label. The brief specified the bound; the cost is stated here.
3. **MMM 1996 was not in the brief.** It is a tenth case of the same defect (Imation; close −0.4 % on a
   3.75 % distribution), refused at the margin.
4. **T-390's AN 1995 reversal was wrong.** Its 3-day window read an 11 % rebound as "no drop".

## §5. What this does to T-390's table

- **R3 (`double_count_reversal`) becomes unnecessary.** DHR 2016 and ETN 2001 are now never added. AN 1995
  must be DROPPED from it (§4.4). For XRX 2017 and CNP 2002, R3's positive amounts were R2's job done
  under the wrong name.
- **R2 should pick up XRX 2017, CNP 2002 and ABT 2004**, which v5 leaves as raw Stooq with the spin-off
  unapplied. As written it cannot: R2 measures the step against `adj_close`, which double-counts on those
  dates, and R2 stands down within three bars of a D/P ≥ 8 % distribution. R2 needs one change: at a
  `refused_distribution`, measure the step against the reference `close`. That is a T-390 rule change to
  pre-declare there, not here.
- R1 and the other R2 rows are unaffected: the guard changes 14 files on 15 bars.
- T-390's table was built on v4's timeline. It must be REBUILT on v5 before it is applied; its DHR/XRX/
  ETN/CNP/AN rows are void.

## §6. Cutover

- v5 needs no new step. `cutover_step1_pass era-tr` already calls the guarded module; the 14 files differ
  from v4 and the write records carry the refusals.
- The runbook's acceptance line "equals v4's processed/, aggregate md5 2cee41ef…" becomes "561 files equal
  v4; 14 equal `config/era_tr_v5_delta_t393.json`".
- **The user's decision:** adopt v5 (= v4 + this guard) as the correction to the 2026-11-12 ruling; and,
  separately, item §4.2.
