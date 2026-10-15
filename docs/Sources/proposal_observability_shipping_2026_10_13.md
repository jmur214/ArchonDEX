# Proposal: get honest-N into the cloud image, re-baked together with the substrate re-pin

**For:** the director. **Status:** proposal only. No image is built, nothing is written to S3, and
`Dockerfile.backtest`, `.dockerignore` and the manifest are untouched. **N_trials: 0.**
**Asked by:** inbox 2026-10-08 ("propose the shipping path with the manifest work").

## Rulings (director, 2026-10-13). These supersede §6's questions.

1. **Mechanics: Option A.** Bake the files and pin them, in the same re-bake as the substrate re-pin
   and the verifier-footer fix.
2. **Manifest: a separate observability manifest.** Yes.
3. **Which runs count toward N_raw: already ruled, by `[NN-MBL]`.** Honest N counts every distinct
   configuration ever run on the same substrate, **cloud runs included**. So the 08-05 local-only
   registry cannot ship. What ships is a registry rebuilt to that rule: **D's queued Option B**,
   rebuilt from the executed universe, per substrate. The user is told this ruling and can override it.
4. **Sequence:** C's cells finish, then D's Option B, then this bake. Until then cloud `--discover`
   stays **halted, failing closed**. That costs nothing, because no promotion cycle may run before
   RR-6.

## 1. The halt, verified on `main`

- **The cycle resolves N first and fails closed** (`orchestration/mode_controller.py:1176-1183`).
  `_run_discovery_cycle` calls `resolve_cycle_n_trials` before the hunt and before any write to
  `edges.yml`. It reads the container's own `data/observability/run_registry.sqlite` and the newest
  `n_effective_*.json`, and raises `HonestNUnavailableError` if either is absent.
- **The image carries neither file.** `.dockerignore:50` excludes `data/observability/` under the
  comment "Runtime output (regenerable; do NOT bake into image)". `Dockerfile.backtest` bakes
  `data/processed`, `data/raw`, two `data/universe` files, `data/macro` and `data/governor`, but not
  observability.
- **Nothing pulls it at runtime either.** `cloud_entrypoint.sh` pushes results to S3 at exit and pulls
  nothing at start.

So every cloud `--discover` halts at the first cycle, before it hunts or writes anything. **That is the
intended fail-closed behaviour, and nothing is broken today.** No cloud Discovery cycle is expected
before RR-6.

**A correction to RR-3 §12.** It names two remedies: pass `n_trials_for_dsr` explicitly, or ship the
files. The explicit parameter exists only for direct `validate_candidate(...)` callers
(`engines/engine_d_discovery/discovery.py:990`). The production cycle has no override; it resolves N
itself, first. **For `--discover`, shipping is the only remedy short of a referee code change.**

## 2. Shipping the files as they are would lift the halt with the wrong N

| file | state on the host | read by the gate? |
|---|---|---|
| `run_registry.sqlite` | 81,920 bytes; last written **2026-08-05** | yes: N_raw |
| `n_effective_2026-09-30.json` | the only artifact | yes: ρ̄ and the ONC gate inputs |
| `run_registry.db` | **0 bytes**, 2026-05-08 | no (the default path is `.sqlite`); exclude it |

**The registry is a stale snapshot, and it is blind to the cloud.** It is rebuilt only by hand
(`python -m core.observability.run_registry --rebuild`) and only from local `data/trade_logs/`, while
cloud runs land in S3. `scripts/rr3_empirical_rho.py` states the consequence: the registry's 231 rows
and the ~1,300 runs whose equity curves survive are **disjoint sets**. ρ̄ is measured on the second
set; N_raw is counted on the first.

So baking today's files would lift the halt with an N that is two months stale and has never counted
a cloud run. That N is too small, so the gate would be too loose: the silent-wrongness shape the halt
exists to prevent. **The halt should be lifted by a dated, reviewed N, not by a file merely existing.**

## 3. Options

**A. Bake and pin (recommended).**
- Un-exclude the two files by name (not the whole directory) and `COPY` them.
- Pin them in a manifest, so the N a container uses is a reviewed diff at build time.
- Pros: **hermetic.** The same image gives the same N, so runs are reproducible. Every other
  load-bearing input (processed, macro, governor) is already handled this way.
- Cons: N is frozen at build time. Trials run after the bake count only from the next re-bake.
  Cycles are rare and deliberate, so I think this is acceptable, provided the cycle's record states
  which N it used (step 5 below).

**B. Pull from S3 at container start.**
- Pros: the N is current.
- Cons:
  - it adds a network dependency to the measurement path; it would stay fail-closed through
    `HonestNUnavailableError`;
  - the same image yields a different N on different days;
  - it needs a publisher job, and nobody owns one today.

**C. Supply an explicit N at submit time.**
- **Not recommended.** It needs a referee code change: an override in `_run_discovery_cycle`, the very
  knob RR-3 removed. An operator-typed N is `max(1, len(batch))` in a new form.

## 4. Prerequisite under any option: which runs count toward N_raw (RULED; see Rulings, item 3)

This is RR-3 §3.1's open question, and it belongs to the user. One option is to rebuild the registry
over a local mirror of the S3 results, so cloud runs count. The other is a ruling that the local-only
population is the honest one. **Until it is settled, any shipped N is the disjoint snapshot**, under
any of the three options.

## 5. The manifest work: the same re-bake

**The backtest image cannot be rebuilt today.** `verify` requires an exact match, and the host has
drifted. Agent R re-derived the numbers on 10-08: 0 MISSING, **130 EXTRA** (40 of them
`tr_reconciled`, plus VVIX, SKEW and Shiller), and **5 CHANGED** (VIX, VIX9D, VIX3M, VIX6M,
`_meta.json`). This is B-7's blocker. RR-3's halt lifts on the same re-bake, so the two belong in one
unit.

Proposed sequence (each step after the user's ruling and after C's cells free the 8 GB host):

1. **Settle the population.** Get the §4 ruling, rebuild the registry, then regenerate the artifact
   with `python -m scripts.rr3_empirical_rho`.
2. **Re-pin the substrate manifest** with `scripts/gen_substrate_manifest.py generate`. Review the diff
   as a statement of what is canonical, not as a rubber stamp: it also pins the 5 changed VIX files and
   the shallow flat ETF files the 08-26 repoint routes around (RR-7 D3's cautions). DFII10 is
   **absent**, not unpinned: fetch it, or record it as absent (`macro_real_rate_v1` is paused, and the
   HMM does not use the column).

   **This is re-pin #1** (director, 2026-10-15). It pins the CURRENT substrate (the drip world) and
   makes `verify` green. Re-pin #2 pins the exact-TR substrate on cutover day (cutover proposal
   §3.2). Measured 2026-10-15: MISSING 0, EXTRA 134, CHANGED 5.
   - The 5 CHANGED VIX-term files are a pure extension: every June row is bit-identical.
   - The EXTRA files are the T-256 additions (including `tr_reconciled/`, which the paper image
     bakes) and 4 fundamentals parquets.

   **Decision (Agent B, by the director's delegation): PIN the fundamentals cache; do NOT exclude
   `*_fundamentals.parquet`.**
   - *Why pin.* 585 of the 589 files are already pinned since June. They are measurement inputs:
     value edges read them, and the census gates `fundamentals_blind`. A JUNK exclusion would UNPIN
     585 inputs that are pinned today, so a changed fundamentals file could move a result without
     the manifest noticing. That is a regression in the referee.
   - *The four new files* (CVNA, KG, SII, S; written 2026-10-14, 02:45–03:06) are what B-1 actually
     read. Pinning them records that input.
   - *The consequence, stated:* the cache has exactly ONE runtime write path, a cache MISS.
     `fetch_historical_fundamentals` (`engines/data_manager/data_manager.py:188`; the cache check at :201) fetches from
     the network when no file exists, and writes a new file into the pinned scope. That happened 4
     times on 2026-10-14, inside a measurement run (B-1).
     - Every such miss turns `verify` red. Under D's stamp design, it turns the stamp STALE, and
       **every campaign submit then refuses until the next re-pin.** That is the right fail-closed
       answer: an unpinned input entered the substrate.
     - It also means one local run can block cloud submits.
   - *Proposed, not built:* in canonical runs a fundamentals cache miss should NOT fetch. It should
     be recorded (per ticker, under the census's `fundamentals_blind`) and left absent, so the
     substrate changes only through a deliberate refresh. This is the same class as the
     yfinance-fallback refusal (`ARCHONDEX_REFUSE_YFINANCE_FALLBACK`).
   - *Found on the way: a lying docstring.* `prefetch_fundamentals` (`data_manager.py:169-185`,
     called on every backtest at `orchestration/mode_controller.py:868`) says it "re-fetches if cache
     is older than max_age_days (default 7)". It never does: `fetch_historical_fundamentals` returns
     the cached file whenever one exists. The files' modification times confirm it: 521 from May,
     64 from June, none rewritten since 2026-06-11 except the four new ones. The re-fetch is dead
     code; the docstring should say what the code does. This is a LOW health row, separate from
     the decision.

   **Also pinned at re-pin #1** (director's rulings, 2026-10-15; cutover proposal §3.2):
   - **`data/external/base_curve/` joins `SUBSTRATE_DIRS`.** The frozen 26-yr arm0 curve that
     T-171, T-178 and T-174 read is a controller product with zero manifest lines today. It is
     pinned here and NOT regenerated at re-pin #2: the old file stays pinned as the input of record.
   - **A SHARES SNAPSHOT for the T-219 `delist_shares` cohort.** `build_pit_cap_history_t219.py`
     fetches shares LIVE (`get_shares_full`, :56) and swallows a failed fetch to None (:57-58). The
     snapshot is fetched once here and pinned, so re-pin #2 recomputes the cohort deterministically
     from the cutover cache. **The recompute path never calls `get_shares_full`**: that is the
     condition under which the live-fetch fail-open is dead and needs no health row of its own. If
     the recompute ever fetches, the fail-open is live again and the row is owed.
3. **Ship the observability files under Option A.** Pin them in a **separate** observability manifest,
   not in the substrate manifest. The substrate changes rarely and deliberately; the registry changes
   with every run. Mixing the two would make every re-bake a substrate diff and train reviewers to
   wave it through.
4. **Fix the verifier footer in the same unit** (one line, referee-adjacent). It prints `total − 60`,
   so on today's drift it says "75 more" while 110 lines are hidden (RR-7 D3; R confirmed).
5. **Check the first artifact, not the build.** Run the new image with `--discover` on a short window
   and confirm the cycle records its N with provenance: source, registry row count, newest snapshot,
   and artifact date. Today the N is printed to stdout (`mode_controller.py:1319`). Whether it reaches
   a durable record is part of this check; if it does not, adding it is a one-line proposal.

## 6. Decisions requested

1. **A or B?** I recommend A. C is not recommended.
2. **Pin observability in a separate manifest?** I recommend yes.
3. **Route the §4 population question to the user.** It decides whether any shipped N is honest.
4. **Timing:** after C's cells. Nothing here is needed before RR-6.
