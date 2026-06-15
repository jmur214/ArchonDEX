# Cloud Usage — how any session uses the AWS Batch backtest infra

**Status:** active 2026-05-22 onward.
**Companion:** [`CLOUD_RUNBOOK.md`](CLOUD_RUNBOOK.md) is the SETUP doc (one-time, AWS Console, IAM, etc.). This is the USAGE doc — what any session (director / Agent A / Agent B) does to actually run a campaign on cloud.

---

## TL;DR pre-flight

```bash
# 1. AWS reachable?
aws sts get-caller-identity --profile archondex
# Expected: account 407539788432, user claude-code-cli

# 2. Batch queue healthy?
aws batch describe-job-queues --profile archondex --region us-east-1 \
  --job-queues archondex-backtest-queue --query 'jobQueues[0].state' --output text
# Expected: ENABLED

# 3. ECR image fresh? (compare to git HEAD)
aws ecr describe-images --repository-name archondex-backtest --image-ids imageTag=dev \
  --profile archondex --region us-east-1 \
  --query 'imageDetails[0].imagePushedAt' --output text
# Expected: a date >= the most recent main commit. If staler, see "Refreshing the image" below.
```

If any check fails: STOP. Don't submit jobs against broken infra. Surface the failure to the director with the error text.

---

## When to use cloud vs. local

**Use cloud when:**
- Campaign is parallelizable into ≥ 4 independent cells (years × reps × arms)
- Total local sequential wall-time would exceed ~2 hours
- You'd otherwise block the user's laptop for a long stretch

**Stay local when:**
- One-off debugging or a single backtest
- < 4 cells (orchestration overhead dominates wall-time savings)
- The change is mid-iteration (rebuild + push cycle is ~10 min vs. seconds to re-run locally)
- You don't have the AWS credentials configured (run pre-flight check 1)

**Rule of thumb:** if `cells × per_cell_hours > 4`, prefer cloud.

---

## ⚠️ Verify-first protocol (mandatory before any full A/B campaign)

Before launching any campaign with > 2 cells, run a **2-cell verify spec** to confirm the patch actually takes effect. T-055g v1 (2026-05-24) cost $1.50 and ~67 min cloud wall on a 75-cell campaign where ALL 5 arms produced identical results because my patch keys used the wrong namespace (`risk.vol_target.X` vs the actual flat `portfolio_vol_target_X`).

The verify catches this in ~10-15 min for $0.04:

```json
{
  "campaign_id": "<your-campaign>-verify",
  "years": [<one-year>],
  "reps": 1,
  "arms": {
    "arm_off": { "config_patch": {} },
    "arm_on": {
      "config_patch": {
        "config/<target>.json": {
          "<key-that-should-affect-canon>": <value>
        }
      }
    }
  }
}
```

Run it. Pull the manifests. **The two cells' `canon_md5` MUST differ.** If they match → patch didn't apply → fix BEFORE launching the full grid. See [`CLOUD_LESSONS_LEARNED.md`](CLOUD_LESSONS_LEARNED.md) gotcha #3 for the full incident report + key-namespace discipline (always grep the actual config-load path for field names).

For determinism validation specifically (cross-container reproducibility), also run a 2-cell OFF-vs-OFF empty-patch check; canon must MATCH between the two reps. Catches the T-057c-determinism class of bug (dict-iteration-order FP-summation drift) which local `--runs N` cannot see.

### ⚠️ Trigger/overlay campaigns: the "mildest-config-fires" pre-flight (mandatory; T-118 lesson)

For any campaign whose arms are gated behind a TRIGGER (a de-gross overlay, a regime
switch, a confidence gate — anything that only acts when a condition crosses a threshold),
the 2-cell verify above is necessary but NOT sufficient: a clean patch can still produce
arm == arm0 in every cell because **the trigger never fired**. T-118 spent a full 52-cell
cloud grid where the overlay armed in ZERO cells — every arm reproduced an arm0 canon — because
the grid's δ-floor (0.30) sat above the trigger's firing threshold. The whole campaign was a
null-by-non-firing (it never tested the thesis), and it predates this note.

**The gate:** BEFORE the grid spend, prove the MILDEST armed config actually fires on a
KNOWN activation event, locally. For a transition de-gross overlay: pick a window containing
an unambiguous regime transition (e.g. 2022), and confirm the lowest-δ arm produces a canon
that DIFFERS from arm0 (i.e. it changed at least one trade). If nothing in the proposed grid
fires on a known transition, the grid is mis-specified — fix the thresholds (or the trigger
formulation) BEFORE launching. A firing-curve sweep (δ from low→the grid floor on the known
event) is the cheapest way to locate a firing δ and set the grid floor below it.

---

## How to submit a campaign

The launcher is `scripts/submit_substrate_run.py`. It currently hardcodes the substrate-measurement shape (reps × arms). For non-substrate campaigns (e.g., vol-target A/B, regime-conditional A/B/C), copy the launcher and adapt the `Cell` dataclass + job-submission loop — see "Adapting the launcher for a new campaign" below.

```bash
python scripts/submit_substrate_run.py --reps 3 --arms 1,2
```

**`--job-timeout` defaults (T-109 lesson):** the job-definition default (30 min) only fits single-year cells. Deep windows need explicit overrides — and budget headroom over the naive estimate: T-109's 26-yr cell completed its full backtest and was SIGKILLed during the S3 upload because the timeout was 20 minutes too tight (the result needed a CloudWatch log-scrape to recover). Reference wall-times on the clean image: ~8-10 min/sim-year.

| Window | `--job-timeout` (109-ticker static) | `--job-timeout` (T-167 full ~96-ticker universe) |
|---|---|---|
| single-year | 3600 (1 h) | 3600 (1 h) |
| 12-yr | 10800 (3 h) | 18000 (5 h) |
| 16-yr | 14400 (4 h) | 28800 (8 h) |
| **26-yr** | 21600 (6 h) | **36000 (10 h) — full-universe deep windows; 12h is safer (T-128r/T-118r 2026-06-14: original 6h cells SIGKILLed mid-run; A relaunched at 10h, C used 12h)** |

**⚠️ T-167 change (2026-06-14): the cloud now runs the FULL ~96-ticker historical universe (the `_normalize_df` load-truncation that ran a ~19-ticker universe is fixed), so deep-window cells take MUCH longer than the old static-109 numbers. Use the right-hand column for any full-universe run, and bump the launcher default.**

**What this does (under the hood):**

1. Submits N=reps × arms Batch jobs via `aws batch submit-job`, one per cell.
2. Each job pulls `archondex-backtest:dev` from ECR, runs `python -m scripts.run_isolated --runs 1` inside the container (`scripts/cloud_entrypoint.sh` is the entrypoint).
3. Container writes its trade log + `performance_summary.json` to S3 under `s3://archondex-results-407539788432/<cell_id>/<run_id>/`.
4. Launcher polls `aws batch describe-jobs` until every job reaches SUCCEEDED or FAILED.
5. Launcher fetches per-cell manifests from S3, writes a CSV summary to `data/cloud_runs/substrate_<launch_ts>.csv`, prints the summary table.

**Cost model (rough, per launch):**

| Cells | Fargate cost | Wall clock |
|---|---:|---|
| 6 (3 reps × 2 arms) | ~$0.60 on-demand / ~$0.18 spot | ~1.5-2 hr |
| 30 (5 yr × 3 rep × 2 arm) | ~$3 on-demand / ~$1 spot | ~1.5-2 hr (still parallel) |
| 150 (full-substrate scan) | ~$15 on-demand | ~2-3 hr |

Monthly budget alarm is set at $20 → triple-digit job counts will trigger billing alerts before they become a problem.

---

## Refreshing the image

The `:dev` tag bakes the project source + `data/processed/` + `data/raw/` + governor ANCHORS at build time. Any time main has commits the image hasn't seen, the image must be rebuilt and pushed BEFORE submitting jobs — otherwise the campaign runs stale code.

**THE ONLY SANCTIONED BUILD PATH (T-127/T-133 — do NOT run raw `docker build .`):**

**`:dev` IS RETIRED (T-155, per A's T-140 recommendation):** the mutable tag is provenance-unverifiable — a campaign can't prove which commit/substrate it ran. Campaigns use **sha-tags + the env-pinned job definition** only. Submit with an explicit `--job-def` / job-definition whose image is the `sha-<short>` tag of a `build_backtest_image.sh` build.

```bash
# From any worktree (symlinked data/ subdirs are followed).
# Registry-direct (preferred; ~8GB less local disk):
ARCHONDEX_BUILD_PUSH=1 scripts/build_backtest_image.sh HEAD \
    407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:sha-<short>
# Local build:
scripts/build_backtest_image.sh <git-ref> archondex-backtest:<tag>

aws ecr get-login-password --profile archondex --region us-east-1 \
  | docker login --username AWS --password-stdin \
    407539788432.dkr.ecr.us-east-1.amazonaws.com

docker tag archondex-backtest:dev \
  407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:dev

docker push 407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:dev
```

Why script-only (the T-125→T-127 saga in one paragraph): raw `docker build .` bakes the LIVE WORKTREE — host `__pycache__` (which the container then EXECUTES in place of the source — the stale-bytecode bug that produced a fake +0.21 Sharpe at 26-yr), untracked junk, uncommitted file states. The script builds from `git archive <commit>` (worktree-independent by construction), verifies the data substrate against the committed `config/substrate_manifest.sha256` (drifted data = loud failure, not a silently moved canon), and labels the image with commit + substrate provenance. Two builds of the same commit produce the same canon — proven 3-builds-1-canon (`529e5520…`, T-127).

**Substrate manifest policy (T-131):** `data/processed/` + `data/raw/` + governor ANCHORS are pinned by the manifest; the 9 LIVE mutable governor files (`edges.yml`, `edge_weights.json`, `regime_edge_performance.json`, `lifecycle_history.csv`, `ga_population.yml`, `lifecycle_journal.jsonl`, `.journal_apply_mark`, `edge_metrics.json`, `decision_diary.jsonl`) are excluded from BOTH the manifest and the image bake (T-133) — they are canon-irrelevant (the in-container harness restores scoped files from `_isolated_anchor/` on entry; the rest are write-only observability). Local runs therefore can NOT block builds.

**Anchor-update procedure (deliberate, director-coordinated):** the anchors are shared across all worktrees via symlink (T-133) and write-protected (0o444). To change them: (1) `python -m scripts.run_isolated --save-anchor` in the director worktree; (2) `python3 scripts/gen_substrate_manifest.py generate`; (3) commit the regenerated manifest in the SAME PR with a note on why the seed state changed. A drifted anchor is a measurement-invalidating event — never update it casually.

Build ~3-5 min (deps + project + bake data). Push ~5-50 min on residential. The Batch job def is set to `imagePullPolicy=Always` so a fresh push is picked up on the next job submit; no `aws batch register-job-definition` rerun needed.

**Automatic:** the GitHub Actions workflow at `.github/workflows/build_backtest_image.yml` rebuilds + pushes `:dev` on every push to main — BLOCKED until the `AWS_ROLE_TO_ASSUME` repo secret is configured (see `docs/Audit/ecr_rebuild_static20_t109_2026_06_05.md` Part A). It should be migrated to call `scripts/build_backtest_image.sh` when revived.

---

## Fetching results back

Per-cell trade logs land in S3. To pull all results from a launch into a local dir:

```bash
aws s3 sync s3://archondex-results-407539788432/<launch_prefix>/ \
  data/trade_logs_cloud/<launch_id>/ \
  --profile archondex --region us-east-1
```

After sync, the existing `scripts/metrics_report.py` CLI (T-069) operates on those run_ids directly:

```bash
python -m scripts.metrics_report \
  --run-ids $(ls data/trade_logs_cloud/<launch_id>/ | paste -sd,)
```

---

## Failure modes + recovery

| Symptom | Likely cause | Fix |
|---|---|---|
| `aws sts get-caller-identity` fails | Credentials missing/expired on this Mac | Re-run `aws configure --profile archondex`; values in 1Password |
| `aws batch list-jobs` returns nothing within ~30 sec of submit | Compute env is scaling up cold | Wait — first job in a cold pool takes ~3-5 min to start |
| All cells FAILED at the same second | Image issue (stale `:dev`, broken dep) | `aws logs tail /aws/batch/job --follow --profile archondex` for the first failed job's stderr |
| One cell FAILED, others SUCCEEDED | Cell-specific data issue OR non-determinism in the harness | Pull the cell's `aws logs tail` output; re-run that cell alone |
| Wall clock much longer than expected | Compute env using on-demand vs spot, OR vCPU quota throttling | Check `aws batch describe-compute-environments`; check vCPU service quota |
| S3 sync returns 403 | IAM policy gap for the bucket prefix | The `claude-code-cli` policy grants `archondex-results-*` — verify the prefix matches |

If something genuinely breaks at the AWS-resource level (job def gone, compute env failed): the source of truth is `CLOUD_RUNBOOK.md` for what's supposed to exist; the IAM policy is at `docs/Cloud/iam_policy_claude_code_cli.json`.

---

## Adapting the launcher for a new campaign

`submit_substrate_run.py` is shaped for the substrate-measurement campaign (reps × arms over a fixed config). For a new campaign type:

1. Copy `submit_substrate_run.py` → `submit_<campaign>_run.py`.
2. Update the `Cell` dataclass to carry whatever per-cell parameters your campaign needs (year, rep, arm, config patches, etc.).
3. Update the `aws batch submit-job` call's `containerOverrides.environment` to pass per-cell env vars.
4. The container's entrypoint (`scripts/cloud_entrypoint.sh`) reads those env vars and dispatches to whatever Python script your campaign uses.
5. Keep the same S3-write convention so `metrics_report.py` works on the output.

**Future direction:** when there are 3+ campaign-specific launchers, refactor into a single `scripts/submit_cloud_run.py` that takes the campaign shape as input. Premature now; revisit after T-055e.

---

## Sessions are interchangeable

Director, Agent A, Agent B all share `~/.aws/credentials` (user-level on the Mac, visible from every worktree). Any of the three can:

- Run pre-flight checks
- Build + push the image (each from their own clean worktree)
- Submit a campaign
- Pull results back via S3

There's no per-session AWS resource to provision. The cloud is a shared backend; the protocol determines who launches what (director dispatches; agents execute).
