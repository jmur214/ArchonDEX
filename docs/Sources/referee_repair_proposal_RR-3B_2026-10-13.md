---
task_id: RR-3 Option B (queued by the RR-3 merge, e1f51df; R's F3)
title: Referee repair proposal — one population for honest N: rebuild the registry from the run evidence, per substrate
date: 2026-10-13
author: Agent D
branch: proposal/rr3-option-b-registry (NOT pushed, NOT merged)
type: REFEREE REPAIR PROPOSAL — DESIGN DRAFT. Propose-only; R reviews, then the director decides.
status: DESIGN + NUMBERS IN (data pass run 2026-10-13 under §8's pre-registered spec). For R's review.
n_trials: 0
---

# RR-3 Option B — one population for honest N

## 0. The problem, in one line

**Discovery's Gate 0 and Gate 8 take their two inputs from two sets that share no run.** N_raw comes from the run
registry (231 rows); the correlation adjustment (ρ̄, ONC compression) comes from the 1,322 executed runs whose
equity curves survive. Not one run is in both. They agree within ~10% today (N_eff 36.9 vs 40.3) — **luck, not
design** (RR-3 proposal §5.2; R's F3). The merge chose Option A (keep the registry) and queued this.

**Sequencing — director ruling, 2026-10-13: Option B is on the CLOUD'S CRITICAL PATH, not a refinement.** Cloud
`--discover` stays halted (RR-3's fail-closed N; F5) **until Option B's rebuilt registry exists**, because `[NN-MBL]`
counts every configuration run on the substrate — **cloud runs included** — and today's registry can never contain
one (§1.1). Shipping Option A's registry into the image would end the halt by feeding the cloud a count that
structurally omits its own runs.

### The numbers (data pass, 2026-10-13 — spec pre-registered in §8 at `17ec6db`, before the pull)

**Cost, as the director required it recorded:** **682,393,600 bytes** pulled from S3 in 127 s (2,053 snapshot files,
895 summaries) into `data/observability/rr3b_s3_mirror_2026-10-13/`; free disk 12 → 11 GB (floor 8, never
approached). The pass ran `nice -n 19` with OMP/OPENBLAS/MKL = 1 and `OMP_DYNAMIC=FALSE`: **124 s wall, peak RSS
172.5 MB** (`/usr/bin/time -l`). Outputs: `data/observability/rr3b_population_2026-10-13.json` and
`rr3b_rho_2026-10-13.json` — neither named `n_effective_*`; the live gate still reads `n_effective_2026-09-30.json`
(verified after the run, N_eff 36.92).

| | |
|---|---|
| executed universe | **1,343** runs → **920** valid → **258** distinct trials (229 from S3, 30 local, 1 in both) across 42 campaigns; 09-30 was 1,322 / 912 / 252 — the growth is C's RR-1 cells |
| the registry's 125 run rows | evidence found anywhere now: **0** (re-confirmed; R confirmed the same independently) |
| ledger ↔ run overlap (rule pre-stated) | **none** — see §9.1 for why, which is not what the rule assumed |
| ρ̄ | **0.6056** [0.574, 0.637] vs 0.6053 [0.571, 0.640] on 09-30 — unchanged to three decimals; **H1 still SUPPORTED** at every setting |
| Option B N_raw | **489** if every ledger row is kept · **383** with no ledger-only rows (the §2D table decides between them) |

**N_eff — and the one choice that moves it most (§9.2):**

| treatment | N_eff | MinBTL @ SR=1 | SR_req 12y | SR_req 26y |
|---|---|---|---|---|
| Option A (merged), tonight's gate inputs | 33.2 | 4.47 y | 0.611 | 0.415 |
| Option B, correlation credit applied to all 489 | 69.1 | 5.75 y | 0.692 | 0.470 |
| **Option B, credit only where correlation is MEASURED** (258 curve-bearing → 36.5, + 231 curve-less at raw) | **267.5** | **8.18 y** | **0.825** | **0.561** |
| same, without ledger-only rows | 161.5 | 7.26 y | 0.778 | 0.528 |

**Option B TIGHTENS the gate on every treatment** — §4's direction is now known. Admitting the 229 cloud trials does
it. The live Option A on main understates N by at least half, and by about 8× under the measured-credit treatment.

## 1. Why the sets are disjoint — the mechanism, verified 2026-10-13

This is not drift that a rebuild would cure. It is how the registry is built.

1. **`rebuild()` walks only the local `data/trade_logs/`.** Cloud cells write to the S3 results bucket and never land
   there, so **1,201 cloud runs could never be registered**, however often `rebuild()` ran.
2. **`rebuild()` upserts and never deletes.** The registry is the union, over time, of whatever sat on this laptop at
   each manual rebuild — last on 2026-08-05. The 125 run rows' directories now exist nowhere (not on disk, not in
   120,036 S3 keys), so those rows can be neither re-verified nor reconstructed.
3. **`rebuild()` skips any directory without `performance_summary.json`.** On 09-30, 72 of 121 local run dirs had none.
4. **The 106 ledger rows are trial counts, not runs** (`backfill_run_registry_t336.py`: one row per `N+=k` in
   `TASK_LEDGER.md`, 26 tasks). They have no equity curve, so ρ̄ can never be measured over them — and they **mix
   substrates**: T-196's 35 foundry candidates ran on Discovery's substrate; T-282/312/318 ran on the T-306
   multidecade substrate. `[NN-MBL]` counts trials *on the same data substrate*.
5. **Runs do not record their substrate.** A current run's census carries `n_resolved`, `regime_total_bars` and
   config md5s — enough to *infer* a substrate, not to *state* one. No universe id, data source or window.
6. **The registry has no durability mechanism** (T-356b, `a0176ad`): gitignored, untracked, no S3 sync, one copy.

## 2. The design

### A. The source of truth is the durable run evidence, not a laptop directory
The registry is rebuilt from **every place run evidence survives**: the S3 results bucket and local
`data/trade_logs/`. A run is admitted on its own artifact (a snapshot or a summary), keyed by `run_id`, with
`source = s3:<prefix> | local | ledger:<task>`.

**Rows are never deleted.** A run whose artifact later disappears keeps its row, marked `evidence = absent`. This is
how the 125 current run rows are carried forward: imported from the archived registry as `evidence = absent`, so
**N can never shrink because a directory was cleaned up.** That is the failure T-356b names: today, losing the
registry and calling `rebuild()` would yield a smaller N and loosen the gate with no alarm.

### B. A trial is a distinct configuration, not a row
Each run gets a `trial_key` (the daily-equity hash RR-3 already uses, cross-checked against census
`trades_canon_md5` where both exist — 0 conflicts on 09-30). **N_raw = distinct `trial_key`s**, so determinism reps
stop counting as trials. On 09-30, 660 of 912 valid runs (72%) were reps.

**This LOOSENS N**, and it is stated as such. It is justified by `[NN-MBL]`'s own definition ("every distinct
backtest configuration") and by the fact that ρ̄ is *already* computed after this dedupe — Option A is the
inconsistent one.

### C. Every trial carries a substrate, with its provenance
- **Going forward:** a run records a **substrate fingerprint** in its census — universe id and `n_resolved`, the
  window's first and last bar, a data-panel hash, and the config md5s the census already holds. This is a
  `[NN-CENSUS]` key, so it is part of this proposal, not something a worker adds.
- **Legacy runs:** inferred from the window (snapshot dates), `n_resolved` where a summary exists, and the S3 campaign
  prefix (e.g. `t055g-…`, `foundry-t196`, `reanchor-t180`) mapped to its task and that task's audit doc. Every
  inferred tag records **how** it was inferred: `substrate_source = recorded | inferred:<rule> | unresolved`.
- **An unresolved trial counts in EVERY family it could belong to.** It is never dropped. Dropping is the
  non-conservative direction.

### D. Ledger rows are tagged per substrate; removing any from Discovery's N needs a ruling
Each of the 26 ledger tasks gets a substrate tag, cited to its audit doc, in a table the reviewer can check line by
line. Excluding the T-306-substrate rows from Discovery's N is correct under `[NN-MBL]` — **and it loosens the gate.**
So the default is conservative: **every ledger row stays in Discovery's N until the table is ruled on.** The table is
a deliverable; the exclusion is a decision for the director.

### E. ⭐ The structural lock: the gate refuses to mix populations
The ρ̄ artifact gains per-substrate blocks, each computed over exactly the `trial_key`s the registry holds for that
substrate, and each records a **hash of its `trial_key` set**. `compute_n_effective_correlated()` compares that hash
with the registry's set for the same substrate, and **raises `HonestNUnavailableError` on a mismatch**.

That turns R's F3 from a reviewer's note into something the code enforces: **N_raw and ρ̄ can only ever be
computed over the same trials.** Ledger rows, which have no curves, are counted in N_raw and are listed separately
in the artifact, so their exclusion from the ρ̄ population is visible rather than implicit.

### F. Durability and cloud availability are one problem
The registry and the artifact are pushed to S3 on every rebuild. That closes T-356b's two KNOWN_GAPs **and** RR-3's
F5 (cloud `--discover` halts until `data/observability/` reaches the container) with one write path. The shipping
itself is B's, with the RR-7 manifest work; this proposal specifies what is shipped and when.

### G. Migration — nothing is lost, and the gate does not switch on its own
1. The current `run_registry.sqlite` is archived (`[NN-ARCHIVE]`), locally and in S3, before anything is built.
2. The new registry is built **beside** the old one. The old one stays the gate's source.
3. A side-by-side report gives N_raw, distinct trials and N_eff per substrate, old against new, with every
   difference attributed to one of §2A–D.
4. The gate switches only after R reviews that report and the director decides.

## 3. Pre-registered: when the per-substrate split is abandoned

Stated before any data is pulled:

- **If more than 25% of distinct trials end up `unresolved`**, the substrate inference is not credible. The
  per-substrate split is then **not adopted**, and Option B delivers only §2A, B, E and F over a single population
  (the executed universe plus the ledger rows).
- **If two inference rules disagree on more than 10% of the trials both can tag**, same outcome.

## 4. Which way N moves — unknown until measured, and the direction matters

| component | effect on Discovery's N |
|---|---|
| A. admit the 1,201 S3 cloud runs | **raises** |
| A. keep the 125 absent-evidence rows | holds (prevents a silent fall) |
| B. dedupe determinism reps | **lowers** |
| C/D. split by substrate | **lowers**, if the T-306-substrate ledger rows leave (ruling required) |
| E. same-population lock | none on the number; refuses a mismatch |

The net is not knowable until §8 runs. Whatever it is, the gate takes it, with RR-3's conservative bounds and the
N_eff floor of 2 unchanged. **If the net LOOSENS the gate, that is acceptable only because every component is a
definitional correction, and the side-by-side report must say which component did it.**

## 5. Verdicts this does not change

Same seven as RR-3, for the same reason — **T-251, T-259, T-279, T-282, T-284, T-312, T-318** are paired-difference
CIs, not DSR-gated, and their scripts touch nothing Option B changes. Option B changes only what feeds
`compute_n_effective_correlated()`.

## 6. What is NOT in this proposal
- **No change to the gate's maths.** E[max], the conservative bounds and the floor are RR-3's, unchanged.
- **No shipping code.** That is B's, with RR-7 (§2F).
- **No exclusion of any ledger row.** It is proposed as a table for a ruling (§2D).
- **No numbers.** §8.

## 7. Deliverables, when built
1. `core/observability/run_registry.py`: multi-source ingest (S3 + local + archived rows), `trial_key`,
   `evidence`, `substrate`, `substrate_source`; never-delete semantics; an absolute default path (the current
   cwd-relative default is the split-in-two class).
2. A census key for the substrate fingerprint, with a `tests/test_contracts.py` guard.
3. `scripts/rr3_empirical_rho.py`: per-substrate blocks, each carrying its `trial_key`-set hash.
4. `core/measurement/mbl_gate.py`: the §2E same-population check, failing closed.
5. The legacy inference rules and the 26-task ledger table, each row cited to its audit doc.
6. The side-by-side report (§2G.3).
7. Tests driving the real entrypoints and proven by reversion — in particular, a mismatched population must
   **raise**, and an artifact disappearing must **not** lower N.

## 8. The data pass — specification, PRE-REGISTERED 2026-10-13 before the pull

Authorised by the director the same evening (one minute of wall time under 1 GB does not compete with C's
single-threaded cell). Written and committed **before** a byte is pulled.

**Conditions.** `nice -n 19`; the single-thread pins C's cells use (`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
`MKL_NUM_THREADS` = 1; `OMP_DYNAMIC=FALSE`); free disk checked before the pull, **abort below 8 GB** (12 GB at
spec time). Peak RSS, bytes pulled and wall time are recorded in §0 beside the numbers.

**Where it goes.**
- Mirror: `data/observability/rr3b_s3_mirror_2026-10-13/` — gitignored, durable, deliberately **not** `/tmp`
  (macOS purges it after three days; that is how the 09-30 mirror and C's logs vanished), and **not** under
  `data/trade_logs/` (the run scan would count the mirror as local runs).
- Output: `data/observability/rr3b_population_2026-10-13.json`. **Deliberately NOT named `n_effective_*.json`.**
  `mbl_gate.latest_n_effective_artifact()` selects the NEWEST file matching that pattern, so writing one would
  silently make tonight's measurement the live gate input on `main` — an unreviewed referee change. That is also a
  finding (§9).

**What it measures.**
1. The executed universe today: discovered / valid / distinct `trial_key`s, split by S3 vs local and by S3 campaign.
2. The current registry's 125 run rows: how many have evidence anywhere now (expected 0).
3. **Ledger ↔ run overlap.** For each of the 26 ledger tasks, `k_ledger` (rows) against the distinct `trial_key`s in
   S3 campaigns carrying that task's token (e.g. `foundry-t196` ↔ T-196's 35 rows). **Pre-stated rule:** where a
   task appears in both, Option B counts **max(k_ledger, k_runs)** — never the sum (double counting) and never the
   min (loosening by switching provenance).
4. **Option B's N_raw**, assembled as: distinct executed `trial_key`s + the 125 absent-evidence rows + ledger rows
   not covered by item 3 — reported **with and without** the T-306-substrate ledger rows (the §2D ruling question).
5. ρ̄ and N_eff over the executed population, by `scripts/rr3_empirical_rho.run()`, with RR-3's conservative gate
   inputs, written to the output above — compared with the 09-30 artifact.

**Pre-data amendment to §2C/§3 (stated before the pull, and why).** Every run carrying a
`portfolio_snapshots.csv` is a **harness** run — `run_isolated`/`BacktestController` writes that file; the research
scripts behind the T-306-substrate verdicts do not. So executed runs form **one substrate family by construction**,
not by inference, and this proposal does **not** propose a finer per-window split among them. §3's inference criteria
therefore have nothing to bind on for executed runs; they remain in force for any future finer split. The substrate
question reduces to the **26 ledger tasks**, which get the audit-cited table (§2D). This rests on where the files
come from, not on any outcome — no N, ρ̄ or count from tonight's pull has been seen.

## 9. POST-DATA findings — labelled as such; none of them is a pre-registered result

### 9.1 Discovery's own candidate trials leave no equity curve — so no curve-based registry can count them
The pre-stated overlap rule found **zero** overlaps, including T-196, though S3 has a `foundry-t196/` prefix. The
reason: `validate_candidate` backtests through `run_backtest_pure`, which uses *"an in-memory cockpit logger, no CSV
files written."* A Discovery candidate's evaluation leaves a result record, never a `portfolio_snapshots.csv`.
`foundry-t196/` holds exactly **35 `t195_foundry_eval.jsonl` files — one per candidate, matching the ledger's 35.**

So **the trials Gate 0/8 exist to count are invisible to the current registry and to §2A's evidence scan alike.**
They survive only as ledger rows, as result records like these, and in `data/research/discovery_log.jsonl` (local,
dormant since June, T-356 gap #4). Two consequences for the design:
- **§2A needs a fourth evidence class:** *candidate-evaluation records*. They count in N_raw, have no curve, and are
  listed separately from the ρ̄ population, as ledger rows are. T-196's 35 rows are therefore **corroborated by 35
  S3 records**, not a bare ledger claim — the §2D table must keep them in Discovery's N.
- **Going forward, `validate_candidate` should persist each candidate's attribution stream.** It already holds it in
  memory (Gate 1 computes it). That one write is what lets candidate trials enter the measured-correlation population
  instead of sitting outside it permanently. It is a Discovery change, small, and belongs with the Option B build.

### 9.2 Correlation credit must not be borrowed by trials outside the population it was measured on
§0's table shows the choice that moves N_eff most. The merged RR-3 method — and the first table this pass printed —
applies the measured compression to **all** of N_raw. But ρ̄ and the ONC compression are measured on the 258
curve-bearing trials only. The other 231 (125 absent-evidence rows, 106 ledger rows) are outside that population.
Crediting them with its correlation is **R's F3 again, in miniature**: an adjustment borrowed from a set that
excludes them.

- **The conservative treatment gives curve-less trials no credit:** N_eff = N_eff(curve-bearing) + N_raw(curve-less)
  = 36.5 + 231 = **267.5**. That is conservative because combining groups additively is what independent groups would
  give, and any correlation between or within them can only lower the true N_eff.
- **The cost is real.** MinBTL at SR=1 goes from 4.47 years (Option A) to 8.18. The 26-year window then needs SR ≥
  0.56 instead of 0.42.
- **It is not mine to choose.** It is the largest single lever in honest N, and it is a ruling. The evidence that
  would narrow it — the curve-less trials' own correlation — is **unmeasurable from what we keep** for legacy trials.
  For future ones, §9.1's attribution-stream persistence removes the question.

This point was found after the data, but it runs in the **tightening** direction. It cannot be fitting toward a pass.

### 9.3 The live gate takes whichever `n_effective_*.json` is newest — on main, today
`mbl_gate.latest_n_effective_artifact()` sorts by filename and takes the last. **Any re-run of
`scripts/rr3_empirical_rho.py`, by anyone, silently replaces the live gate's input on main**, with no review. This
pass avoided it only by deliberately not using that name (§8). Under Option B, §2E's hash lock catches a population
change; under Option A, which is live, nothing does. **Recommend pinning now, independent of Option B** — for example
a committed pointer naming the artifact and its sha256, which the gate verifies, failing closed on a mismatch. Small,
referee-side, R's to review.

### 9.4 The ONC compression is a noisy estimator
Its conservative bound (ci_high) moved **0.160 → 0.141** between 09-30 and tonight, on 2.4% more trials. The
equicorrelated estimate moved far less, and the conservative `max()` of the two is what absorbs that noise — today the
two land within 3% of each other (36.5 vs ~35.5 for the 258). Worth knowing before anyone quotes an ONC number alone.

### 9.5 §3's pre-registered criteria: applied, not binding
Per the pre-data amendment in §8, executed runs form one substrate family by construction, so the >25% unresolved and
>10% disagreement criteria had nothing to bind on. The substrate question now sits entirely in the 26-task ledger
table (§2D) and in §9.1's candidate records.

---
**PROPOSAL — propose-only, not pushed, not merged.** N_trials 0. Rulings needed: §2D (the ledger table), §9.2 (credit
for curve-less trials), §9.3 (pin the live artifact). The build follows RR-6 unless R's read of these numbers changes
that.
