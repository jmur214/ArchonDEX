# Referee repair proposal — RR-7: record and reproducibility hygiene

**Brief:** `docs/Sources/alpha_frontier_program_2026_09_30.md` §3.1 RR-7, fired unchanged,
plus one director-added proposal line (`[NN-AI-GATE]`).
**Branch:** `chore/referee-rr7-record-hygiene` (based on `origin/research/alpha-frontier-2026-09-30`
@ `99153df`, the same base as the RR-1/2/3 siblings — `origin/main` does not yet carry the brief
or the xfail file). **N_trials: 0.** Nothing here is merged; review → director → user.

**Anchor rule (09-18 design note):** every record change below cites `file:line` **and the exact
string currently there**, so a reviewer can confirm staleness mechanically and a later edit that
moves the text cannot silently orphan the claim.

**Five findings go beyond the brief**, and each is marked **[BEYOND BRIEF]**. Two of them narrow
what the brief asserted; none is acted on without review.

---

## Deliverable 1 — edge-weight key (DONE on the branch, commit 1/6)

`config/alpha_settings.prod.json:37` `"news_sentiment_edge": 0.5` → `"news_sentiment_v2": 0.5`,
the EDGE_ID at `engines/engine_a_alpha/edges/news_sentiment_edge.py:32`. Targeted xfail
`test_prod_edge_weight_keys_match_edge_ids` now passes; the other 15 xfails untouched.

**⚠ Rail conflict, for an explicit ruling.** The common hard constraints forbid touching
`config/*.prod.json`; the brief scopes this key as its one exception. Verified before editing
that the change is **behavior-neutral in production**: `news_sentiment` appears in
`data/governor/edges.yml` **zero** times, and `orchestration/mode_controller.py` loads edges only
via `registry.get_all_specs()`. The edge never loads, so no weight is consulted under either key.

**The xfail's own comment was inaccurate** and is corrected on the branch (intent kept, false
sentence not reproduced): it said the 0.5 "is never applied (defaults to 1.0)". Nothing is
misapplied today; the risk is **forward** — register the edge and `edge_weights.get(edge_name, 1.0)`
(`engines/engine_a_alpha/signal_processor.py:657`) silently misses the key.

**[BEYOND BRIEF] The generic test's definition had to be widened.** Auditing all 25 keys first
surfaced `growth_sales_v1` and `value_deep_v1` as apparent mismatches. Both are **parametrised
instances** of the generic `fundamental_ratio` module — their identity lives only in the
registry. A check against class `EDGE_ID`s alone falsely flags them; a check against the registry
alone falsely flags `news_sentiment_v2` (declared, unregistered). **Only the union is correct.**
After the fix: zero invalid keys — the brief's one named mismatch was the only real one.
Test: `tests/test_edge_weight_keys_rr7.py` (skips with a reason when `edges.yml` is absent).

---

## Deliverable 2 — proposal text for the record (NO edits made)

### 2a. `docs/State/health_check.md:137-140` — legacy HMM row
- **Anchor:** line 140, `- Status: not started (repoint is propose-first; sequenced behind T-118 verdict)`
- **Stale since** 2026-08-26 (`20f6fc6`). Verified today: `config/regime_settings.json` and the
  `HMMConfig` dataclass default both name `hmm_3state_crisis_v1.pkl`.
- **Proposed:** `- Status: RESOLVED 2026-08-26 (20f6fc6) — production config and dataclass default
  both name hmm_3state_crisis_v1.pkl. Row kept for provenance.` Move to the Resolved section.

### 2b. `docs/State/health_check.md:41` — HMM blind pre-2020
- **Anchor:** `### [HIGH] The HMM is structurally BLIND before 2020-05-08, and says nothing (2026-08-26)`
- **Stale since** `068afba` (2026-08-26). Verified today: panel **5,041/8,361** complete rows back to
  **2006-04-04**; `tlt_ret_20d` NaN **36.6%** (was 82.1%).
- **Proposed:** retitle `[RESOLVED 2026-08-26] ...` with the two commit hashes; keep the
  uniform-posterior note, since the classifier still returns a uniform posterior on a NaN row
  (the panel no longer produces one on the common window).

### 2c. `docs/State/CURRENT_STATE.md:23` — **[BEYOND BRIEF] a double error on one line**
- **Anchor:** `- **Engine E \`hmm_p_crisis\` is predictive (AUC 0.887)** — but production loads the legacy HMM and the panel is blind pre-2020`
- **Error 1:** "production loads the legacy HMM … blind pre-2020" — both fixed 2026-08-26.
- **Error 2:** "`hmm_p_crisis` … AUC 0.887" — 0.887 is the **old** model's `p_crisis` (T-087). On the
  crisis model now in production, `p_crisis` alone is a **coin flip, OOS 0.497** (T-103); the
  validated signal is the **combined** posterior `p_crisis + p_stressed`, OOS **0.914** (ci_low 0.880).
- **Proposed:** `- **Engine E: the crisis-trained HMM is in production (since 2026-08-26); its
  COMBINED posterior (p_crisis + p_stressed) is predictive, OOS AUC@5d 0.914 (ci_low 0.880) —
  p_crisis ALONE is not (0.497).** Panel deep-backfilled to 2006-04-04.`

### 2d. `docs/State/CURRENT_STATE.md:39` — pending-work line
- **Anchor:** `- Referee repairs (B, after the director pass's first artifact): HMM backfill repoint; legacy-HMM production load.`
- **Proposed:** delete as a pending item; both were already done (see my 2026-09-18 design note).

### 2e. `CLAUDE.md` `[NN-MBL]` lines 135-136 — **[BEYOND BRIEF] a sibling-number tell**
- **Anchor:** `to N_trials). At our current ~75 accumulated N_trials, the` / `5-year substrate-honest window requires SR ≥ 1.55 to clear DSR`
- **"~75" is stale:** `core.measurement.mbl_gate.compute_n_effective()` returns **231** today.
- **The two numbers disagree with the formula printed beside them.** The paragraph states
  `T ≥ 2·ln(N)/SR²`. At N=75, T=5 that gives **SR ≥ 1.31**, not 1.55; SR 1.55 corresponds to
  N≈405. At the live N=231: **SR ≥ 1.48**.
- **Replacement text: owned by RR-3, cross-referenced here rather than duplicated.** RR-3 reaches
  the same contradiction independently (`docs/Sources/referee_repair_proposal_RR-3_2026-09-30.md:159-160`,
  branch `fix/referee-rr3-honest-n`: *"Its own formula gives 1.31 at N=75; 1.55 corresponds to N≈406"*)
  and proposes the `[NN-MBL]` wording at its §5.3 — the honest-N brief is the right owner, since its
  exact-E[max] proposal changes the number again. RR-7's only addition: whatever the sentence
  becomes, it should **point at `compute_n_effective()` rather than transcribe a value**, because a
  hardcoded N is exactly how "~75" went stale.
- **Three independent passes reached this** — both RR-7 executions and RR-3 — without seeing each
  other.

### 2f. `CLAUDE.md` `[NN-SHARPE-CI]` lines 123-124
- **Anchor:** `Block-bootstrap (Künsch 1989, default 1000 iter, auto block` / `length per Politis-White) is the project standard.`
- **False:** `core/metrics_engine.py:923` is `block_length = max(5, int(round(n ** (1.0 / 3.0))))` — a
  **fixed n^(1/3) rule with floor 5**, moving-block. Politis-White is a data-adaptive selector
  driven by estimated autocorrelation; nothing in the codebase implements it.
- **Proposed:** `Block-bootstrap (Künsch 1989 moving-block, default 1000 iter, block length
  max(5, round(n^(1/3)))) is the project standard.` (Keeping the rule's force; correcting the method.)

### 2g. `docs/State/TASK_LEDGER.md:143` — T-196
- **Anchor:** `33 died at gate_1, 2 at gate_3.`
- **Proposed:** `33 died at gate_1; 2 cleared Gates 1–2 and were killed by a FORCED Gate 4 fail
  (mislabeled gate_3 at the time — see RR-2 / gap report §2 N-2).`
- **Evidence:** `docs/Sources/alpha_frontier_review_2026_09_30/01_gap_report.md:45-46`. **I could not
  independently verify this** — no per-candidate gate record for T-196 persists under
  `data/research/`. And **the cited source contains a counting tension the reviewer should
  reconcile**: its line 42 says *"Every recorded candidate — 93/93 … T-196 — died at Gate 1"*, while
  line 45 says *"Two T-196 features … cleared Gates 1–2"*. Both cannot hold.

### 2h. `CLAUDE.md` `[NN-AI-GATE]` — the director's added line
- **Anchor:** line 248, `the honest bar: the price-vocabulary is H0-exhausted (foundry,` (continuing
  `conjunctive), so value — if any — is in NEW DATA modalities`)
- **Why it must change:** the premise rests on T-196, now **DEMOTED to untested** (RR-1 frozen sizing
  capital; RR-2 overwritten Discovery verdict). Stating it as established overstates the record.
- **What must NOT change:** the gate's operative rules — no AI integrated until the system WITHOUT
  it beats the robo; judged only on making the whole system beat the robo by more; held to the same
  gauntlet/DSR/beat-robo gates; no special pleading. **None of those rests on T-196.** They are
  process rules, and they stand whatever B-1 finds.
- **Proposed replacement for the one premise clause:**
  > `the honest bar. The price vocabulary was reported H0-exhausted by T-196 (foundry,
  > conjunctive); that verdict is DEMOTED TO UNTESTED pending B-1 (the raw-signal decile
  > re-evaluation), because the referee that produced it is under repair (RR-1, RR-2). Until B-1
  > lands, treat the price vocabulary as UNTESTED — not exhausted, and not promising. Either way the
  > prior on "AI finds alpha" stays LOW, and NEW DATA modalities (text/news/filings the price
  > vocabulary cannot see) remain the more plausible place to look.`
- **Why this does not weaken the gate:** it removes a claim the record no longer supports, and adds
  none. The prior stays LOW; the burden of proof stays on AI; the integration bar is untouched. The
  only thing that changes is that we stop citing a demoted verdict as settled.
- **Why the prior stays LOW without T-196** — worth saying in the text, or the demotion will be read as
  lowering it. The LOW prior is the default for *every* alpha claim, not a conclusion drawn from one
  verdict; and new data modalities remain the better bet on general grounds — price is the most
  heavily mined input in markets. T-196 was one supporting pillar, never the foundation. Stating the
  ground explicitly closes the obvious misreading: *"demoted to untested"* is exactly the phrase a
  motivated reader turns into *"so maybe it works"*, and **an unproven vocabulary is not a promising
  one.**

---

## Deliverable 3 — the substrate manifest (reported; NOT re-pinned)

**Anchor:** `config/substrate_manifest.sha256` (14,120 lines). Entries found for the five named inputs:
**tr_reconciled 0 · VVIX 0 · SKEW 0 · Shiller 0 · DFII10 0.** None is pinned.

**The consequence first — sharper than the brief's "may lack the data".** Measured read-only on
2026-09-30 with the generator's own `verify` and a full diff via its `build_manifest()`:
**pinned 14,120 · on host 14,250 · MISSING 0 · EXTRA 130 · CHANGED 5.** `verify` requires an EXACT
match (`gen_substrate_manifest.py:170`) and `scripts/build_backtest_image.sh` runs it before every
build, so:
- **the backtest image cannot currently be rebuilt at all** against the host substrate without
  regenerating the manifest. Any existing backtest image predates `tr_reconciled` (07-02) and so the
  08-26 HMM repoint too; Batch runs on it see the panel **blind pre-2020 again**, because
  `macro_features._safe_load_price_csv` falls back to the shallow flat TLT when the deep copy is absent;
- **the paper image — the live fleet — is unaffected**: `build_paper_image.sh` does not verify against
  this manifest and `Dockerfile.paper` does not COPY `data/processed`;
- **5 VIX-term files are CHANGED since pinning** (`VIX`, `VIX9D`, `VIX3M`, `VIX6M`, `_meta.json`), so a
  backtest on the host today already reads a substrate that differs from the pinned one.

**Diagnosis — for four of the five, the scope is fine and the pin is merely stale.**
`scripts/gen_substrate_manifest.py:37` scans `SUBSTRATE_DIRS = ["data/processed", "data/raw",
"data/governor", "data/macro"]`; tr_reconciled lives under `data/processed/`, and VVIX, SKEW and
Shiller under `data/macro/`. No exclude rule covers them. They are unpinned because **the manifest
was last regenerated 2026-06-18** (`ad03a97`) — before tr_reconciled existed (T-256, 07-02) and
before the 08-26 repoint.

**Re-pin command** (per `docs/Core/execution_manual.md:726`; run on a machine holding the substrate,
commit in the same PR):
```bash
python3 scripts/gen_substrate_manifest.py verify     # expect the new files to show as unpinned
python3 scripts/gen_substrate_manifest.py generate   # then commit config/substrate_manifest.sha256
```
**Two cautions for whoever re-pins:** `generate` pins *whatever is on the host* — including the 5
changed VIX files and the 12 shallow flat ETF files the repoint routes around — so review the diff as
a statement of canonicity rather than rubber-stamp it. And DFII10 still will not be pinned (below).
This is B-7's blocker, and it is **harder** than the brief says: not "the image may lack the data" but
"the image cannot be rebuilt until the manifest is".

**[BEYOND BRIEF] DFII10 is not unpinned — it is ABSENT.** No DFII10 file exists anywhere under
`data/` (the `dfii.us.txt` under stooq is an unrelated equity ticker). It is read by
`engines/engine_a_alpha/edges/macro_real_rate_edge.py` via `MacroDataManager.load_cached`, whose cache
dir is `data/macro` (`engines/data_manager/macro_data.py:52`) — and `load_cached`
(`macro_data.py:221-226`) **returns an empty frame silently when the file is missing**: no warning,
no raise. That is the always-empty-channel class.
**Severity today: none live.** `macro_real_rate_v1` is `status: paused` in `edges.yml`, and
`real_rate_level` is an **AUX** column the production 7-feature HMM does not use
(`engines/engine_e_regime/macro_features.py:100-104`). But the edge's own docstring (line 6) claims
*"DFII10 10y real rate now feeds Engine E's HMM regime classifier"* — which overstates it. **Re-pin
does not apply; fetch first.** The silent `load_cached` is a latent hazard for its own unit.

---

## Deliverable 4 — one bootstrap (inventory + proposed API)

**The three the brief names**, verified at the cited lines:

| where | shape | block length | pairing |
|---|---|---|---|
| `core/metrics_engine.py:864` `bootstrap_distribution` | single series | `max(5, round(n^(1/3)))` | none |
| `scripts/deep_reverify_sleeve_t311.py:139` `paired` | two series | fixed **21** | **paired** |
| `scripts/excess_of_cash_attribution_t333.py:54` `block_ci` | single series | fixed **21** | none |

They disagree on block length and on pairing, so **the same data can receive different CIs
depending on which script measured it** — a consistency defect for a referee, not a style issue.

**[BEYOND BRIEF] "Three" undercounts.** A scan for block-resampling patterns matches **~44 files**
under `core/`, `engines/` and `scripts/` (an upper bound; some matches are incidental — the true
count needs a per-file read). One unification must account for all of them, not three.

**[BEYOND BRIEF] The word "stationary" is wrong in 4 of the 5 places that use it** — including the
project standard:

| file | calls itself | draws geometric block lengths? |
|---|---|---|
| `core/metrics_engine.py` | stationary | **no** — fixed-length moving-block |
| `scripts/excess_of_cash_attribution_t333.py` | stationary | **no** (my code) |
| `scripts/third_stream_battery.py` | stationary | **no** (my code) |
| `scripts/probe_spy_ci_low_kill_threshold.py` | stationary | **no** |
| `scripts/crisis_replay_t118b.py` | stationary | **yes** |

A stationary bootstrap (Politis-Romano 1994) draws geometric block lengths; fixed-length circular
blocks are a moving-block bootstrap. Same defect class as 2f: documentation naming a method the code
does not run. Two of the four are mine.

**Proposed single API** (in `core/metrics_engine.py`, the canonical home):
```python
def block_bootstrap(
    x: np.ndarray,                      # 1-D series, OR (n, k) for PAIRED series
    stat: Callable[[np.ndarray], float],
    *,
    block: int | None = None,           # None -> max(5, round(n ** (1/3)))
    scheme: Literal["moving", "circular", "stationary"],   # REQUIRED — no default
    iters: int = 1000,
    seed: int = 0,
    conf: float = 0.95,
) -> BootstrapResult:                   # point, ci_low, ci_high, block, scheme, n_valid
```
- **Pairing by construction:** a 2-D input resamples ROW-blocks, so paired statistics
  (Δ-Sortino, Δ-wealth, correlations) never destroy the dependence they measure.
- **The scheme is a REQUIRED argument and is RECORDED in the result**, so a CI states how it was made
  and the "stationary" mislabel becomes impossible rather than merely discouraged. *Reconciliation
  note:* one draft defaulted `scheme="circular"`; a default lets a caller omit the method and receive
  one silently — the exact path by which every mislabel in this section got in. Required, then.
- **Migration pins, then labels.** Route each caller through the API with **its current scheme, block
  and seed pinned**, so historical CIs reproduce bit-for-bit — that is a refactor. Harmonising schemes
  is a *separate, later* decision, and there **any** caller whose CI moves is labeled RE-SCORE, never a
  new trial. *Reconciliation note:* one draft labeled only moves larger than the interval's own width;
  a tolerance lets small shifts go unlabeled, which is the silent-drift shape the referee exists to
  prevent.

**Classified from executable index lines, docstrings stripped** (the first pass read prose and
repeated the mislabel — stripping docstrings is what gave the right answer):

| implementation | scheme in code | note |
|---|---|---|
| `metrics_engine.py:864` | moving-block, non-circular (`starts ∈ [0, n−block]`) | the standard |
| `industry_momentum_t213`, `vrp_edge_t174`, `tilt_decision_measure_t318_t320` | moving-block | t318/320 paired |
| `crisis_replay_t118b.py:386` / `:414` | circular / **stationary** | both correctly named |
| `per_edge_per_year_attribution.py:95` | **IID — deliberately** | unit is the TRADE; see below |
| `probe_spy_ci_low_kill_threshold.py:73` | **delegates to `MetricsEngine.bootstrap_distribution`** | the pattern to follow |

**The one IID implementation is a reasoned exception, not a `[NN-SHARPE-CI]` violation.** Its docstring
states the unit is the trade, since trades within a regime are not a contiguous series;
`[NN-SHARPE-CI]` forbids iid resampling of serially-correlated *returns*. Honest caveat: overlapping
positions can correlate trade outcomes. **Among the implementations classified, no `[NN-SHARPE-CI]`
violation was found** — checked before being claimed either way.

**On the count:** "~44" is files matching a resampling *pattern* (an upper bound, as noted); about
**20** distinct bootstrap *functions* were confirmed by name. Same scope, different units.

---

## Deliverable 5 — record correction: IRAs and crypto (proposal only; `paper_trader/` untouched)

**Director-verified 2026-09-30** (alpaca.markets/support, "can-ira-trade-crypto"): **Alpaca IRAs
cannot hold crypto**, and **IRAs are options Level 2 only.** I have not independently re-verified.

**Consequence for the record:** the BTC 5% leg (T-272; `paper_trader/btc_shadow.py`) is specified as
a crypto position. In the Roth, the only executable vehicle is a **spot-bitcoin ETF** (IBIT; MSBT at
0.14%). **Proposed text** for the spec and for any forward-validation note:
> *"In the Roth IRA the leg is executable only as a spot-bitcoin ETF (IBIT, or MSBT at 0.14% ER);
> Alpaca IRAs cannot hold crypto directly. Forward-validation must therefore track the ETF, including
> its expense ratio and any NAV/basis tracking error vs. spot BTC — not spot BTC itself."*

The ETF's tracking error vs. spot is a real difference from the backtest, not a formality.

---

## Deliverable 6 — "$0 short borrow" and the two branches

**`backtester/borrow_rate_model.py:231-243`** — the position-notional helper **returns `0.0` on
every failure path**: no price map, ticker missing, no `Close` column, empty slice, or *any*
exception (`except Exception: return 0.0`). A missing price therefore produces a borrow cost computed
on zero notional — **$0 borrow that looks like a real (cheap) number.** That is `[NN-FAIL-CLOSED]`'s
defect exactly. Proposed: raise, or return `None` with the caller treating it as a failure; never `0.0`.
(Practical impact is bounded while the book is long-only, which is why it is a record item and not an
incident.)

**The two branches are NOT lost — they are local-only and single-copy.**

| branch | where | unpushed commits | tip |
|---|---|---:|---|
| `feature/factor-neutrality-sizing-t218` | local, `trading_machine-2` | **7** | `39779fc` 2026-06-19 |
| `feature/no-borrow-cash-budget-t232` | local, `trading_machine-2` | **2** | `b582039` 2026-06-25 |

Neither exists on `origin`. They are recoverable today and would be gone with one disk — the same
exposure the autonomy ledger had before its survival unit. **Proposed (push is propose-first, so not
done):** push both to `origin` under an `archive/` prefix so the work survives the machine.

---

## How this document was produced — read before relying on it

After a machine restart this conversation resumed in **two Claude Code sessions at once**, and both
executed this brief in the same worktree (2026-09-30, 13:51–13:58). One instance's rewrite overwrote
the other's Deliverable 2; the other then appended duplicate D3 and D4 sections — **one of those
appends landed after the first instance had already posted a warning and stopped**, which was my
error. Both stood down on a director ruling; this file is the owner's reconciliation, using the more
complete draft as the base and folding in three items from the other. **Nothing was lost:** every
version survives in branch history (`6faf9e5`, `d1d470c`, `20841ed` for the folded-in text).

**The two executions reached the same five non-obvious findings independently** — the 0.887
misattribution, the Politis-White misnaming, the `[NN-MBL]` sibling-number tell, DFII10 absent rather
than unpinned, and the manifest stale since 06-18 — **which is decent evidence that they hold.** On
the MBL finding a third pass (RR-3) agrees as well.

## Summary for the reviewer
| # | status | needs a ruling on |
|---|---|---|
| 1 | done on branch | the `config/*.prod.json` rail vs. the brief's named exception |
| 2a–2h | proposal text | 2c (double error), 2e (sibling-number tell), 2g (the gap report's own tension), 2h (the AI-gate wording) |
| 3 | reported | re-pin — the backtest image **cannot be rebuilt** until it happens; DFII10 is ABSENT, not unpinned |
| 4 | inventory + API | ~20 functions (~44 matching files), not 3; "stationary" wrong in 4/5; **no `[NN-SHARPE-CI]` violation found**; `scheme` required, migration pins then labels |
| 5 | proposal text | — (director-verified) |
| 6 | reported | pushing the two local-only branches |
