---
name: daily-run-writes-under-root
description: Which run_paper_cloud_day writers resolved output from the module's checkout (fixed 2026-11-19 on branch fix/daily-run-writes-under-root-2026-11-19), which READERS still do, the hazards found on the way (news_panel reads a hard-coded main .env; the mirror block's json NameError), and how to drive main() so steps 7/8 actually run
metadata:
  type: project
---

Five writers on the daily path wrote into the CHECKOUT whatever `root` main() was given; all now take
the run's root (commit c753a3a, unmerged at 2026-11-19, director merges on the user's word):
eval harness (`run(root=)`: log + summary written, notes + event ledger READ under root), digest
(`generate(root=)`: docs/State + docs/Measurements archive), news panel (`append_today(root=)`, runs on
EVERY account), the two alt-data archivers (`run_altdata_archive` swaps the modules' `OUT_DIR` global for
the jobs' duration — the same global their `--out-dir` flag sets; every write site reads it at call time),
and the intel pulse's event ledger (`ledger_path=` into `pulse_step`, model-gated).
**Why:** a reviewer's simulation on 2026-11-17 replaced main's analyst_eval_summary.json and failed the gate.
In the container root == /app == every module's ROOT, so paths are unchanged (verified: production-shape
drive on baseline vs fix wrote the same 25 paths, 22 byte-identical, 3 differing only in wall-clock stamps).

**Still module-ROOT readers (not fixed, reads only):** eval `_disk_price`/`KALSHI_SNAP`/`FRED_PATH`,
`context_builder.PRED_LOG`/`EVENTS_PARQUET`, `eightk_feed.SPECIAL_SITS`, `build_news_panel_t289.full_universe`,
`load_designated_allocator`, archivers' `KALSHI_SERIES_CONFIG`.

**Hazards found, reported, NOT fixed:** (1) `intelligence/news_panel._creds()` reads the HARD-CODED main-repo
`.env` path into os.environ (setdefault) — any tree, any test reaching `append_today` without stubbing
`_client` loads real Alpaca keys. (2) `run_paper_cloud_day.py` never imports `json`; the fleet-mirror block's
`json.loads(yesterday's slice)` raises NameError inside a bare except → `prev_tier_equity` is always None →
`day_change` null every day in production.

**How to apply (driving main() in a test):** older driver tests' cloud stubs lack `pull_altdata`/
`pull_news_month`, so steps 7/8 raise AttributeError into their fail-open excepts and NEVER RUN — a lock
built that way is blind to those writers. Give the stub those methods, stub `news_panel._client`/
`_fetch_universe`, stub the archiver jobs (or fake `_get`/`_get_bytes`), and refuse sockets
(`socket.socket.connect`, `getaddrinfo`). The digest fires only on a FRIDAY (2026-09-18 works); only the
trend_sleeve branch reaches eval + digest. Lock: tests/test_daily_run_writes_under_its_root_2026_11_19.py.
See [[reversion-harness-and-worktree-bash]].
