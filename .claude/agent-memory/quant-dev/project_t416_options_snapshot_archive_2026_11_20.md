---
name: project-t416-options-snapshot-archive
description: T-416 (2026-11-20) daily options snapshot archive — design decisions (universe, expiry rule, real-quote rule, coverage floor, per-day zstd files, verifier wiring) and why; branch only, first production artifact owed after merge
metadata:
  type: project
---

T-416 was built 2026-11-20 on branch `worktree-agent-aeda84432f0d9481c` and is not merged. The owner approved it the same day: build our own options history (quotes and IV), since no free one exists.

**Why:** Alpaca has no historical option quotes, and IV and greeks exist only as current snapshot values. A daily forward archive is the only free source. See [[reference-alpaca-options-api-quirks-2026-11-20]].

**Code, outputs and wiring**
- Code: `scripts/archive_options_snapshots.py`.
- Universe: `config/options_archive_universe.json`, 49 underlyings:
  - SPY, QQQ, IWM;
  - XSP, which needs proxy SPY and has no IV;
  - 45 large S&P names drawn from the 117-name earnings-calendar set.
- Output: `data/macro_data/options/options_snapshot_YYYY-MM-DD.parquet`, plus a run log `_archive_runs.jsonl`. The leading underscore keeps pyarrow dataset reads off the log.
- Wiring:
  - `run_altdata_archivers.sh` runs it with its own `RC4`, before the verifier.
  - `verify_altdata_snapshot.py` has its own local-only options check.
  - `paper_trader/altdata_archive.py` lists are untouched, because the cloud never collects options.

**Decisions and rationale**
- **Expiries:** take the last listed expiry of each Mon–Sun week (4 of them), then the next 2 weeks that contain a third Friday. Only expiries strictly after the session date count. "Next 4 expiries" would have covered only about 4 trading days, since dailies exist even on single names.
- **Real quote:** all three must hold:
  - the quote is stamped on the ET session date;
  - bid > 0, or a last trade > 0 on the same session;
  - 0 < ask, with bid ≤ ask ≤ the no-arbitrage bound (S for a call, K for a put).
  
  IV must also be finite and > 0, unless the config sets `iv_expected: false`. The freshness leg matters: SPX-root quotes were a day stale on expiry day.
- **Coverage:** an underlying is covered when it has at least 10 real rows AND at least 30 % of its rows are real. FAILED (rows kept) when coverage is below 90 % of declared underlyings, OR when any REQUIRED underlying (SPY, QQQ, IWM, XSP) is not covered. Zero real quotes → FAILED, nothing written.
  - The required and share legs were added AFTER reading the live smoke by content. At 15:59:59 ET the feed zeroed 164 XSP quotes (0/0, size 0, exchange "?"). The rule caught those rows, but a fully wiped XSP would have hidden inside a 48/49 "OK" day.
- **Live smoke** (2026-11-20 16:16 ET, after the close, full universe):
  - 21,136 contracts, 19,004 real (90 %); 979,555 B (46 B/row), so about 1 MB/day and about 250 MB/yr.
  - 343 requests (293 data + 50 trading), 0 × 429, 109 s.
  - Every non-real row was "IV missing": 1,411 bid-0 deep OTM, 721 deep ITM.
  - Lowest real share 0.68 (PEP); fewest real rows 110 (NKE).
- **Verifier:** re-judges by CONTENT, recomputing the rule rather than trusting the stored `real_quote` flag. On a weekend it checks the previous session, so a missed Friday alarms on Saturday. An empty store on a non-trading day is a SKIP, so the first post-merge run does not false-alarm.
- **Storage:**
  - One file per day, not per month: an atomic tmp + os.replace touches only that day.
  - zstd level 9 gives 46-51 B/row on real data. Level 19 saves only 3 %, and byte_stream_split saved nothing.
  - Floats stay float64; float32 was rejected because it rounds prices.

**How to apply:** for the first production run after merge ([NN-FIRST-ARTIFACT]), read the file by content: the real share per underlying, the categories of non-real rows, and quote timestamps on the session date. The 18:30 ET feed state was observed only up to the smoke time on 2026-11-20. If the feed blanks quotes later in the evening, the first night FAILS loudly by design.
