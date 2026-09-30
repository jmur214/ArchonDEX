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
- **Proposed:** `At the current honest N (231 as of 2026-09-30 — read it live from
  compute_n_effective(), do not transcribe it), the 5-year substrate-honest window requires
  SR ≥ ~1.5 to clear DSR under the upper-bound form above.` ⚠ RR-3 proposes the exact E[max] form;
  if it lands, this sentence should quote its number instead.

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

---

## Deliverable 3 — the substrate manifest (reported; NOT re-pinned)

**Anchor:** `config/substrate_manifest.sha256` (14,120 lines). Entries found for the five named inputs:
**tr_reconciled 0 · VVIX 0 · SKEW 0 · Shiller 0 · DFII10 0.** None is pinned.

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
⚠ **The cloud image may lack the 08-26 repoint data until it is re-baked**: it bakes `data/processed/`
from the host at build time, and the repointed HMM panel depends on `data/processed/tr_reconciled/`
— which no manifest entry currently guarantees is present. This is exactly B-7's blocker.

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
    scheme: Literal["moving", "circular", "stationary"] = "circular",
    iters: int = 1000,
    seed: int = 0,
    conf: float = 0.95,
) -> BootstrapResult:                   # point, ci_low, ci_high, block, scheme, n_valid
```
- **Pairing by construction:** a 2-D input resamples ROW-blocks, so paired statistics
  (Δ-Sortino, Δ-wealth, correlations) never destroy the dependence they measure.
- **The scheme is a named argument and is RECORDED in the result**, so a CI states how it was made
  and the "stationary" mislabel becomes impossible rather than merely discouraged.
- **Migration is RE-SCORE-labeled** where any historical verdict's CI moves by more than the width of
  its own interval — never a new trial.

---

