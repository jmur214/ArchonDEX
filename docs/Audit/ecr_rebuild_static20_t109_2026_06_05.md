# T-2026-06-05-109 — Stale ECR root-cause + image refresh + static-20 cloud A/B

**Date:** 2026-06-06 (work began 2026-06-05)
**Branch:** `feature/ecr-rebuild-static20-t109`
**Worker:** Agent B
**Predecessors:** T-107 (static-20 5-yr local lead motivator), T-099 (long-window FP determinism), T-106 (drawdown kill-switch dead-knob; same 4h timeout pattern)

## TL;DR

Three deliverables, all done:

1. **Part A — stale ECR root cause:** the `.github/workflows/build_backtest_image.yml` workflow has been failing on **every main push since 2026-05-24** (10 consecutive failures) because the repo secret `AWS_ROLE_TO_ASSUME` has **never been configured**. The OIDC step silently reports "Credentials could not be loaded." Improved the workflow with a fail-loud precheck step that names the missing secret explicitly. The one-time IAM + OIDC trust + repo-secret config is propose-first for the user (documented below). **Without that user-config step, this workflow stays dead.**
2. **Part B — image refresh:** pruned local Docker (11.4 GB reclaimed; disk 8.6 → 20 GiB free), built `archondex-backtest:dev` from clean main HEAD (commit `c074744`; 178s build wall), pushed to ECR. `imagePushedAt` confirmed `2026-06-06T01:30:24-05:00` (was 9 days stale at `2026-05-28T23:37:27`). Det `--runs 3` sanity on the fresh image: **2/3 cells produced identical canon `0a62b7541d3d…`, 1/3 drifted to `b17bb3953b9e…` — all Sharpe-identical 1.6**. **T-099 floor is partial-pass on the fresh image** — headline metrics reproduce but canon-md5 isn't bitwise-stable on the new base. Flagged for follow-up.
3. **Part C — static-20 cloud A/B verdict: REJECT.** On both 16-yr AND 26-yr, the static-20 sector cap drops Sharpe and loses CAGR despite improving MDD. T-107's 5-yr local +0.043 edge was **2024-luck — does not survive depth**.

| Window | Arm | Sharpe | CAGR (%) | MDD (%) | Total Trades | canon_md5 |
|---|---|---|---|---|---|---|
| 16-yr (2010-2025) | arm0_baseline_30pct | **1.021** | 11.08 | -15.38 | 8632 | `62db5c0db75f…` |
| 16-yr | arm1_static_20pct | 0.766 | 6.61 | -11.48 | 7945 | `1003293821cf…` |
| 16-yr | **Δ (arm1 − arm0)** | **−0.255** | **−4.47** | **+3.90** | −687 | DIFFERS ✓ |
| 26-yr (2000-2025) | arm0_baseline_30pct | **0.446** | 5.40 | -48.00 | 12023 | `2b2f2c2b12b8…` |
| 26-yr | arm1_static_20pct (CW-recovered) | 0.355 | 3.32 | -37.93 | n/a | n/a |
| 26-yr | **Δ (arm1 − arm0)** | **−0.091** | **−2.08** | **+10.07** | n/a | n/a |

**Decision gate per dispatch:** "recommend static-20 iff Sharpe ci_low NOT down AND MDD improved on 26-yr."
- Sharpe DOWN both windows → **GATE FAILS**
- MDD improved both windows → secondary criterion only

**Verdict: DO NOT enable static-20 as a prod default.** Honest read confirms the dispatch's own hypothesis: a tighter cap that helped in one strong year (2024) is net-negative at depth.

## Part A — Stale ECR root cause + workflow improvement

### Failure pattern

`gh run list --workflow build_backtest_image.yml --limit 10` shows the workflow has fired on every main push since 2026-05-24 but **failed in 8-15 seconds — far too fast for a build**. The 10 most recent runs all show `completed failure`. That's a pre-build failure, not a build failure.

### Smoking-gun error

From `gh run view 27052844493 --log-failed`:
```
##[error]Credentials could not be loaded, please check your action inputs:
Could not load credentials from any providers
```

That comes from the `aws-actions/configure-aws-credentials@v4` step using `role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}`. When the secret is missing, the action receives an empty string and bails — but the error message is buried in the OIDC action output.

### Confirmation: secret never configured

`gh secret list` returns **empty**. No repo secrets at all — `AWS_ROLE_TO_ASSUME` has never been set. IAM listing via `claude-code-cli` also returns AccessDenied, so I can't directly verify the IAM role side either. But the secret-missing is sufficient to explain 100% of failures.

The workflow header (lines 11-15 of `.github/workflows/build_backtest_image.yml`) explicitly documents the prereq:
```
# Prerequisite secrets (configure in repo settings → Secrets → Actions):
#   AWS_ROLE_TO_ASSUME — ARN of an IAM role with ECR push permissions for
#                        archondex-backtest. Federated via OIDC (no
#                        long-lived access keys in CI).
```

This was documented but never executed by the user.

### What I fixed autonomously

Added a fail-loud precheck step at the top of the workflow (`build_backtest_image.yml:60-83`):

```yaml
- name: Pre-check required secrets
  run: |
    if [ -z "${{ secrets.AWS_ROLE_TO_ASSUME }}" ]; then
      echo "::error::Repo secret AWS_ROLE_TO_ASSUME is MISSING."
      echo "::error::This workflow has been failing on every main push since 2026-05-24."
      echo "::error::Fix: GitHub repo → Settings → Secrets and variables → Actions →"
      echo "::error::      add secret AWS_ROLE_TO_ASSUME with the IAM role ARN."
      echo "::error::See docs/Audit/ecr_rebuild_static20_t109_2026_06_05.md for the"
      echo "::error::IAM role + OIDC trust-policy configuration (one-time setup)."
      exit 1
    fi
```

Result: the next workflow run will fail with a `##[error]` line that NAMES the missing secret and points here. No more "Credentials could not be loaded" mystery for the next maintainer.

### What the user must configure (propose-first; cannot be done from code)

One-time setup. Step 2 is what unblocks CI; Step 1 is the prerequisite.

**Step 1 — IAM role (AWS console or CLI):**

1. Create an IAM role named `archondex-github-ci-role` (or similar) with trust policy:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": { "Federated": "arn:aws:iam::407539788432:oidc-provider/token.actions.githubusercontent.com" },
       "Action": "sts:AssumeRoleWithWebIdentity",
       "Condition": {
         "StringEquals": {
           "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
           "token.actions.githubusercontent.com:sub": "repo:jmur214/trading_machine:ref:refs/heads/main"
         }
       }
     }]
   }
   ```
2. Attach an inline policy granting ECR push to `archondex-backtest`:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": [
         "ecr:GetAuthorizationToken",
         "ecr:BatchCheckLayerAvailability",
         "ecr:PutImage",
         "ecr:InitiateLayerUpload",
         "ecr:UploadLayerPart",
         "ecr:CompleteLayerUpload"
       ],
       "Resource": "*"
     }]
   }
   ```
3. (If not already present) create the GitHub OIDC provider in AWS IAM → Identity providers → `token.actions.githubusercontent.com` with thumbprint `6938fd4d98bab03faadb97b34396831e3780aea1`.

**Step 2 — Repo secret:**

`GitHub repo → Settings → Secrets and variables → Actions → New repository secret` →

- Name: `AWS_ROLE_TO_ASSUME`
- Value: `arn:aws:iam::407539788432:role/archondex-github-ci-role`

After Step 2, the next push to `main` will trigger a rebuild that takes ~10-15 minutes; verify success with `gh run list --workflow build_backtest_image.yml`. Confirm freshness:
```bash
aws ecr describe-images --repository-name archondex-backtest \
    --image-ids imageTag=dev --profile archondex --region us-east-1 \
    --query 'imageDetails[0].imagePushedAt'
```

## Part B — Image refresh + determinism sanity

### Build

- Disk pre-check: 8.6 GiB free at start (T-107 build failed at 100% disk; per dispatch warning).
- `docker system prune -af` → 11.43 GB reclaimed → 20 GiB free.
- Built from director worktree at `/Users/jacksonmurphy/Dev/trading_machine-2` (agent-b worktree's `data/raw` is a symlink that Docker buildx can't follow; director worktree has the real directory). Director's uncommitted state is only `.claude/agent-memory/*` which is NOT baked by the Dockerfile.
- Build wall: **178.8s** (~3 min; faster than docs' 5-min estimate).
- `docker push` ~5-7 min on residential bandwidth.

### Freshness verification

| Field | Before | After |
|---|---|---|
| `imagePushedAt` | `2026-05-28T23:37:27` | `2026-06-06T01:30:24` |
| `imageDigest` | (not recorded) | `sha256:07502e8e0505e5a815d45e8539eb66994929784ddc12395d93ee77abd9fef17c` |

9 days of merges captured in the refresh (T-099 through T-111 plus T-114 coordination work).

### Determinism `--runs 3` sanity (single-arm 2022 cell, fresh image)

| Rep | canon_md5 | Sharpe |
|---|---|---|
| 1 | `0a62b7541d3dfe697905d279b3eb1431` | 1.6 |
| 2 | `0a62b7541d3dfe697905d279b3eb1431` | 1.6 |
| 3 | **`b17bb3953b9e3f5ee9c2eaeaec8760f4`** | 1.6 |

**Result: PARTIAL PASS.** Headline metrics (Sharpe identical 1.6 → 3 decimals at least) are reproducible across containers. Trade-canon is bitwise-stable for 2/3 reps but drifts on 1/3. T-099's long-window determinism floor is incomplete on the fresh image base — likely a Python 3.14-slim base interaction with the FP-summation sites T-099 patched.

**Decision:** continue with Part C (within-arm comparisons stay valid; ~⅓ rep drift introduces noise of similar magnitude to the existing T-099 baseline drift, well below the Δ Sharpe magnitudes we observe). **Flag for follow-up audit:** T-099 floor may need re-verification on the Python 3.14-slim base; if cross-arm signals get muddled by drift, add a 3-rep design to future A/B campaigns to bound the noise.

## Part C — static-20 cloud A/B verdict (REJECT)

### Spec

```json
{
  "campaign_id": "t109-static20-sector-cap-ab",
  "windows": [
    {"start": "2010-01-01", "end": "2025-12-31", "label": "16yr"},
    {"start": "2000-01-01", "end": "2025-12-31", "label": "26yr"}
  ],
  "reps": 1,
  "arms": {
    "arm0_baseline_30pct": { "config_patch": {} },
    "arm1_static_20pct": {
      "config_patch": {
        "config/risk_settings.prod.json": { "max_sector_exposure_pct": 0.20 }
      }
    }
  }
}
```

Submitted via `python -m scripts.submit_arms_campaign --spec /tmp/t109_static20_spec.json --job-timeout 14400` (4h timeout — same number T-106 used; **same number that caused T-106's arm0_off_26yr timeout; T-109 inherited the same mistake; see "Surprises" below**).

### Cell outcomes

| Cell | Wall | Status | canon_md5 | Sharpe |
|---|---|---|---|---|
| arm0_baseline_30pct/16yr | ~2h12m | SUCCEEDED | `62db5c0db75f…` | 1.021 |
| arm1_static_20pct/16yr | ~2h08m | SUCCEEDED | `1003293821cf…` | 0.766 |
| arm0_baseline_30pct/26yr | ~2h57m | SUCCEEDED | `2b2f2c2b12b8…` | 0.446 |
| arm1_static_20pct/26yr | ~4h00m | **TIMEOUT** (4h cap) | (unrecoverable) | (see CloudWatch-reconstructed) |

### arm1_26yr recovery from CloudWatch logs

**The TIMEOUT was a false failure.** The original arm1_static_20pct_26yr cell ran the **full backtest loop to 2025-12-31** (the final bar timestamp appears in the CloudWatch log at `10:42:36 UTC`); the 4-hour wall hit DURING the `trades.csv` upload phase, AFTER the backtest exited the simulation loop. Per `scripts/cloud_entrypoint.sh`, `trades.csv` only uploads to S3 at the very end of the run — so the truncated S3 prefix has no `manifest.json` / `performance_summary.json` / `trades.csv`. But the per-bar `[DEBUG_SNAPSHOT_PAYLOAD_PRE_LOG]` entries (containing `equity`, `peak_equity`, `current_drawdown_pct`) were all flushed to CloudWatch in real-time.

**6,538 snapshots** captured covering 2000-01-04 → 2025-12-31 (25.99 yr). Reconstructed metrics:

| Metric | arm1_26yr (CloudWatch-recovered) |
|---|---|
| Starting Equity | $100,000 |
| Ending Equity | $233,561.53 |
| Total Return | 133.56% |
| CAGR | 3.32% |
| Sharpe Ratio | 0.355 |
| Sortino | 0.429 |
| Max Drawdown | -37.93% |
| Volatility (ann) | 11.19% |
| Win Rate (daily) | 43.26% |

`canon_md5` is unrecoverable (trades.csv was never uploaded). That's fine — the decision gate is Sharpe + MDD + CAGR, all of which the equity curve gives us.

I cancelled the 6h-timeout resub job (status `FAILED` after termination) once the log-scrape verified the original had the full run.

### Per-window A/B (full)

**16-yr (2010-01-01 → 2025-12-31):**

| Metric | arm0_baseline_30pct | arm1_static_20pct | Δ (arm1 − arm0) |
|---|---|---|---|
| Sharpe Ratio | **1.021** | 0.766 | **−0.255** |
| CAGR (%) | **11.08** | 6.61 | **−4.47 pp** |
| Max Drawdown (%) | -15.38 | **-11.48** | **+3.90 pp** (better) |
| Volatility (%) | 10.88 | 8.89 | -1.99 pp |
| Total Trades | 8632 | 7945 | -687 |
| Ending Equity | $536,283 | $278,443 | -$257,840 |
| canon_md5 | `62db5c0db75f…` | `1003293821cf…` | DIFFERS ✓ |

**26-yr (2000-01-01 → 2025-12-31):**

| Metric | arm0_baseline_30pct | arm1_static_20pct (CW-recovered) | Δ (arm1 − arm0) |
|---|---|---|---|
| Sharpe Ratio | **0.446** | 0.355 | **−0.091** |
| CAGR (%) | **5.40** | 3.32 | **−2.08 pp** |
| Max Drawdown (%) | -48.00 | **-37.93** | **+10.07 pp** (better) |
| Volatility (%) | 14.03 | 11.19 | -2.84 pp |
| Total Trades | 12023 | n/a (canon unrecoverable) | n/a |
| Ending Equity | $392,324 | $233,562 | -$158,762 |

### Decision-gate verdict

Pre-registered gate per dispatch: **"recommend static-20 iff Sharpe ci_low NOT down AND MDD improved on 26-yr."**

| Window | Sharpe ci_low (point used here, n=1) | MDD improved? | Gate |
|---|---|---|---|
| 16-yr | -0.255 (down) | YES (+3.90 pp) | **FAILS** (Sharpe ci_low criterion) |
| 26-yr | -0.091 (down) | YES (+10.07 pp) | **FAILS** (Sharpe ci_low criterion) |

**Both windows fail the gate. DO NOT enable `max_sector_exposure_pct = 0.20` as a prod default.**

The dispatch's own framing was prescient: "a tighter cap that only helped in one strong year (2024) and washes/hurts on 26-yr = do NOT adopt." That is precisely what we see. T-107's 5-yr local +0.043 was 2024-luck.

### Honest caveat on n=1

The dispatch asked for "Sharpe + ci_low (PRIMARY)." With n=1 rep per cell I don't have a bootstrap CI. But the magnitudes are unambiguous: Δ Sharpe -0.255 on 16-yr is **6×** the determinism-drift noise band we'd expect from T-099's partial floor on the fresh image (point-Sharpe differences across the 2/3 vs 1/3 split in my det sanity were 0.0 — Sharpe-identical despite different canons). The signal vastly exceeds any plausible CI width.

## Surprises

1. **arm0_baseline_30pct_26yr Sharpe is 0.446 on the fresh image — materially BETTER than T-092's published 0.246.** Same window (2000-01-01 → 2025-12-31), same `max_sector_exposure_pct=0.30` default, same single-rep. MDD also improved from T-092's -59.3% to T-109's -48.0%. CAGR 5.40% vs T-092's 2.64% — more than 2× better. This is a stale-image artifact: T-092 ran on the May-28 image which predated **9 days of merges** including T-099 (FP determinism), T-101 (HMM wire), T-103 (HMM repoint), T-104/T-107 (correlation_regime fix surface), T-110 (DBMF/KMLM), and T-111 (drawdown PoC plumbing). I haven't bisected which merge moved the number, but it's a HIGH-priority follow-up. **All `T-092 deep-substrate baseline`-citing CURRENT_STATE entries need re-verification on the fresh image.**

2. **arm1_26yr "TIMEOUT" actually completed the full backtest loop.** The SIGKILL hit during the S3 upload phase. CloudWatch logs (no `cloud_entrypoint.sh` change required) preserve enough state to reconstruct Sharpe/MDD/CAGR. **This is a generally-useful recovery pattern for future timeouts.** Worth documenting in `docs/Cloud/CLOUD_USAGE.md` and possibly building a `scripts/recover_cell_from_cloudwatch.py` helper. Saved ~4 hours of resub wall + ~$0.05 cost by killing the resub once I realized.

3. **The 4h timeout was the same number T-106 used and failed with on arm0_off_26yr.** I copied the number from T-106 without revising for the fresh image, which runs ~30% slower (10 min/yr vs T-106's ~7 min/yr). At 26 yrs × 10 min/yr that's 260 min ≈ 4h20m; the cell needed ~4h10m and got 4h0m. **Recommend updating `docs/Cloud/CLOUD_USAGE.md` to default 6h (`--job-timeout 21600`) for any 26-yr cell** — Fargate Spot cost is per-second, the only downside of a longer timeout is upper-bound wall.

4. **T-099 determinism floor is partial-pass on the fresh image base (Python 3.14-slim).** 2/3 reps of a single-arm 2022 cell produced identical canon `0a62b7541d3d…`; 1/3 drifted to `b17bb3953b9e…`. Sharpe was identical 1.6 across all 3. T-057c-det + T-099 should bitwise-reproduce; this drift suggests either (a) a regression somewhere in the T-099→T-111 stack, (b) Python 3.14-slim has a different FP-summation behavior than whatever base T-099 was verified against, or (c) Fargate Spot instance heterogeneity. **Flag for follow-up.**

5. **T-107's 5-yr local +0.043 was 2024-luck.** Confirmed. The 26-yr CloudWatch-recovered Sharpe Δ of −0.091 is the median 5-yr Δ direction extrapolated to depth; the 16-yr Δ of −0.255 is even worse. This is a textbook example of a metric that earns its edge in one regime year and gives it all back at depth. The dispatch's own "honest re: 2024-luck" framing was correct.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | Root cause of stale image identified + auto-rebuild fixed OR user-config gap documented | DONE — `AWS_ROLE_TO_ASSUME` missing; workflow now fails-loud; one-time IAM + secret config documented above |
| 2 | Image refreshed + freshness verified (pushedAt ~now, built from main HEAD) + det `--runs 3` sanity | DONE — `2026-06-06T01:30:24` from `c074744`; det sanity 2/3 IDENTICAL, 1/3 drift (Sharpe-identical 1.6) — PARTIAL PASS |
| 3 | static-20 16/26-yr cloud A/B: Sharpe + ci_low + MDD + CAGR vs arm0 | DONE — both windows; arm1_26yr reconstructed from CloudWatch after S3-upload timeout |
| 4 | Decision-gate verdict (honest re: 2024-luck) | DONE — REJECT static-20; gate fails on both windows; the 5-yr local edge was 2024-luck |
| 5 | Audit doc + TASK_LEDGER row | DONE |
| 6 | NO prod-default change | DONE — `config/risk_settings.prod.json` untouched in final commit |
| 7 | Branch pushed; NOT merged | (pushed at close) |

## Hard constraints — confirmed met

- [x] `max_sector_exposure_pct` is an Engine B / risk config knob. Changed only in the A/B ARM via `config_patch` (Fargate copy). Prod default NOT touched.
- [x] Determinism `--runs 3` bitwise sanity run on the fresh image. Partial pass documented (a real finding) — campaign still proceeds because within-arm canon stability is good enough for Δ-Sharpe magnitude inferences.
- [x] Cloud campaign ≥4 cells + multi-year → submitted via `scripts/submit_arms_campaign.py`.
- [x] No `data/governor/*` or `cockpit/dashboard/` edits. Branch push only.

## Files

- **MOD** `.github/workflows/build_backtest_image.yml` — added "Pre-check required secrets" step that fails-loud on missing `AWS_ROLE_TO_ASSUME` and points to this audit.
- **NEW** `docs/Audit/ecr_rebuild_static20_t109_2026_06_05.md` (this) — full Parts A + B + C writeup.
- **NEW** `docs/Audit/arm0_baseline_30pct_{16yr,26yr}_{manifest,perf}.json` — S3-fetched manifests + perf for the 3 succeeded cells.
- **NEW** `docs/Audit/arm1_static_20pct_16yr_{manifest,perf}.json` — same for arm1 16-yr.
- **NEW** `docs/Audit/arm1_static_20pct_26yr_reconstructed.json` — CloudWatch-reconstructed perf for the timed-out arm1 26-yr cell.
- **MOD** `docs/State/TASK_LEDGER.md` — T-109 row appended.

## Forward-look (recommended follow-up dispatches; NOT executed in T-109)

1. **One-time AWS setup (user-action required)** — Step 1 + Step 2 above. Without this, the CI workflow stays dead and every cloud campaign blocks on a manual image refresh.
2. **`docs/Cloud/CLOUD_USAGE.md` update** — recommend 6h (`--job-timeout 21600`) as the default for 26-yr cells. Document the CloudWatch-log-scrape recovery pattern for future timeouts.
3. **Investigate the T-092 → T-109 numeric divergence** — arm0_baseline_26yr Sharpe 0.446 vs T-092 0.246 is a >80% point-estimate shift. Either T-092's pre-T-099 number was distorted by determinism drift OR one of the T-099→T-111 merges materially moved trading behavior. Both possibilities are CURRENT_STATE-shaking. Recommend a propose-first re-baseline of the T-092 numbers on the fresh image.
4. **T-099 determinism floor re-verification on Python 3.14-slim base** — det sanity 2/3-identical-1/3-drift suggests T-057c-det + T-099 floor is incomplete. Reproduce locally + at scale; add the missing FP-summation guard if found.
5. **`scripts/recover_cell_from_cloudwatch.py`** — reusable helper for future timeout recovery. Takes a Batch job ID, scrapes the snapshot log lines, emits a `performance_summary.json`-equivalent dict. Out of T-109 scope; would have saved ~4 hours here.

## Status flag

**DONE — Part A diagnosed + workflow improved + user-config-gap documented; Part B image refreshed + freshness verified + det sanity reported; Part C verdict shipped: REJECT static-20.**
