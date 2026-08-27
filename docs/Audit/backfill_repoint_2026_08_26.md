# The backfill repoint — consumer census, two infrastructure fixes, and the `[NN-SUBSTRATE-REVERIFY]` verdict

**Date:** 2026-08-26 · **Agent:** B · Branch `feature/backfill-repoint` · **0 N_trials**

Follows the partial-backfill finding: 12 of 730 tickers in `data/processed/` were never
deepened and still stop at the 2020-04-09 Alpaca boundary — `DBC, DKNG, EEM, GLD, IEF, IWM,
MARA, QQQ, RIOT, TLT, USO, UUP`, six of them load-bearing.

## 1. Consumer census — every reader of a shallow ticker, by price source

| source | n | reading |
|---|--:|---|
| **`data/processed` (SHALLOW)** | **12** | at risk on any pre-2020 window |
| `tr_reconciled` (T-256) | 6 | correct |
| `stooq` | 14 | split-only, separate known issue; not this defect |
| no direct load (ticker passed in) | 16 | inherits its caller's source |

The 12 at-risk: `universe_resolver.py`, `composite_edge.py`, `update_data.py`,
**`core/benchmark.py`**, `discovery.py`, **`macro_features.py`**, and the T-278/T-031/T-262/
T-257/T-285 measurement scripts plus `run_paper_cloud_day.py`.

## 2. `[NN-SUBSTRATE-REVERIFY]` verdict: **NULL for every historical measurement** — verified

The dispatch hoped this was null "since the measurement path honored T-256". It is, and the
discipline is better than hoped — **the caveat was already known and written down**:

- **T-257** discovered it: *"data/processed GLD starts 2020-04"*.
- **T-278** inherited the caveat verbatim and set `start = "2020-01-01"` accordingly.
- **T-262** `start="2020-01-01"`; **T-031** `--is-start 2021-01-01`; **T-285** does not use
  `data/processed` at all (it pulls yfinance directly — a classifier false positive).

And confirmed against stored artifacts rather than by reading code alone: every persisted
gate output (`oos_validation_q1..q3`, `cap_recalibration_a0..a3`, `c1_path2_revalidation`)
carries **`n_obs` of 249 or 1004** — 1 and 4 years, both comfortably inside the shallow
copy's 1,513-bar coverage. **No stored measurement ever reached past the truncation.**

**But the discipline held only where a human was looking.** Two pieces of shared
infrastructure had no such caveat and would have truncated silently:

### 2a. `core/benchmark.py` — the promotion gate (LATENT, never exercised)
`gate_sharpe_vs_benchmark(mode="strongest")` — the default — thresholds on the strongest of
SPY / QQQ / 60-40, and **QQQ and TLT are both shallow**. Measured on 2005-2026 before the fix:

| benchmark | n_obs | Sharpe |
|---|--:|--:|
| SPY | **5,355** | +0.632 |
| QQQ | **1,512** | **+0.998** |
| 60/40 | **1,512** | +0.698 |

The docstring said so out loud: *"falls back to whatever coverage is available (logs
nothing)"*. QQQ's true deep Sharpe is **0.753** — the threshold ran **+0.245 too HIGH**, and
MDD read −35.1% instead of −53.4% (the GFC simply absent). The tell was visible: requesting
2005 and 2010 returned **byte-identical** QQQ numbers. Direction matters — an inflated
threshold produces **false negatives**, so nothing was ever promoted on an inflated basis.

### 2b. `engines/engine_e_regime/macro_features.py` — the HMM (REAL, but report-only)
`tlt_ret_20d` NaN on **82.1%** of the panel → uniform posterior on every pre-2020-05 bar,
with no `degraded` flag and no census coverage. Real, but harmless downstream: the merged
repoint verified every HMM consumer is inert.

## 3. Fixes applied

**`core/benchmark.py`** — prefers `tr_reconciled` (T-256), and **fails closed on coverage**:
- `_resolve_path` is now the single selection authority; `_source_of` calls it, so a reported
  provenance can no longer drift from the file actually read (it did, briefly, mid-fix).
- **Convention consistency wins over span**: a price-only SPY compared against a total-return
  QQQ is biased by the missing dividend yield (T-256: SPY 0.685%/yr) — a subtler error than a
  short window, because nothing about the output looks wrong.
- Two guards, both raising `BenchmarkCoverageError`: **(G1)** the data must reach the
  requested start, and **(G2)** the comparison set must span equal windows. G1 exists because
  G2 alone cannot see three benchmarks that truncate *together*.
- `BenchmarkMetrics` now carries `source` / `first_obs` / `last_obs`.
- Escape hatch is explicit (`allow_unequal_coverage=True`), never a silent default.

**Effect:** on 2006-2026 all three now span 5,103 bars on one convention, and the promotion
threshold corrects from **+0.798 → +0.593**. The winning benchmark also changes (QQQ → 60/40,
whose bond leg was reading the 2020-2026 bond bear at Sharpe −0.421 instead of +0.282).

**`macro_features.py`** — `_safe_load_price_csv` takes `tr_reconciled` **only when the flat
copy is materially shallower**, so SPY keeps its 1993 depth and the trained model's feature
distribution moves as little as possible. Complete panel rows **1,493 → 5,041 (17.9% → 60.3%)**,
span back to **2006-04-04 — exactly the crisis model's `train_start`**.

Verified before applying: the baked `tlt_ret_20d` normalization (mean 0.004012, std 0.036708)
vs tr_reconciled (0.005436 / 0.036629) — std matches to three decimals, mean shifts **0.04σ**,
consistent with TLT's dividend yield. Deep *price-only* TLT no longer exists, so this is the
only deep option. Posteriors after the repoint, on dates the panel previously could not see:

    2008-10-15  crisis=1.00      2010-05-20  stressed=1.00     2018-12-24  stressed=1.00
    2008-11-20  crisis=1.00      2011-08-08  stressed=1.00     2020-03-16  stressed=1.00

All were uniform-blind before. (COVID reading *stressed* rather than *crisis* matches T-103's
documented behaviour — the crisis label concentrates on 2008-magnitude tails.)

## 4. A bug this fix introduced and caught
Preferring `tr_reconciled` via a module-level constant frozen at import **silently defeated
`DEFAULT_DATA_DIR` overrides**, so an isolated run read PRODUCTION prices. Caught by
`test_synthetic_downtrend_produces_negative_sharpe`, which had written synthetic data and got
real-market Sharpe 0.875 back. Path resolution is now relative to the *effective* base dir at
call time, and a hermeticity test pins it.

## 5. Not repointed (deliberate)
The 10 remaining shallow consumers are either frozen historical scripts whose windows already
respect the caveat (T-278/T-262/T-257/T-031), infrastructure that passes tickers through
(`universe_resolver`, `update_data`), or the live paper path (`run_paper_cloud_day` fetches
from the broker, not the CSV). Changing a frozen measurement script would alter a published
result; they are correct as written.

## 6. Tests
`tests/test_benchmark_substrate_repoint_2026_08_26.py` (10) — T-256 sourcing, fallback,
**hermeticity**, provenance-cannot-drift, both guards separately, all-truncate-together,
explicit escape hatch, gate propagation. Plus 2 in `test_hmm_repoint_t_2026_08_26.py` — deeper
substrate per ticker (SPY keeps 1993) and *the HMM can now see the GFC at all*.
