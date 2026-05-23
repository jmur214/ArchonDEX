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

## How to submit a campaign

The launcher is `scripts/submit_substrate_run.py`. It currently hardcodes the substrate-measurement shape (reps × arms). For non-substrate campaigns (e.g., vol-target A/B, regime-conditional A/B/C), copy the launcher and adapt the `Cell` dataclass + job-submission loop — see "Adapting the launcher for a new campaign" below.

```bash
python scripts/submit_substrate_run.py --reps 3 --arms 1,2
```

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

The `:dev` tag bakes the project source + `data/processed/` + governor templates at build time. Any time main has commits the image hasn't seen, the image must be rebuilt and pushed BEFORE submitting jobs — otherwise the campaign runs stale code.

**Manual (until CI takes over — see `.github/workflows/build_backtest_image.yml`):**

```bash
# From repo root, on a clean main checkout.
docker build -f Dockerfile.backtest -t archondex-backtest:dev .

aws ecr get-login-password --profile archondex --region us-east-1 \
  | docker login --username AWS --password-stdin \
    407539788432.dkr.ecr.us-east-1.amazonaws.com

docker tag archondex-backtest:dev \
  407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:dev

docker push 407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:dev
```

Build ~5 min (deps + project + bake data). Push ~2-5 min on residential. The Batch job def is set to `imagePullPolicy=Always` so a fresh push is picked up on the next job submit; no `aws batch register-job-definition` rerun needed.

**Automatic:** the GitHub Actions workflow at `.github/workflows/build_backtest_image.yml` rebuilds + pushes `:dev` on every push to main. Once that's set up + verified, the manual sequence above is the fallback for "I need this rebuilt RIGHT NOW and can't wait for CI."

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
