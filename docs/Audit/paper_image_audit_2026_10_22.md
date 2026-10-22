# Paper-fleet image audit — 2026-10-22 (director; approved by the user 2026-10-22; B's design, outbox :865-866)

> Point-in-time record (`[NN-AUDITS-NOT-CURRENT]`). **Method:** per live paper image, a dedicated job definition
> `archondex-image-audit-<digest8>` with NO `jobRoleArn` and NO `secrets` (the platform's execution role only, for the
> ECR pull and the log), Fargate / ARM64 (the images' own platform — the first attempt failed as EC2-shaped, the second
> as x86: `exec format error`; both definitions deregistered), on `archondex-backtest-queue` at 15:3x ET (outside the
> 09:30–10:00 firing window), a READ-ONLY listing, the CloudWatch log quoted below, the definition deregistered after.
> Job ids: acct-1 `b0c331bf-0f54-47b6-a9e9-427ceba5977b`; accts 2/3 `7b2481e6-54e4-4f9f-a7c7-f5164b2ed4f9`. Both SUCCEEDED.

## Verdicts (`[NN-FIRST-ARTIFACT]`: the container, not the Dockerfile)

| Claim | Image `paper-sha-75c9f65` (acct 1, pushed 2026-09-29) | Image `paper-sha-def0b89` (accts 2/3, pushed 2026-09-17) |
|---|---|---|
| A `.env` file baked into the image | **NONE** (`find /app -maxdepth 3 -name ".env*"` empty) | **NONE** |
| Secrets path | injected by the job definition's `secrets` block only (the entrypoint says so; the audit job, with no secrets block, saw only `AWS_*` / `ECS_*` names) | same |
| Data baked under `/app/data` | **40 files**: 39 `data/processed/tr_reconciled/*_1d.csv` (the ETF sleeve's price substrate) + `data/universe/sp500_membership_pit.parquet` | same 40 |
| `Dockerfile.paper:48-54` "exactly one data file … No other data substrate is baked" | **FALSE** — 39 `tr_reconciled` files are baked beside it (the comment is stale; the build wrapper stages them) | FALSE |
| `tr_reconciled/` baked into the paper image UNPINNED (the manifest MEDIUM row's claim) | **VERIFIED**: the 39 files are present; `config/substrate_manifest.sha256` (the June pin, 1,609,557 bytes) is present in the image — whether its scope covers `tr_reconciled` is the manifest row's question (B) | same |
| Equity processed cache, `data/state`, `data/governor`, fundamentals | **absent** (no `data/processed/*_1d.csv` outside `tr_reconciled`; no `data/state`; no governor files) | absent |
| Build provenance inside the image | **none** (no build-info file; the commit is known only from the tag) | none |
| Runtime | python 3.14.5, pandas 3.0.1, pyarrow 23.0.1, `/app`, root | same |
| Platform | Fargate, **ARM64** (`runtimePlatform` on the fleet's definitions; a redeploy or audit must declare it) | same |

**Closed by this artifact:** the question whether a `.env` rides in the fleet's containers (no); whether the equity cache rides (no); whether `tr_reconciled` rides (yes, 39 files, with the June manifest beside it). **Owed:** the `Dockerfile.paper` comment correction (rides with the next docker touch, as already recorded); the manifest row's scope question for `tr_reconciled` (B, re-pin #1); a build-info file in the image (a one-line proposal, B).

## Log — acct 1 (`paper-sha-75c9f65`)

```
== image audit ==
pwd=/app user=0
python 3.14.5 pandas 3.0.1 pyarrow 23.0.1
== /app top ==
total 212
drwxr-xr-x.  1 root root  4096 Sep 29 18:45 .
drwxr-xr-x.  1 root root  4096 Oct 22 19:32 ..
drwxr-xr-x.  4 root root  4096 Sep 22 23:19 .agent
-rw-r--r--.  1 root root   359 Sep 22 23:19 .aider.conf.yml
-rw-r--r--.  1 root root   197 Sep 22 23:19 .aiderignore
-rw-r--r--.  1 root root  2093 Sep 22 23:19 .dockerignore
drwxr-xr-x.  3 root root  4096 Sep 22 23:19 .github
-rw-r--r--.  1 root root  2695 Sep 22 23:19 .pre-commit-config.yaml
drwxr-xr-x. 20 root root  4096 Sep 22 23:19 Archive
-rw-r--r--.  1 root root  8453 Sep 22 23:19 Dockerfile.backtest
-rw-r--r--.  1 root root  3385 Sep 22 23:19 Dockerfile.paper
-rw-r--r--.  1 root root 15520 Sep 22 23:19 README.md
-rw-r--r--.  1 root root     5 Sep 22 23:19 _tmp_probe.txt
drwxr-xr-x.  2 root root  4096 Sep 22 23:19 analytics
drwxr-xr-x.  2 root root  4096 Sep 22 23:19 backtester
drwxr-xr-x.  2 root root  4096 Sep 22 23:19 brokers
-rw-r--r--.  1 root root  3113 Sep 22 23:19 clean_data.py
drwxr-xr-x.  2 root root  4096 Sep 22 23:19 cockpit
-rw-r--r--.  1 root root   534 Sep 22 23:19 cockpit_dashboard_v2.py
drwxr-xr-x.  5 root root  4096 Sep 22 23:19 config
drwxr-xr-x.  5 root root  4096 Sep 22 23:19 core
drwxr-xr-x.  4 root root  4096 Sep 29 18:45 data
drwxr-xr-x.  2 root root  4096 Sep 22 23:19 debug
-rw-r--r--.  1 root root  1694 Sep 22 23:19 debug_config.py
drwxr-xr-x. 10 root root  4096 Sep 22 23:19 engines
drwxr-xr-x.  3 root root  4096 Sep 22 23:19 infra
drwxr-xr-x.  5 root root  4096 Sep 22 23:19 intelligence
drwxr-xr-x.  4 root root  4096 Sep 22 23:19 ops
drwxr-xr-x.  2 root root  4096 Sep 22 23:19 orchestration
drwxr-xr-x.  2 root root  4096 Sep 22 23:19 paper_trader
-rw-r--r--.  1 root root   862 Sep 22 23:19 pytest.ini
-rw-r--r--.  1 root root   848 Sep 22 23:19 reproduce_fundamentals.py
-rw-r--r--.  1 root root  1671 Sep 22 23:19 requirements.lock.txt
-rw-r--r--.  1 root root   904 Sep 22 23:19 requirements.txt
drwxr-xr-x.  2 root root  4096 Sep 22 23:19 research
drwxr-xr-x.  4 root root 20480 Sep 22 23:19 scripts
-rw-r--r--.  1 root root  3010 Sep 22 23:19 seed_governor_data.py
drwxr-xr-x.  4 root root 20480 Sep 22 23:19 tests
drwxr-xr-x.  2 root root  4096 Sep 22 23:19 utils
== .env files anywhere under /app ==
(none above = none)
== /app/data tree (dirs) ==
/app/data
/app/data/processed
/app/data/processed/tr_reconciled
/app/data/universe
== /app/data files: count + list ==
40
/app/data/processed/tr_reconciled/PFF_1d.csv
/app/data/processed/tr_reconciled/XLE_1d.csv
/app/data/processed/tr_reconciled/XLC_1d.csv
/app/data/processed/tr_reconciled/XLV_1d.csv
/app/data/processed/tr_reconciled/PGX_1d.csv
/app/data/processed/tr_reconciled/IEF_1d.csv
/app/data/processed/tr_reconciled/EEM_1d.csv
/app/data/processed/tr_reconciled/DBC_1d.csv
/app/data/processed/tr_reconciled/TIP_1d.csv
/app/data/processed/tr_reconciled/XLY_1d.csv
/app/data/processed/tr_reconciled/XLI_1d.csv
/app/data/processed/tr_reconciled/PCEF_1d.csv
/app/data/processed/tr_reconciled/SCHD_1d.csv
/app/data/processed/tr_reconciled/MUB_1d.csv
/app/data/processed/tr_reconciled/VIXY_1d.csv
/app/data/processed/tr_reconciled/XLF_1d.csv
/app/data/processed/tr_reconciled/LQD_1d.csv
/app/data/processed/tr_reconciled/JEPI_1d.csv
/app/data/processed/tr_reconciled/DBMF_1d.csv
/app/data/processed/tr_reconciled/SPY_1d.csv
/app/data/processed/tr_reconciled/XLU_1d.csv
/app/data/processed/tr_reconciled/XLB_1d.csv
/app/data/processed/tr_reconciled/QQQ_1d.csv
/app/data/processed/tr_reconciled/SVXY_1d.csv
/app/data/processed/tr_reconciled/EFA_1d.csv
/app/data/processed/tr_reconciled/AGG_1d.csv
/app/data/processed/tr_reconciled/BND_1d.csv
/app/data/processed/tr_reconciled/IWM_1d.csv
/app/data/processed/tr_reconciled/BIL_1d.csv
/app/data/processed/tr_reconciled/XLP_1d.csv
/app/data/processed/tr_reconciled/XLRE_1d.csv
/app/data/processed/tr_reconciled/SHY_1d.csv
/app/data/processed/tr_reconciled/XLK_1d.csv
/app/data/processed/tr_reconciled/KMLM_1d.csv
/app/data/processed/tr_reconciled/TLT_1d.csv
/app/data/processed/tr_reconciled/HYG_1d.csv
/app/data/processed/tr_reconciled/GLD_1d.csv
/app/data/processed/tr_reconciled/VNQ_1d.csv
/app/data/processed/tr_reconciled/UUP_1d.csv
/app/data/universe/sp500_membership_pit.parquet
== /app/config ==
total 1740
drwxr-xr-x. 5 root root    4096 Sep 22 23:19 .
drwxr-xr-x. 1 root root    4096 Sep 29 18:45 ..
-rw-r--r--. 1 root root       0 Sep 22 23:19 __init__.py
-rw-r--r--. 1 root root    1684 Sep 22 23:19 account_routing.json
-rw-r--r--. 1 root root    8185 Sep 22 23:19 advisor_tier_table.json
-rw-r--r--. 1 root root    4117 Sep 22 23:19 advisor_tier_table.schema.json
-rw-r--r--. 1 root root     575 Sep 22 23:19 alpha_settings.dev.json
-rw-r--r--. 1 root root    1802 Sep 22 23:19 alpha_settings.json
-rw-r--r--. 1 root root    1412 Sep 22 23:19 alpha_settings.prod.json
-rw-r--r--. 1 root root    1798 Sep 22 23:19 alpha_settings.validated.json
-rw-r--r--. 1 root root    3324 Sep 22 23:19 backtest_settings.json
-rw-r--r--. 1 root root    1763 Sep 22 23:19 deploy_candidate.json
-rw-r--r--. 1 root root    1626 Sep 22 23:19 discovery_settings.json
-rw-r--r--. 1 root root    6417 Sep 22 23:19 edge_config.json
-rw-r--r--. 1 root root    1872 Sep 22 23:19 fitness_profiles.yml
-rw-r--r--. 1 root root    5404 Sep 22 23:19 fomc_calendar.json
-rw-r--r--. 1 root root     697 Sep 22 23:19 governor_settings.json
drwxr-xr-x. 2 root root    4096 Sep 22 23:19 grids
-rw-r--r--. 1 root root     209 Sep 22 23:19 harness_assumptions.json
-rw-r--r--. 1 root root    3760 Sep 22 23:19 information_cohorts.json
-rw-r--r--. 1 root root    1142 Sep 22 23:19 intel_sources.json
-rw-r--r--. 1 root root    2619 Sep 22 23:19 llm_settings.json
-rw-r--r--. 1 root root    2127 Sep 22 23:19 macro_impact.json
-rw-r--r--. 1 root root     660 Sep 22 23:19 oos_window.json
-rw-r--r--. 1 root root     976 Sep 22 23:19 paper_designated_allocator.json
-rw-r--r--. 1 root root     196 Sep 22 23:19 portfolio_policy.json
-rw-r--r--. 1 root root    1672 Sep 22 23:19 portfolio_settings.json
drwxr-xr-x. 6 root root    4096 Sep 22 23:19 prompts
-rw-r--r--. 1 root root    2990 Sep 22 23:19 regime_settings.json
-rw-r--r--. 1 root root     257 Sep 22 23:19 risk_settings.dev.json
-rw-r--r--. 1 root root     745 Sep 22 23:19 risk_settings.json
-rw-r--r--. 1 root root     291 Sep 22 23:19 risk_settings.prod.json
-rw-r--r--. 1 root root    1548 Sep 22 23:19 sector_map.json
-rw-r--r--. 1 root root       0 Sep 22 23:19 settings.py
-rw-r--r--. 1 root root    4547 Sep 22 23:19 spinoff_events_curated.yml
-rw-r--r--. 1 root root    1199 Sep 22 23:19 substantially_identical.json
-rw-r--r--. 1 root root 1609557 Sep 22 23:19 substrate_manifest.sha256
-rw-r--r--. 1 root root    1288 Sep 22 23:19 universe.json
drwxr-xr-x. 2 root root    4096 Sep 22 23:19 wf
== manifest present? ==
-rw-r--r--. 1 root root 1609557 Sep 22 23:19 /app/config/substrate_manifest.sha256
== entrypoint head ==
#!/usr/bin/env bash
# scripts/paper_cloud_entrypoint.sh
#
# Container entrypoint for the daily CLOUD paper loop (T-186).
# EventBridge Scheduler → AWS Batch (Fargate) → this script.
#
# Thin by design: the heavy lifting (pull durable state from S3, run the
# T-185 calendar-aware cycle, push state back, emit the CloudWatch
# dead-man's-switch metrics, set the exit code) lives in
# scripts/run_paper_cloud_day.py so it is unit-testable. This wrapper only
# fixes the environment and forwards the exit code.
#
# Creds: ALPACA_API_KEY / ALPACA_SECRET_KEY are injected as env vars by
# the Batch job definition's `secrets` block (valueFrom an AWS Secrets
# Manager ARN). This script NEVER reads, prints, or persists them.
#
# Required env (set by the job definition):
#   ARCHONDEX_PAPER_STATE_BUCKET   durable-state S3 bucket (journal/ledger/heartbeat)
#   AWS_DEFAULT_REGION             us-east-1
# Optional:
#   ARCHONDEX_PAPER_STATE_PREFIX   default "paper_state"
#   ARCHONDEX_PAPER_ALLOCATOR      default "mean_variance"
set -uo pipefail
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ALLOC="${ARCHONDEX_PAPER_ALLOCATOR:-mean_variance}"
# T-238: strategy = reconcile_only (default, the proven pulse) | trend_sleeve.
STRATEGY="${ARCHONDEX_PAPER_STRATEGY:-reconcile_only}"
# Optional small-notional cap for the FIRST armed sleeve run (cautious test);
# unset → the sleeve sizes to the full paper account.
== git describe baked? ==
no build info file
== env var NAMES only (values never printed) ==
AWS_BATCH_CE_NAME AWS_BATCH_JOB_ATTEMPT AWS_BATCH_JOB_ID AWS_BATCH_JQ_NAME AWS_DEFAULT_REGION AWS_EXECUTION_ENV AWS_REGION ECS_AGENT_URI ECS_CONTAINER_METADATA_URI ECS_CONTAINER_METADATA_URI_V4 HOME HOSTNAME PATH PWD PYTHONUNBUFFERED PYTHON_SHA256 PYTHON_VERSION SHLVL _ 
== end ==
```

## Log — accts 2/3 (`paper-sha-def0b89`)

```
== image audit ==
pwd=/app user=0
python 3.14.5 pandas 3.0.1 pyarrow 23.0.1
== /app top ==
total 212
drwxr-xr-x.  1 root root  4096 Sep 18 02:58 .
drwxr-xr-x.  1 root root  4096 Oct 22 19:34 ..
drwxr-xr-x.  4 root root  4096 Sep 18 00:58 .agent
-rw-r--r--.  1 root root   359 Sep 18 00:58 .aider.conf.yml
-rw-r--r--.  1 root root   197 Sep 18 00:58 .aiderignore
-rw-r--r--.  1 root root  2093 Sep 18 00:58 .dockerignore
drwxr-xr-x.  3 root root  4096 Sep 18 00:58 .github
-rw-r--r--.  1 root root  2695 Sep 18 00:58 .pre-commit-config.yaml
drwxr-xr-x. 20 root root  4096 Sep 18 00:58 Archive
-rw-r--r--.  1 root root  8453 Sep 18 00:58 Dockerfile.backtest
-rw-r--r--.  1 root root  3385 Sep 18 00:58 Dockerfile.paper
-rw-r--r--.  1 root root 15520 Sep 18 00:58 README.md
-rw-r--r--.  1 root root     5 Sep 18 00:58 _tmp_probe.txt
drwxr-xr-x.  2 root root  4096 Sep 18 00:58 analytics
drwxr-xr-x.  2 root root  4096 Sep 18 00:58 backtester
drwxr-xr-x.  2 root root  4096 Sep 18 00:58 brokers
-rw-r--r--.  1 root root  3113 Sep 18 00:58 clean_data.py
drwxr-xr-x.  2 root root  4096 Sep 18 00:58 cockpit
-rw-r--r--.  1 root root   534 Sep 18 00:58 cockpit_dashboard_v2.py
drwxr-xr-x.  5 root root  4096 Sep 18 00:58 config
drwxr-xr-x.  5 root root  4096 Sep 18 00:58 core
drwxr-xr-x.  4 root root  4096 Sep 18 02:58 data
drwxr-xr-x.  2 root root  4096 Sep 18 00:58 debug
-rw-r--r--.  1 root root  1694 Sep 18 00:58 debug_config.py
drwxr-xr-x. 10 root root  4096 Sep 18 00:58 engines
drwxr-xr-x.  3 root root  4096 Sep 18 00:58 infra
drwxr-xr-x.  5 root root  4096 Sep 18 00:58 intelligence
drwxr-xr-x.  4 root root  4096 Sep 18 00:58 ops
drwxr-xr-x.  2 root root  4096 Sep 18 00:58 orchestration
drwxr-xr-x.  2 root root  4096 Sep 18 00:58 paper_trader
-rw-r--r--.  1 root root   862 Sep 18 00:58 pytest.ini
-rw-r--r--.  1 root root   848 Sep 18 00:58 reproduce_fundamentals.py
-rw-r--r--.  1 root root  1671 Sep 18 00:58 requirements.lock.txt
-rw-r--r--.  1 root root   904 Sep 18 00:58 requirements.txt
drwxr-xr-x.  2 root root  4096 Sep 18 00:58 research
drwxr-xr-x.  4 root root 20480 Sep 18 00:58 scripts
-rw-r--r--.  1 root root  3010 Sep 18 00:58 seed_governor_data.py
drwxr-xr-x.  4 root root 20480 Sep 18 00:58 tests
drwxr-xr-x.  2 root root  4096 Sep 18 00:58 utils
== .env files anywhere under /app ==
(none above = none)
== /app/data tree (dirs) ==
/app/data
/app/data/universe
/app/data/processed
/app/data/processed/tr_reconciled
== /app/data files: count + list ==
40
/app/data/universe/sp500_membership_pit.parquet
/app/data/processed/tr_reconciled/UUP_1d.csv
/app/data/processed/tr_reconciled/TIP_1d.csv
/app/data/processed/tr_reconciled/XLB_1d.csv
/app/data/processed/tr_reconciled/HYG_1d.csv
/app/data/processed/tr_reconciled/DBC_1d.csv
/app/data/processed/tr_reconciled/XLC_1d.csv
/app/data/processed/tr_reconciled/XLE_1d.csv
/app/data/processed/tr_reconciled/QQQ_1d.csv
/app/data/processed/tr_reconciled/XLV_1d.csv
/app/data/processed/tr_reconciled/XLK_1d.csv
/app/data/processed/tr_reconciled/PCEF_1d.csv
/app/data/processed/tr_reconciled/GLD_1d.csv
/app/data/processed/tr_reconciled/XLY_1d.csv
/app/data/processed/tr_reconciled/BIL_1d.csv
/app/data/processed/tr_reconciled/DBMF_1d.csv
/app/data/processed/tr_reconciled/SVXY_1d.csv
/app/data/processed/tr_reconciled/IEF_1d.csv
/app/data/processed/tr_reconciled/IWM_1d.csv
/app/data/processed/tr_reconciled/XLI_1d.csv
/app/data/processed/tr_reconciled/SCHD_1d.csv
/app/data/processed/tr_reconciled/VNQ_1d.csv
/app/data/processed/tr_reconciled/XLP_1d.csv
/app/data/processed/tr_reconciled/XLF_1d.csv
/app/data/processed/tr_reconciled/XLRE_1d.csv
/app/data/processed/tr_reconciled/BND_1d.csv
/app/data/processed/tr_reconciled/KMLM_1d.csv
/app/data/processed/tr_reconciled/XLU_1d.csv
/app/data/processed/tr_reconciled/PFF_1d.csv
/app/data/processed/tr_reconciled/EEM_1d.csv
/app/data/processed/tr_reconciled/MUB_1d.csv
/app/data/processed/tr_reconciled/AGG_1d.csv
/app/data/processed/tr_reconciled/JEPI_1d.csv
/app/data/processed/tr_reconciled/PGX_1d.csv
/app/data/processed/tr_reconciled/EFA_1d.csv
/app/data/processed/tr_reconciled/SHY_1d.csv
/app/data/processed/tr_reconciled/VIXY_1d.csv
/app/data/processed/tr_reconciled/TLT_1d.csv
/app/data/processed/tr_reconciled/LQD_1d.csv
/app/data/processed/tr_reconciled/SPY_1d.csv
== /app/config ==
total 1740
drwxr-xr-x. 5 root root    4096 Sep 18 00:58 .
drwxr-xr-x. 1 root root    4096 Sep 18 02:58 ..
-rw-r--r--. 1 root root       0 Sep 18 00:58 __init__.py
-rw-r--r--. 1 root root    1684 Sep 18 00:58 account_routing.json
-rw-r--r--. 1 root root    8185 Sep 18 00:58 advisor_tier_table.json
-rw-r--r--. 1 root root    4117 Sep 18 00:58 advisor_tier_table.schema.json
-rw-r--r--. 1 root root     575 Sep 18 00:58 alpha_settings.dev.json
-rw-r--r--. 1 root root    1802 Sep 18 00:58 alpha_settings.json
-rw-r--r--. 1 root root    1412 Sep 18 00:58 alpha_settings.prod.json
-rw-r--r--. 1 root root    1798 Sep 18 00:58 alpha_settings.validated.json
-rw-r--r--. 1 root root    3324 Sep 18 00:58 backtest_settings.json
-rw-r--r--. 1 root root    1763 Sep 18 00:58 deploy_candidate.json
-rw-r--r--. 1 root root    1626 Sep 18 00:58 discovery_settings.json
-rw-r--r--. 1 root root    6417 Sep 18 00:58 edge_config.json
-rw-r--r--. 1 root root    1872 Sep 18 00:58 fitness_profiles.yml
-rw-r--r--. 1 root root    5404 Sep 18 00:58 fomc_calendar.json
-rw-r--r--. 1 root root     697 Sep 18 00:58 governor_settings.json
drwxr-xr-x. 2 root root    4096 Sep 18 00:58 grids
-rw-r--r--. 1 root root     209 Sep 18 00:58 harness_assumptions.json
-rw-r--r--. 1 root root    3760 Sep 18 00:58 information_cohorts.json
-rw-r--r--. 1 root root    1142 Sep 18 00:58 intel_sources.json
-rw-r--r--. 1 root root    1986 Sep 18 00:58 llm_settings.json
-rw-r--r--. 1 root root    2127 Sep 18 00:58 macro_impact.json
-rw-r--r--. 1 root root     660 Sep 18 00:58 oos_window.json
-rw-r--r--. 1 root root     976 Sep 18 00:58 paper_designated_allocator.json
-rw-r--r--. 1 root root     196 Sep 18 00:58 portfolio_policy.json
-rw-r--r--. 1 root root    1672 Sep 18 00:58 portfolio_settings.json
drwxr-xr-x. 6 root root    4096 Sep 18 00:58 prompts
-rw-r--r--. 1 root root    2990 Sep 18 00:58 regime_settings.json
-rw-r--r--. 1 root root     257 Sep 18 00:58 risk_settings.dev.json
-rw-r--r--. 1 root root     745 Sep 18 00:58 risk_settings.json
-rw-r--r--. 1 root root     291 Sep 18 00:58 risk_settings.prod.json
-rw-r--r--. 1 root root    1548 Sep 18 00:58 sector_map.json
-rw-r--r--. 1 root root       0 Sep 18 00:58 settings.py
-rw-r--r--. 1 root root    4547 Sep 18 00:58 spinoff_events_curated.yml
-rw-r--r--. 1 root root    1199 Sep 18 00:58 substantially_identical.json
-rw-r--r--. 1 root root 1609557 Sep 18 00:58 substrate_manifest.sha256
-rw-r--r--. 1 root root    1288 Sep 18 00:58 universe.json
drwxr-xr-x. 2 root root    4096 Sep 18 00:58 wf
== manifest present? ==
-rw-r--r--. 1 root root 1609557 Sep 18 00:58 /app/config/substrate_manifest.sha256
== entrypoint head ==
#!/usr/bin/env bash
# scripts/paper_cloud_entrypoint.sh
#
# Container entrypoint for the daily CLOUD paper loop (T-186).
# EventBridge Scheduler → AWS Batch (Fargate) → this script.
#
# Thin by design: the heavy lifting (pull durable state from S3, run the
# T-185 calendar-aware cycle, push state back, emit the CloudWatch
# dead-man's-switch metrics, set the exit code) lives in
# scripts/run_paper_cloud_day.py so it is unit-testable. This wrapper only
# fixes the environment and forwards the exit code.
#
# Creds: ALPACA_API_KEY / ALPACA_SECRET_KEY are injected as env vars by
# the Batch job definition's `secrets` block (valueFrom an AWS Secrets
# Manager ARN). This script NEVER reads, prints, or persists them.
#
# Required env (set by the job definition):
#   ARCHONDEX_PAPER_STATE_BUCKET   durable-state S3 bucket (journal/ledger/heartbeat)
#   AWS_DEFAULT_REGION             us-east-1
# Optional:
#   ARCHONDEX_PAPER_STATE_PREFIX   default "paper_state"
#   ARCHONDEX_PAPER_ALLOCATOR      default "mean_variance"
set -uo pipefail
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ALLOC="${ARCHONDEX_PAPER_ALLOCATOR:-mean_variance}"
# T-238: strategy = reconcile_only (default, the proven pulse) | trend_sleeve.
STRATEGY="${ARCHONDEX_PAPER_STRATEGY:-reconcile_only}"
# Optional small-notional cap for the FIRST armed sleeve run (cautious test);
# unset → the sleeve sizes to the full paper account.
== git describe baked? ==
no build info file
== env var NAMES only (values never printed) ==
AWS_BATCH_CE_NAME AWS_BATCH_JOB_ATTEMPT AWS_BATCH_JOB_ID AWS_BATCH_JQ_NAME AWS_DEFAULT_REGION AWS_EXECUTION_ENV AWS_REGION ECS_AGENT_URI ECS_CONTAINER_METADATA_URI ECS_CONTAINER_METADATA_URI_V4 HOME HOSTNAME PATH PWD PYTHONUNBUFFERED PYTHON_SHA256 PYTHON_VERSION SHLVL _ 
== end ==
```
