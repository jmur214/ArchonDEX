---
name: pattern_product_moved_charters_stayed
description: 2026-09-17 fit-for-purpose audit — the live product is paper_trader/ + intelligence/ (~21k prod lines) but every charter/index/README still describes the A-F backtest stack; where the real god-module and duplication live now
metadata:
  type: project
---

The production system (3 Alpaca paper accounts, daily AWS Batch) runs on a ~21k-line
static import closure rooted at `scripts/run_paper_cloud_day.py` → `paper_trader/` +
`intelligence/`. Only ~4.5k lines of the ~53k-line engines/backtester/core stack are on
that path (wash guard, PortfolioPolicyConfig, MetricsEngine, TrendOverlay, census).

**Why it matters for future audits:**
- `engine_charters.md`, `high_level_engine_function.md`, `PROJECT_CONTEXT.md`,
  `docs/README.md`, and all 7 `index.md` files contain ZERO mention of `paper_trader`
  (checked 2026-09-17). Charter-vs-implementation audits scoped to A-F are auditing
  the legacy stack; the real authority boundaries (who may emit an OrderSpec, who
  may write DURABLE_PATHS) are unwritten.
- God-module has moved: `run_paper_cloud_day.py::main()` is a single 1,156-line
  function (lines 304-1460) with 15 lazy imports and 13 `args.strategy ==` branches.
  The account-1 trend_sleeve path is inline (:527) and deliberately bypasses the
  `_run_family_strategy` abstraction the other 4 strategies use (:596) — two code
  paths for the same job, the deployed one being the unrefactored one.
- Dead-code signature specific to this codebase: production importing T-numbered
  "research" scripts (`scripts/build_news_panel_t289.py`, `archive_altdata_t136.py`,
  `similarity_t237.py`, `archive_positioning_t136.py`). The T-suffix lies about
  liveness in BOTH directions — some T-scripts are prod, ~53 T-scripts are
  referenced by nothing.
- `CURRENT_STATE.md` "Last reconciled" stamp was 2026-07-27 on 2026-09-17 (7 weeks
  stale) while auto-memory + git log show major events through 09-16. The Stop hook
  that supposedly checks the stamp is not forcing reconciliation.

**How to apply:** when asked "does the architecture match the product", start from
the Dockerfile.paper entrypoint closure, not from `engines/`. Treat A-F charter
audits as legacy-stack audits unless the user says otherwise. See
[[pattern_flag_vs_path_disconnect]] for the liveness-tracing method.
