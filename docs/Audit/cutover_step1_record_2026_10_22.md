# Cutover step 1 — the record (2026-10-22; Agent B; the user's OPTION (a) ruling)

> Point-in-time record (`[NN-AUDITS-NOT-CURRENT]`). **Scope:** step 1 of the substrate cutover
> (`docs/Sources/proposal_substrate_cutover_exact_tr_2026-10-15.md` §6, step 2), under the user's
> ruling of 2026-10-22: OPTION (a) — the pre-seam drip STAYS for every file, labelled universally;
> the POST-seam span of every fetchable file is rewritten exact through the merged writer; the
> eight class (iii) and five class (iv) names keep their deep history behind a DECLARED seam; (b)
> declined; nothing fetched from Alpaca (one provider, yfinance). **Everything here happened on a
> COPY outside the repo.** The real cache was never written: its file count and aggregate md5 are
> identical before and after (§3). The real-cache write is cutover day, a separate approved act.
> **N_trials: 0** (no measurement was run on the candidate).

## 1. What the ruling required that did not yet exist, and what was built

The 2026-10-15 write pass on `processed_exact_tr_2026-10-15/` replaced files WHOLE — the provider's
exact total return over the whole span, pre-seam included — and carries no per-file write records
(it predates the level rail). That is the option (b) form. Option (a) needed a writer mode that
KEEPS the cached pre-seam bars; so step 1 built, locked and reversion-proved (§9):

| unit | what it does | commit |
|---|---|---|
| **the seam-preserving write** (`tr_writer.full_refetch(seam="auto")`) | resolves the file's seam through `seam_for` — a declared seam (`config/convention_declarations.json`), else the merge record `_merge_meta.json` under the cache (a `both` file with pre-seam bars); KEEPS the cached bars before the seam, scaled by the ratio measured AT the seam bar (the seam-day return is unchanged; the file sits at the provider's level); takes the provider's exact total return from the seam on; requires the provider to cover the POST-seam span only (what admits the (iii)/(iv) names); writes `seam` and `convention` into the pinned per-file record. A cache with no merge record has no seams to keep: whole-file, as before | `eeb6f25` |
| **the seam-ratio rail** | \|ln r_seam − ln r_tail\| within 3 rounding floors, else the cache changed convention between the seam and the 252-bar tail (a missed ex-date older than the tail reads a clean RESCALE there) — refused unless a mixed-convention declaration explains it | `eeb6f25` |
| **cache-convention defects** (`config/convention_declarations.json`) | AGG, EFA, VNQ `split_only_cache`: the cached tail must agree with the provider's SPLIT-ONLY mode AND differ from its total-return mode, then the whole span is re-fetched as total return. AMCR `mixed_convention_cache`: the provider/cache log ratio piecewise constant with a step at 2025-09-05 and 2025-11-28 and at no other date. A declaration the data no longer matches is refused ("re-rule it") | `eeb6f25` |
| **the 13 declared seams** | C, INTC, JPM, ELV, MAR, PLD, AXP, WMT (iii); CHTR, KDP, TDC, UAL, WU (iv): seam date + convention per side, each locked equal to the canonical merge record's seam; a disagreement is refused | `eeb6f25` |
| **class (i) by declaration** (`config/level_declarations.json`) | ABS, BMC, CCE, CFC, GR, HAR, MHS, NCC, TEG, TIE join SLE and POM as `reused_ticker` — refused before any provider call | `eeb6f25` |
| **BK → BNY** (`yahoo_symbols.py`) | a RENAME, landed with its class; the rails still decide (refused, §4) | `eeb6f25` |
| **SPY's whole-file override** | SPY was regenerated whole after the merge (T-167); its merge record is stale (alpaca_only from 2020-04-09 vs the file's 1993-01-29); the label reads the override, never the stale record | `eeb6f25` |
| **the universal convention label** (`engines/data_manager/convention.py`; census key `substrate_convention`) | ONE function both census producers call over the run's names: the label from the pinned write record, else the declared override, else the merge record witnessed against the run's frame; an unlabelled name FAILS the gate (invariant 10), an errored record fails under 8; the two-producer lock and the gating-key contract name the key. Canonical cache today: 730 labelled, 575 with a pre-seam drip span, 155 exact_tr whole, 0 unlabelled | `e9d75f4` |
| **`close_unadj`** | every written file carries the provider's SPLIT-ONLY close as a second column named exactly `close_unadj` (the dollar-ADV ruling; the Engine B share-sizing unit reads it), NaN only on bars the provider does not hold, never derived; the record carries its span | `84156a8` |
| **the pass driver** (`scripts/cutover_step1_pass.py`) | refuses any path that is a repo's `data/processed`; resumable; the writer's log and the PROVIDER's output UNFILTERED per file; a provider exception retried 3× with the reasons kept; `guard`, `label`, `stage` subcommands | `e5a2cd5` |

## 2. The copies (all under `/Users/jacksonmurphy/Dev/_substrate_candidates/`)

| copy | what it is | state |
|---|---|---|
| `processed_exact_tr_2026-10-15/` | the 10-15 whole-file pass (option (b) form; no `_write_records/`) | untouched by step 1; the record of that pass |
| `cutover_copy_2026_10_22_pass1_no_close_unadj/` | **pass 1**: fresh copy of the canonical, the declared paths then every file, through the option (a) writer BEFORE `close_unadj` existed | complete (§5); superseded by pass 2 because its files lack `close_unadj` |
| `cutover_copy_2026_10_22/` | **pass 2, THE CANDIDATE**: a fresh copy of the canonical (digest identical to the canonical's, 2,172 files), every file through the final writer | §5–§8 |
| `_quarantine_canonical_writes_2026_10_22/` | the two `AAPL_fundamentals.parquet` files a suite run wrote into the canonical cache tonight (§10), moved out by rename | kept, never deleted |

Logs beside the copies: `pass_<tag>.jsonl` (one row per file, the writer source's sha256 and the
worktree HEAD on every row), `write_log_<tag>.jsonl` (the writer's own records), `provider_<tag>.log`
(the provider's output, unfiltered, under each file's name), `stdout_<tag>.log`; tags `pass1_2026_10_22`
and `step1_2026_10_22`.

## 3. The real cache, never written — the proof

Method: `agg_md5.py` — every file under the directory (recursive), sorted by relative path; the md5 of
the lines `relpath<TAB>md5(content)`; the inventory TSV kept. The same method on every tree.

| tree | files | aggregate md5 | when |
|---|---|---|---|
| canonical `data/processed` BEFORE the unit | 2,172 | `672a5459ad5746675d055c21fb3ccb04` | 22:05 |
| the fresh copy for pass 1, before any write | 2,172 | `672a5459ad5746675d055c21fb3ccb04` | 22:39 (after the quarantine, §10) |
| canonical AFTER the quarantine of the suite-written file | 2,172 | `672a5459ad5746675d055c21fb3ccb04` | 22:39 |
| the fresh copy for pass 2, before any write | 2,172 | `672a5459ad5746675d055c21fb3ccb04` | 23:24 |
| canonical AFTER the unit (read 23:49, after pass 2 ended) | 2,172 | `2c2f0a3d9107e3a4f67d8470b592f12c` — **ONE file changed, `fundamentals_simfin.parquet`**: a sibling suite's SimFin panel rebuild at 23:49 (the coordinator's finding; not this unit, which never ran the data manager against the main tree) | 23:49 |
| **the canonical PRICE files, BEFORE = AFTER** | 730 `*_1d.csv` + 730 `parquet/*_1d.parquet` | identical line for line: price-set md5 `7f18799d029fb27b1264151fdec5470a`; csv-only `5e744d06405c91b5149140cec01b66b5` (`price_files_diff.py`: missing 0, extra 0, changed 0) | |
| **the candidate (pass 2) after the pass** | 2,820 (2,172 + 648 write records) | `bd05b479658c31c39c447e3365c14341` | 00:08 |

The inventories (one line per file, `relpath<TAB>md5`) and the two scripts are beside the copies:
`inventory_canonical_BEFORE_2026_10_22.tsv`, `inventory_canonical_AFTER_2026_10_22_2349.tsv`,
`inventory_cutover_copy_2026_10_22.tsv`, `agg_md5.py`, `price_files_diff.py`.

## 4. The declared paths, per name (pass 1 and pass 2 agree unless noted)

| class | names | outcome | evidence |
|---|---|---|---|
| **split-only trio** | AGG, EFA, VNQ | **WRITTEN** whole as total return under `split_only_cache`: the tail agrees with the split-only mode (APPEND), differs from the total-return mode (DIFFERENT_CONVENTION); level residual 0.0 | post-2018 annualised log return, written − old: AGG +2.87 %/yr, EFA +2.89, VNQ +3.79 (their yields) |
| **mixed cache** | AMCR | **WRITTEN** whole under `mixed_convention_cache`: steps found exactly at 2025-09-05 and 2025-11-28, none other | +0.37 %/yr post-2018 (the two missed ex-dates) |
| **ticker change** | BK → BNY | mapped `BK -> BNY (rename)`; **REFUSED** DIFFERENT_CONVENTION over 252 bars (median log ratio −0.00878, max resid 8.4e-4, slope move 8.1e-4) — the 2026-10-15 measurement reproduced; the cached BK file stays as it is (ends 2026-04-10) | the rail is not loosened |
| **class (i) by declaration** | SLE, POM, ABS, BMC, CCE, CFC, GR, HAR, MHS, NCC, TEG, TIE | **REFUSED** before any provider call (`calls == []` in the lock; no provider log entry); the copies' files are byte-identical to the canonical | SLE's lift refused by construction (`liftable: False`) |
| **the ÷10 restorations** | AZO, MTD, NVR | **WRITTEN** under `scale_defect` (level residual ln 0.1 = −2.3026, explained by the declared ratio 10.0); seam mode: 6,739 / 3,234 / 3,234 pre-seam bars kept, seam ratio 10.0 exactly | **written ÷ old = 10.000000000000 on every bar**, pre-seam and post-seam; at the evidence date 2021-06-01: AZO 141.085 → 1410.85, MTD 129.63 → 1296.30, NVR 484.102 → 4841.02; `lift_verified()` **True** for all three |
| **class (iii) declared seams** | C, INTC, JPM, ELV, MAR, PLD, AXP, WMT | **WRITTEN** in seam mode (`seam_source: declared`): pre-seam bars kept (12,678 / 12,160 / 12,678 / 6,844 / 6,098 / 6,195 / 12,160 / 12,047), pre-seam RETURNS unchanged (max \|Δ log return\| 9e-16), the post-seam span the provider's, the end extended 2026-04 → 2026-10-22; seam ratio = tail rescale (gaps ≤ 3.4e-7) | the deep history kept, the provider's shorter history never asked to cover it |
| **class (iv) declared seams** | CHTR, KDP, TDC, UAL, WU | **WRITTEN** likewise (2,009 / 2,437 / 2,594 / 3,005 / 2,839 pre-seam bars kept) | |
| **class (ii)** | DAL | WRITTEN in seam mode from the merge record's seam (9,581 pre-seam bars kept, the pre-2007 bars among them: the archived artifact, withheld at LOAD by `dal_pre2007_excluded` as before) | the span check no longer reaches the old-Delta years |
| **class (i) by the rails** | BBBY, PSKY, NFX (provider series start 2026-07: span); CPWR (DIFFERENT_CONVENTION); CA (unfetchable) | **REFUSED** by the rails, as on 10-15 | |

## 5. The full pass (pass 2, THE CANDIDATE)

From `pass_step1_2026_10_22.jsonl` (730 rows; pass 1 reads IDENTICALLY on every count):

| outcome | files |
|---|---|
| **written** | **648**: 483 RESCALED, 161 APPEND, 4 under cache-convention declarations. 563 seam-kept (456 seam 2018-01-02, 100 seam 2020-04-09, 7 other seams; 550 from the merge record, 13 declared), 85 whole-file. Every written file ends **2026-10-22**; 648 write records pinned under `_write_records/` |
| refused: class (i) by declaration | 12 (§4) — no provider call |
| refused: convention | 3: BK → BNY, CPWR, FRC → FRCB (DIFFERENT_CONVENTION over the 252-bar tail) |
| refused: span | 10: BBBY, PSKY, NFX and the seven relisted symbols AVB, EA, EQR, LEG, QRVO, SATS, WBD (the provider's series under the symbol starts 2026-07..10: a later entity) |
| unfetchable | 57 — the provider's own reasons kept unfiltered in `provider_step1_2026_10_22.log`: 44 "possibly delisted; no timezone found", 13 "possibly delisted; no price data found" |
| provider errors / retries | 0 / 0 |

\|ln level residual\| over the 648: median 0, p99 3.9e-3, max 2.3026 (exactly the three declared ÷10);
seam-ratio gap over the 563 seam writes: max 8.7e-7 (PVH), none needing a declaration. The 10-15 pass's
75 unfetchable are today 57 unfetchable + 7 relisted (span) + 11 now served (the provider's coverage
moved; every served file passed the rails).

> **Correction (a), 2026-11-04 (the follow-up builder; the three lines above kept as written):** "11 now
> served … every served file passed the rails" is FALSE. Of the 18 names that explain 75 → 57, NONE was
> served or written: **ABS, BMC, CCE, CFC, GR, HAR, MHS, NCC, TEG, TIE** (10) are class (i) by declaration,
> refused BEFORE any provider call (§4; on 10-15 the provider was asked for them and returned nothing);
> **AVB, EA, EQR, LEG, QRVO, SATS, WBD** (7) are span refusals — a later entity under the symbol — now
> DECLARED writer-side at `dd64793` (`symbol_reused_by_later_entity`; §11.2 note); **FRC → FRCB** (1)
> is DIFFERENT_CONVENTION under the rename table. 10 + 7 + 1 = 18 = 75 − 57. The written count moved
> **632 → 648 = +13 declared seams** (C, INTC, JPM, ELV, MAR, PLD, AXP, WMT; CHTR, KDP, TDC, UAL, WU — the
> 10-15 span refusals) **+ DAL** (class (ii), seam mode) **+ 4 cache-convention defects** (AGG, EFA, VNQ,
> AMCR — the 10-15 DIFFERENT_CONVENTION refusals) **− SLE − POM** (written on 10-15, class (i) by
> declaration today): 632 + 18 − 2 = 648. CPWR and BK stay refused on both passes. No provider coverage
> "moved"; reconciled against `pass_step1_2026_10_22.jsonl` and the proposal's §2b table.

**The five LEGACY-W residuals** (the rail proposal §8, ruled to be quoted beside the pass's own):

| file | 2026-10-15 ln residual | pass 1 | pass 2 |
|---|---|---|---|
| CAT | +0.0019 | +0.0019020 | +0.0019020 |
| ZTS | +0.0043 | +0.0043402 | +0.0043402 |
| LOW | +0.0048 | +0.0047887 | +0.0047887 |
| PG | +0.0075 | +0.0075018 | +0.0075018 |
| CVS | +0.0087 | +0.0087388 | +0.0087388 |

No provider revision between 10-15 and today: the values agree to four decimals; all five inside the
0.01 tolerance, written RESCALED.

**`close_unadj` coverage (pass 2):** 648 of 648 written files carry the column (the csv pair too);
the kept pre-seam bars before a provider's first bar are NaN, never derived — C 1,768 bars (before
1977-01-03), ELV 2,205, DAL 6,895 (the old-Delta years, withheld at load anyway), AXP 93, CHTR 15,
and the other declared seams likewise; at the last bar `Close / close_unadj = 1.000000` on every file
checked (a total-return close equals the print on the day it is written). A handful of files lack
exactly one `close_unadj` bar (§11.9).

**The refusals that are NEW since 10-15 (a finding, §11):** AVB, EA, EQR, LEG, QRVO, SATS, WBD — the
names the proposal recorded as "delisted between the snapshot and the pass" — now have a provider
series under the symbol starting 2026-08-14 / 08-04 / 08-17 / 08-26 / 10-02 / 10-20 / 10-05: later
entities on reused symbols. The span rail refused all seven (fail-closed), but none is yet DECLARED
class (i). FRC (→ FRCB, the rename table) is refused DIFFERENT_CONVENTION.

## 6. The stale/holed-files guard's reading (PIT; declarations as shipped)

| substrate | window | stale | holed | calendar | note |
|---|---|---|---|---|---|
| the canonical cache | 2000-01-03 → 2025-12-31 | 30 | 254 | proven both ways (6,539 days) | the baseline; formation coverage min 0.383 / median 0.699 / 208 of 312 dates below 0.80 |
| the canonical cache | 2018-01-02 → 2025-12-31 | 30 | 52 | proven (2,011 days) | |
| `processed_exact_tr_2026-10-15` (the 10-15 copy) | 2000 → 2025 | 3 (CCR, DLPH, FSR) | 5 (JPM, KDP, TDC, WMT, WU) | proven | the proposal recorded 0 / 5: the three are declared delistings whose `ends_at_delisting` no longer excuses the end under today's membership clip |
| **the candidate (pass 2)** | 2000 → 2025 | 3 (CCR, DLPH, FSR) | **216** | proven (6,539 days) | the five (iii)/(iv) holes ARE filled; the 216 are the kept DRIP's own holes — see below |
| **the candidate (pass 2)** | 2018 → 2025 | 3 (CCR, DLPH, FSR) | 1 (SLE) | proven (2,011 days) | the post-seam span is green: the 33 truncated and the 81 holed post-seam files are restored; SLE is class (i), never written, and a cache-wide reading requires a non-member to the window end (a real run withholds it at resolution) |

**What the 216 are (measured, `hole_split.py`, against the 10-15 copy's complete provider series):**
215 of the 216 have holes ONLY before their seam — 388 missing trading days in all, one to four per
name, mostly 2000–2002 (the Stooq years) — and SLE alone has post-seam holes (428). That is option
(a) by construction: the pre-seam drip STAYS, and the pre-T-167 band's holes inside it stay with it.
The 10-15 whole-file pass had read 5 holed only because it replaced the pre-seam with the provider's
complete series (the option (b) form). **So under option (a) the guard over 2000 → 2025 is NOT green
after the cutover, and the proposal's "one user ruling from green" does not hold for (a).** For the
director: declare the 388 pre-seam holes mechanically (`holed_inside`, as the first declaration set
was built), or rule a declared hole-fill of the drip span from the provider's series (a mixed-source
pre-seam span: a ruling, not a default). Nothing above was tuned. The per-name records are in
`guard_candidate_2000_2025.json` / `guard_candidate_2018_2025.json` beside the copy.

> **Correction (b), 2026-11-04 (the paragraph above kept as written):** "388 missing trading days" does
> not reproduce — `guard_candidate_2000_2025.json` (the guard's own record beside the copy) sums **380**
> undeclared missing days over the 215 non-SLE holed names; a count over each file's WHOLE span gives
> 393; `hole_split.py`'s 388 was measured against the 10-15 copy's provider series (a different
> calendar). **ONE defined computation, stated and locked** (`tests/test_pre_seam_drip_gaps_2026_11_04.py::
> test_the_real_COPY_reads_215_names_and_380_days_under_the_class_holed_1_stale_3`): the guard's own
> rule — a missing day of the MAJORITY calendar (the dates on which at least half of the names active
> that day have a bar; 6,539 days 2000-01-03 → 2025-12-31, proven against SPY both ways), inside each
> name's PIT-required spans (`data/universe/sp500_membership_pit.parquet`, clipped to the window and to
> the file's own span), counted per name, PRE-SEAM when strictly before the name's seam (the write
> record's `seam.date`, else the merge record's `seam_date`). Computed by the builder on the copy
> (`pre_seam_split.py`, read-only, 2026-11-04 20:36 UTC): **384 pre-seam missing days over 218
> drip-labelled names** (118 names with 1, 66 with 2, 25 with 3, 4 with 4, 2 with 5, one each with 6, 9
> and 18; the first hole falls in 2000–2003 for 117 names and in 2011 for 91), of which **4 days on 3
> names (AVB 1, BBBY 1, LEG 2) were already declared `holed_inside` on 10-15**, leaving **380 undeclared
> over 215 names — the guard's red count, and exactly what the `pre_seam_drip_gap` class now excuses
> and reports (§6a)**. The 27 names with POST-seam holes (557 days) are SLE 428 (undeclared; class (i)),
> CCR 64 and FISV 1 (declared) and 24 exact_tr-whole files with 1–4 declared days each; no name has both.
> The guard's reading on the copy BEFORE this unit (2026-11-04 20:33 UTC, HEAD `dd64793`) reproduced the
> table exactly: stale 3 (CCR, DLPH, FSR), holed 216, 808 undeclared days (380 + SLE's 428).

### 6a. The guard's reading AFTER the `pre_seam_drip_gap` class (2026-11-04; `3ef4034`)

The class (ruled 2026-10-23; `engines/data_manager/coverage.py`, the module docstring): the kept drip's
own pre-seam holes are excused and COUNTED, keyed to the convention label — only a hole strictly before
the seam, on a file whose bars before the seam number exactly the kept count its record carries, that
the file lacks too. Read-only, the pass driver's `guard` (exit 3 on any defect):

| substrate | window | stale | holed | `pre_seam_drip_gaps` | what remains |
|---|---|---|---|---|---|
| **the candidate (pass 2)** | 2000 → 2025 | 3 (CCR, DLPH, FSR) | **216 → 1** | **215 names / 380 days** | SLE (428 post-seam holes; class (i), a non-member required to the window end in a cache-wide read) and the three stale names of the membership identity defect (§11.5 note) |
| the candidate (pass 2) | 2018 → 2025 | 3 | 1 (SLE) | 0 / 0 (no pre-seam bars in the window) | unchanged from §6 |
| the canonical cache | 2000 → 2025 | 30 | **254 → 52** | 215 / 380 — the SAME holes, the same count | the 52 are the pre-T-167 band's POST-seam holes (the files the cutover restores); the 30 stale are the band's early ends plus the three |

So under option (a) the copy reads green over 2000 → 2025 but for SLE (a withheld class (i) name) and
CCR/DLPH/FSR (a membership defect, not a file defect) — with the 380 excused days VISIBLE in every
census (`stale_files.pre_seam_drip_gaps`, both producers, the `[CENSUS]` line). Any NEW hole — post-seam,
or pre-seam but absent from the file, or on a file whose kept count moved — still fails, by lock.

## 7. The universal label on the candidate

`label_candidate.json` beside the copy: **730 labelled, 0 unlabelled** — 648 from their write
records, 82 (the refused and unfetchable) from the merge record; 575 with a pre-seam drip span
(`drip<2018-01-02|exact_tr` 465, `drip<2020-04-09|exact_tr` 100, ten other seams), 155 `exact_tr`
whole. The same convention structure as the canonical cache (730 / 575 / 155 / 0): option (a)
changes no file's convention, only the SOURCE of the label (the record) and the post-seam bars. SPY
was written whole (`exact_tr`) and now reads from its record, not the override.

## 8. The candidate manifest

Pinned ON the copy through a staging root (`cutover_step1_manifest_root_2026_10_22/`: `data/processed`
→ the candidate; `raw`, `governor`, `macro`, `universe` → the main tree's), written BESIDE the copy —
never to `config/substrate_manifest.sha256` (re-pin #2 is cutover day's separate act):

`/Users/jacksonmurphy/Dev/_substrate_candidates/cutover_step1_candidate_manifest_2026_10_22.sha256`
— **14,902 files, manifest-md5 `4c0bb4991761feb31339f8cd9e8b73be`**; 2,820 lines under
`data/processed/` (the 2,172 files of the cache + the 648 pinned write records); `config/` untouched
(`git status` clean). This is the candidate as a fixed object, not re-pin #2.

## 9. Locks and reversions (every lock drives the real entrypoint; each reverted, run, restored by file)

| reversion | what was reverted | locks that FAILED | restored |
|---|---|---|---|
| coarse | `tr_writer.py` to its pre-unit version | both new lock files fail at collection (the new names do not exist) | `git show HEAD:` → file |
| A1 | the seam-ratio rail (`if gap > tol` → `if False`) | 1: the missed-ex-date-older-than-the-tail lock | yes |
| A2 | the kept pre-seam (the provider's bars taken instead) | 3: KEEPS, the (iii)/(iv) shape, the declared mixed write | yes |
| A3 | the split-only check's two verifications | 1: the neither-mode refusal | yes |
| A3b | the declared-but-agreeing re-rule refusal | 1: a split-only declaration on a TR cache | yes |
| A4 | the mixed-convention mismatch refusal | 2: the wrong-date and the clean-cache refusals | yes |
| A5 | the ten class (i) declarations removed from the config | 11: the ten parametrized refusals + the shipped-set pin | yes |
| A6 | the BK → BNY entry | 1 | yes |
| A7 | the declared-seam disagreement check | 1 | yes |
| B1 | the gate's unlabelled failure | 5 | yes |
| B2 | `backtest_controller.py` to its pre-unit file | 3: the backtest producer lock, the gating-key contract, the two-producer lock | yes |
| B3 | `discovery.py` to its pre-unit file | 2: the candidate producer lock, the two-producer lock | yes |
| B4 | the stale-merge-record witness | 1 | yes |
| B5 | the declared-override source | 3 (incl. the canonical data lock) | yes |
| B6 | the write-record source | 3 | yes |
| B7 | a missing merge record read as empty | 1 | yes |
| C | `close_unadj` emitted under another name | 14 (the two column locks and every write path) | yes |

The tree was clean (`git status`) after every restore.

## 10. Incident: a suite run WROTE into the canonical cache (not this unit's code; quarantined)

Between the BEFORE digest (22:05) and the first fresh copy (22:33), `data/processed/parquet/
AAPL_fundamentals.parquet` appeared in the canonical cache; it appeared again at 22:40 (different bytes:
two network fetches). B's own test files, run alone and in the same combinations with a spy on
`DataManager.fetch_historical_fundamentals`, reach no AAPL fetch; two sibling worktrees were active in
that window (one with a fresh `.hypothesis/`), and the coordinator later confirmed a sibling's suite
run through a plain `data/processed` symlink as the writer. The class is re-pin #1's "+4 EXTRA": a
NON-canonical fundamentals cache miss is fetched and written into the pinned scope
(`data_manager.py:353`). Both files were moved out by rename (never deleted) to
`_quarantine_canonical_writes_2026_10_22/`, the canonical digest returned to its BEFORE value, and
B's worktree `data/processed` was rebuilt as a REAL directory of per-file csv symlinks with an EMPTY
real `parquet/` (plus read-only symlinks for `_merge_meta.json`, the two top-level parquets,
`tr_reconciled/`, `stooq_us_daily/`), so nothing a test writes can reach the canonical cache.
`docs/State/health_check.md` carries the HIGH row.

## 11. Defects and findings, stated (not fixed here)

1. **A suite run writes into the pinned scope** (§10): the non-canonical miss branch fetches and writes; propose-first fix in the HIGH row.
2. **Seven more reused symbols** (§5): AVB, EA, EQR, LEG, QRVO, SATS, WBD need class (i) `reused_ticker` declarations (today the span rail refuses them; a declaration makes the refusal a ruling, and withholds them from a static universe as SLE/POM are). FRC → FRCB refuses DIFFERENT_CONVENTION under the rename table.
   > **Note, 2026-11-04 (the item above kept as written):** built differently from its wording, by ruling (2026-10-23, `dd64793`): the seven carry a WRITER-SIDE declaration of kind `symbol_reused_by_later_entity` in `config/level_declarations.json` — kept, never re-fetched, refused before any provider call (with a provider that raises if invoked, by lock) — NOT a class (i) `reused_ticker` universe exclusion. Their cached files ARE the PIT names' own series, so the resolver still resolves them and nothing is withheld from a static universe; SLE and POM remain the only `reused_ticker` exclusions. The proposal's "class (i)" wording for these seven is superseded by that kind.
3. **The merge record is the only seam source, and it is stale for any file regenerated after the merge** (SPY: declared). Every future whole-file regeneration outside the writer would be unlabelled until declared — which is the gate's job now (invariant 10), but the record itself should be regenerated or retired at cutover day.
4. **The 10-15 copy is the option (b) form** (whole-file exact, no records); it is a record, not a candidate.
5. **The guard's three stale names on the 10-15 copy** (CCR, DLPH, FSR) read differently from the proposal's 0: their `ends_at_delisting` declarations no longer excuse the end — the declaration or the membership clip moved; the guard's owner should re-read.
   > **Correction (c), 2026-11-04 (the item above kept as written):** NOT a declaration-regeneration gap, and not `ends_at_delisting` either — none of the three carries that facet (CCR and FSR carry `holed_inside` only; DLPH has no declaration at all). They read stale on the CANONICAL cache too (the guard over 2000 → 2025 on `data/processed`, 2026-11-04: 30 stale, the three among them, `required_end` 2025-12-31 for each) for one reason: `data/universe/sp500_membership_pit.parquet` — the PIT intervals the guard and the resolver read — carries NO interval for any of the three, so the guard treats each as outside the membership and requires it to the window end; and `data/universe/sp500_membership.parquet` (universe.py's table) carries **Countrywide Credit Industries (CCR, from 1997-06-17), Delphi Automotive (DLPH, from 2012-12-21) and Firstar (FSR, from 1998-12-11) with `included_until = NaT`** — "currently in the index" — although the names left in 2008, 2017 and 2001 and the symbols were later reused by CONSOL Coal Resources (the cached file: 2020-07-28 → 2020-12-29), Delphi Technologies (2020-07-27 → 2020-10-01) and Fisker (2020-07-27 → 2024-03-25). A pre-existing membership/identity defect; why the proposal read 0 on 10-15 is not re-derived here. Recorded as a MEDIUM row in `docs/State/health_check.md` (2026-11-04); the fix is a membership-table correction with the delisting dates from the exchange status — a DECLARED act, later; until then the guard reads them stale, correctly.
6. **51 `both` files have 0 pre-seam bars** (AMCR's shape): the merge record calls them `both`, the label calls them `exact_tr` whole — consistent, but the record's `merge_case` is misleading for them.
7. **The worktree layout:** harness worktrees carry no `data/`; the setup script's plain `data/processed` symlink is the write hazard of §10 — the script should build the per-file layout.
8. **Option (a) keeps the drip's holes** (§6): 215 names, 388 pre-seam missing days; the guard stays red over 2000 → 2025 until they are declared or a hole-fill is ruled. The proposal's green reading was the option (b) form's.
9. **53 written files have NaN `close_unadj` bars, all in the kept PRE-SEAM drip span** (`close_unadj_single_missing_2026_10_22.txt` beside the copy): 18 are the declared-seam names' bars before their provider's first bar (C, ELV, DAL, AXP, CHTR, …); 35 lack exactly ONE bar — six of them 1985-09-27 (AAPL, ADSK, AMAT, AMGN, …), a day the exchange was CLOSED (Hurricane Gloria) that the Stooq drip carries as a bar and the provider rightly does not; the rest single pre-seam days the provider lacks (AVGO 2009-08-05, AWK 2008-04-22, …). None is post-seam. The drip carrying bars on closed days is a drip-span data fact for the guard's owner; the dollar-ADV readers must treat a NaN `close_unadj` as "no print", never as zero.
10. **The cache-wide guard reading requires a non-member to the window end** (SLE over 2018 → 2025): a quirk of reading every file; a real run never puts a withheld name in the map.
11. **The second fundamentals write of the night** (`fundamentals_simfin.parquet` replaced at 23:49 by a sibling suite's SimFin panel rebuild through a raw symlink): the coordinator's finding, recorded here because it is why the canonical whole-tree digest moved (§3) while the price files did not.

## 12. The full suite, doc_lint, sync_docs — and every pytest run of the night

**Full suite: NOT RUN — HALTED** by the coordinator at 23:5x (a suite that can reach the main tree's
data is a writer until the SimFin rebuild path is fixed). `python scripts/doc_lint.py` exit 0;
`scripts/sync_docs.py` run after the engine edits (indexes committed).

**Every pytest invocation tonight**, all from this worktree, none a full-suite run, with the data
layout in force. Layout **L1** (22:03 → 23:13): `data/*` plain symlinks to the main tree's
(`processed`, `logs`, `macro`, `universe`, `research`, `observability`, `trade_logs`, `raw`, …),
`data/governor` a copy with the anchors symlinked, `data/state` a plain symlink until 22:32 then an
empty real directory. Layout **L2** (from 23:13): `data/processed` a REAL directory of 730 per-file
`*_1d.csv` symlinks, read-only symlinks for `_merge_meta.json`, `earnings_dates_pinned.parquet`,
`fundamentals_simfin.parquet`, `tr_reconciled/`, `stooq_us_daily/`, and an EMPTY real `parquet/`;
the other `data/*` symlinks as in L1.

| start (local) | layout | files / selection | result |
|---|---|---|---|
| ~22:27 | L1 | tr_writer, level_rail, yahoo_symbols, ticker_exclusion | 72 passed, 1 failed (the shipped-set pin, updated) |
| ~22:31 | L1 | contracts, census_fail_closed, gate1_t347, stale_holed_guard, data_feed_census, price_levels_item_d, ticker_exclusion, fundamentals_miss_refusal, level_rail, tr_writer, census | 203 passed, 3 failed (fixed) |
| ~22:33 | L1 | discovery_gates_7_8 + fundamentals_miss_refusal; then `-x -k gate_7_passes` | 14 / 7 failed (the synthetic name) |
| ~22:34 | L1 | discovery_gates_7_8, fundamentals_miss_refusal, census, contracts, census_fail_closed, gate1_t347; then `-x -k gate_7_passes` | 93 / 3 failed (fixed) |
| ~22:36 | L1 | tr_writer, level_rail, discovery_gates_7_8, fundamentals_miss_refusal | 68 passed |
| ~22:37, 22:38 | L1 | the two new lock files | 54/1 then 55 passed |
| ~22:40 | L1, `ARCHONDEX_REFUSE_YFINANCE_FALLBACK=1` | discovery_gates_7_8, fundamentals_miss_refusal, substrate_convention_census, contracts (`-v -s`) | forensic |
| ~22:41, ~22:42 | L1, refuse env + a spy on `fetch_historical_fundamentals` | discovery_gates_7_8; then the other three | forensic: no AAPL fetch |
| ~22:43 → ~22:46 | L1 | each of the four files alone, then the four together (60) | forensic: no write |
| ~22:50 → ~23:08 | L1 | 16 reversion-proof runs: the coarse revert; the restore (75); A1–A7 on the writer lock file (± level_rail, yahoo_symbols); B1–B7 on the census lock file (± contracts, the writer lock file) | §9 |
| ~23:17 | **L2** | tr_writer, level_rail, cutover_step1_writer, substrate_convention_census, yahoo_symbols | 113 passed |
| ~23:19 | L2 | reversion C (tr_writer + cutover_step1_writer) | 14 failed as required; restored |
| after 23:5x | — | **none** (halted) | — |

## 13. What is NOT done (by design)

- **The real-cache write** — cutover day, a separate approved act: the candidate replaces the canonical in one step; every §3 pin re-pinned together; the guard switches on at every writer; `lift_verified()` called per name (AZO, MTD, NVR; never SLE) and the ticker-exclusion test flips in the same commit.
- **Re-pin #2** (`config/substrate_manifest.sha256`) — only the CANDIDATE manifest beside the copy exists.
- **The 2024–2025 verdict re-runs, B-1 as a new pre-registered run, the (c) pricing** — after cutover.
- **The dollar-ADV / slippage / borrow readers' switch to `close_unadj`** — their own unit; the column now exists on every written file.
- **Class (i) declarations for the seven relisted symbols** (§11.2) — a config ruling for the director.
  > **Note, 2026-11-04 (the bullet above kept as written):** DONE at `dd64793`, as the writer-side kind `symbol_reused_by_later_entity` (kept, never re-fetched; the resolver still resolves them) — not as class (i) `reused_ticker` exclusions; see the §11.2 note.
