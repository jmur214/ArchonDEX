---
name: ui-never-mutates-machine-state
description: Cockpit hygiene rules — UI callbacks never write files that shadow engine/paper state; Command Center registers only argparse-verified, non-order-arming commands
metadata:
  type: feedback
---

Two hard hygiene rules from the WS5 legacy-regroup workstream (2026-07 dashboard overhaul), both directed by the design brief:

**1. A UI callback must never produce files that shadow the real machine's state.** The old dashboard_callbacks paper branch wrote `data/trade_logs/paper/*.csv` on every 2s tick — files that shadowed the REAL paper ledger (`data/paper_state/`). Removed. Same class: the mode_callbacks hidden-div callback did live Alpaca API calls to render into `display:none` — invisible network work, removed to a documented no-op register fn (keep the `register_*(app)` signature so app.py wiring never changes).

**Why:** the paper machine's state dir is the ledger of record for go-live validation; UI-written lookalike files are exactly the "silent shadow state" the census layer exists to catch.

**How to apply:** dashboards READ pre-computed state, period. When stubbing a dead callbacks module, keep the register function importable as a no-op with a docstring saying what was removed, why, and where the working pieces live now.

**2. Command Center = whitelisted registry, argparse-verified, no order-arming.** Before registering a command, READ the target script's argparse (`[NN-NO-GUESS-CLI]`) and cite the verification in a code comment. For `run_paper_cloud_day`: registered ONLY `--allocator mean_variance --strategy reconcile_only` (matches the production wrapper `paper_cloud_entrypoint.sh` + `config/paper_designated_allocator.json`). Deliberately EXCLUDED `--strategy trend_sleeve` from the dashboard — it arms order submission, and even `--dry-run` journals staged orders into `data/paper_state/orders.jsonl` (rule 1 violation). If a command can't be verified or safely scoped, leave it out.

Related: [[dashboard-v2-idiom]], [[paper-tab-degrade-patterns]].
