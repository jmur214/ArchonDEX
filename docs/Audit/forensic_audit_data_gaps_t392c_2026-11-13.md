# Forensic audit — did the archived `audit_data_gaps.py` cause the write-time-band HIGH? (T-392c)

- Date: 2026-11-12 (filed under the brief's 2026-11-13 name). Author: T-392 worker (quant-dev lens). READ-ONLY:
  nothing under `data/` was written; the substrate manifest verified PASS (14,259 files, md5 prefix `44d3be53`)
  before and after.
- Subject: `Archive/scripts/audit_data_gaps_ARCHIVED_2026_11_12.py` (archived on main `9b10fc8`), formerly
  `scripts/audit_data_gaps.py`.
- Question: does the script's signature appear in the canonical price cache or its history, and does it relate
  to the health HIGH "The pre-T-167 GLOBAL-median×3 band, applied at WRITE time …"?

## Verdict

**DID NOT RUN on any surviving price file.** Neither the canonical cache (`data/processed/*_1d.csv`, 730 files)
nor the Alpaca leg it was merged from (`data/processed_alpaca_backup_2026_05_23`, 730 files) carries any part of
the signature. A run on files overwritten before 2026-04-18 (including the three CSVs committed in January 2026)
is **NOT ESTABLISHED**: nothing records one, and on those files a run would have left nothing detectable. That
question does not reach the canonical cache, because every surviving file was rewritten afterwards.

**Relation to the band HIGH: a DIFFERENT mechanism.** The script cannot be the HIGH's cause. The HIGH's
attribution to the write-time band stands, unaffected.

## What the script would have left

`main()` runs an audit pass, then an unconditional "repair" over `data/*_1d.csv` and `data/processed/*_1d.csv`.
Per file it:

1. lowercases every column name;
2. adds a `timestamp` column (parsed from `date` when there is no `timestamp`);
3. drops NaT-dated rows and sorts;
4. clips `open` and `close` to [0.5, 1.5] × the whole-history median, leaving `high` and `low` untouched;
5. writes the CSV only, so the parquet twin is untouched.

Clipping preserves the median. So a clipped series reads max/median == 1.5 exactly whenever any bar was above the
band, and min/median == 0.5 exactly whenever any bar was below it. The bars at the bounds form plateaus while
High/Low keep moving.

## Evidence

| Check | Canonical `data/processed` (730) | Pre-merge Alpaca leg (730) |
|---|---|---|
| Header | 730 × `Date,Open,High,Low,Close,Volume,ATR,PrevClose` | 719 standard; 8 `Date,Close,High,Low,Open,…`; 3 without ATR/PrevClose |
| Lowercase OHLC / `timestamp` column | 0 / 0 | 0 / 0 |
| Close max/median == 1.5 or min/median == 0.5 (to 1e-9) | **0 files**; 668 have closes outside the band, so a run would have marked at least 668 | **0 files**; 598 would have been marked |
| Open, same test | 0 (669 would) | 0 |
| csv vs parquet Close, common dates | 730 twins, 0 diffs > 1e-6, 0 date-set differences | 727 twins (3 absent), 0 diffs, 0 date-set differences |
| File mtimes | 729 at 2026-05-23 11:05:50 UTC; SPY at 2026-06-14 04:10 UTC | 2026-04-18 → 2026-05-22 |

- **Near-hits are coincidences.**
  - 12 canonical files have ≥ 2 bars landing exactly on 1.5× or 0.5× their median. Every one has max/median between
    2.4 and 17, not 1.5. Tick-rounded prices hit a round multiple: COL at a 0.05 tick, for example.
  - 15 files have Close outside [Low, High], 808 bars in all. Of those bars, 775 are CPWR, where 832 bars carry a
    0.01 placeholder close with min == median (a provider defect, not a 0.5× clip). The other 14 files have 1–5
    such bars each, none at a clip bound.
- **No carried plateau.** A clip followed by an incremental rewrite would leave many bars on one exact Close while
  High ≠ Low. The median file's most frequent Close occurs 3 times, and the 99th percentile is about 22. The
  outliers are all something else:
  - CPWR 832, the placeholder above;
  - CFC 286, NCC 206 and BMC 134 are acquired names with High == Low;
  - VRT 22 is the 2018 GSAH SPAC at about $9.70.
- **The merge record agrees.**
  - `_merge_meta.json` was `generated_at` 2026-05-23T11:05:50.92Z, the canonical mtimes to the second.
    `alpaca_source` was `data/processed`; the result was 626 `both` and 104 `alpaca_only`.
  - The merge read each leg CSV with `df["Date"]`. That is `scripts/merge_stooq_alpaca_substrate.py:111-112`, and
    a `KeyError` there is not caught, so a lowercased leg would have crashed it.
  - 163 of the 626 `both` names have a seam-date close outside the clip band, so a clipped leg would have moved
    their seam. The merge recorded max |seam_close_diff_pct| 0.43 % and 0 anomalies > 1 %.
- **Git history.**
  - The script was added in `62c3eaf` (2025-10-21) and stayed byte-identical until `9b10fc8` (2026-11-12). No
    commit message or diff records a run. Docs only describe it: README in `cb61f4f`, and in `3e5288c`
    `codebase_findings.md` says "attempts repairs (clipping)".
  - Price CSVs were committed from 2025-10-15 to 2026-04-09: `3c9cc9f`, `48f3212`, `62c3eaf`, `cb61f4f`.
    `3e5288c` removed them. At `62c3eaf` the header is mixed-case `timestamp,symbol,Open,…,ATR,PrevClose`, so the
    script had not run on those bytes.
  - At `cb61f4f` (2026-01-27), AAPL, MSFT and SPY read `timestamp,open,high,low,close,volume,trade_count,vwap`.
    That is exactly what `scripts/fetch_data.py` wrote at that commit (`bars.df.reset_index()`, `symbol` dropped,
    `to_csv(index=False)`). A script run on the `62c3eaf` files would have kept `symbol`/`atr`/`prevclose`.
  - Those three series lie inside the clip band (max/median 1.29–1.45, min/median ≥ 0.54). A run on them is undetectable: the clip
    is a no-op and the header idempotent. That is the one NOT ESTABLISHED case.
- **Logs.** No file under `data/logs` (133 files, 130 MB) contains the script's output strings ("Running optional
  repair", "open/close clipped", "suspicious gaps in", "candidate CSVs"). The repo-root logs don't either.
  `data/*_1d.csv`, the script's other target, holds 0 files today.

## Why the mechanisms differ

| | Write-time band (the HIGH) | `audit_data_gaps.py` |
|---|---|---|
| Where | `DataManager._normalize_df` before `save_cache` (pre-T-167, bd68438^:527-529) | a manual script |
| Rule | DROP every row with Close ≥ 3 × the fetched frame's global median | CLIP open/close values to [0.5, 1.5] × median |
| Rows | removed, so files end early and have holes | all kept (only NaT-dated rows dropped) |
| Kept values | unchanged | altered; High/Low untouched, so Close can fall outside [Low, High] |
| csv/parquet | written together | csv only, so they diverge |

The script cannot remove a bar. The HIGH is about missing bars: 33 early ends, 114 holed files, and the replayed
band date sets EQUAL the saved files for NVDA, PLTR, GE, FICO, AXON and SEDG. This audit removes the script as an
alternative cause. It neither adds to nor subtracts from the band evidence.

## Reproduce (read-only)

The core test per file. `d` is a cache dir: `data/processed` or `data/processed_alpaca_backup_2026_05_23`.

```python
import numpy as np, pandas as pd
from pathlib import Path
for f in sorted(Path(d).glob("*_1d.csv")):
    df = pd.read_csv(f); c = df["Close"][df["Close"] > 0]; m = c.median()
    clipped = np.isclose(c.max() / m, 1.5, rtol=0, atol=1e-9) or np.isclose(c.min() / m, 0.5, rtol=0, atol=1e-9)
    p = pd.read_parquet(Path(d) / "parquet" / f.name.replace(".csv", ".parquet"))   # csv vs parquet Close
    # report: header line, clipped, (df.set_index(pd.to_datetime(df.Date)).Close - p.Close).abs().max()
```

The other checks used the same reads:

- the plateau scan: `Close.value_counts()` and the High ≠ Low share at the top value;
- the seam-band count against `_merge_meta.json` `per_ticker[*].seam_date`;
- `git show <commit>:<path>` over the commits above.
