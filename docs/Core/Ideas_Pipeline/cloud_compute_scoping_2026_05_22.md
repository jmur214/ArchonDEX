# Cloud-compute scoping — minimum viable migration of long backtest sweeps

> **⚠️ SUPERSEDED 2026-05-22 (same day).** This doc was written without searching the repo for existing cloud infrastructure. AWS-Batch parallel infra had already been built and verified in commit `e0d9ab3` (2026-05-09): `Dockerfile.backtest`, `requirements.lock.txt`, `scripts/submit_substrate_run.py`, `scripts/cloud_entrypoint.sh`, `docs/Cloud/CLOUD_RUNBOOK.md`, AWS account `407539788432`, IAM user `claude-code-cli`, S3 buckets, Batch queue `archondex-backtest-queue`. The recommendation below to spike GitHub Actions was actively wrong — we already chose AWS Batch and built it.
>
> **What's actually needed now:** validate that the existing infra still works end-to-end in a real campaign (Phase 1-6 was unit-spike-verified, never run for a full substrate measurement — zero historical jobs in the Batch queue). The next A/B campaign is the natural validation. The right next doc is a *"first-cloud-campaign runbook"*, not a clean-slate scoping.
>
> **Discipline failure logged:** `feedback_search_existing_infra_before_scoping_2026_05_22.md` in memory.

---

**Status:** SCOPING. Not a build plan; a "what would it take" so we can decide whether to invest before the next long-running sweep.
**Date:** 2026-05-22
**Trigger:** Agent A's current chain (T-041c-archive → T-053 → T-057) projects to ~12 hours on the user's MacBook. T-055c required 30 backtests × ~15 min each. Multi-hour-on-laptop is the current dominant cost; cloud parallelism would collapse it to wall-time-of-longest-run.

---

## Problem

Multi-hour backtest sweeps currently run on the user's MacBook inside an Agent worktree. While they run:

- The MacBook is loaded; A and B compete for cores with the director and with each other.
- The director can't kick off a parity-check (e.g., `scripts/run_isolated.py --runs 3` for a hot-path refactor) without slowing the in-flight agent.
- Real wall-clock for a 30-backtest sweep is ~15-min × 30 = 7.5 hours sequential. Multi-year × multi-rep × multi-arm campaigns compound.
- Sleep / coffee breaks for the laptop are blocking events.

Cloud-compute would let each backtest run in its own container, in parallel, on rented CPUs. A 30-backtest sweep that takes 7.5 hours locally could finish in ~15 minutes if 30 workers fired in parallel.

## What "minimum viable" actually means

The smallest thing that unblocks the next long sweep, NOT a full ML/Ops platform. Three pieces:

### 1. Containerize the backtest harness

- **What:** A Dockerfile that pins `python:3.11-slim` + project's `requirements.txt` + the repo + an entrypoint that runs one backtest (`python -m scripts.run_backtest --year 2024 --rep 1 --arm 1`).
- **Why:** No-Docker cloud workflows mean re-installing Python + 30 packages on every worker — wasted wall-time and a fragility surface.
- **Effort:** ~2 hr. Roughly 30-line Dockerfile + a `.dockerignore` excluding `data/trade_logs/`, `data/research/`, `.git/`, `.claude/`.
- **Risk:** Low. Container only runs read-mostly scripts; doesn't touch broker credentials.

### 2. Object-storage sync for trade logs

- **What:** S3 (or equivalent) bucket where workers upload `data/trade_logs/<run_id>/` after each backtest. Director's `scripts/metrics_report.py` (T-069) already handles per-run-id input — just point it at downloaded artifacts.
- **Why:** Workers are ephemeral; if their outputs don't sync to durable storage immediately, they're lost on container exit.
- **Effort:** ~3 hr. `boto3` client + a 50-line "post-run upload" hook in the existing `scripts/run_backtest.py` (guarded by `--sync-to s3://bucket/path` flag so local runs are unaffected).
- **Risk:** Low. S3 bucket policy = write-only for workers, read-only for director. No production secret exposure.

### 3. Dispatcher (the actual orchestrator)

This is the design decision with the biggest tradeoff range.

- **Option A — AWS Batch (managed):** Submit job array, AWS handles container scheduling. ~2 hr to wire. Cost: $0 dispatch + per-vCPU-hour rates ($0.04ish on m6i). For a 30-backtest sweep at ~15 min × 30 ≈ 7.5 vCPU-hours = ~$0.30. Multi-hour campaigns: maybe $5-10/sweep.
- **Option B — GitHub Actions matrix:** `strategy.matrix` over (year × rep × arm). Zero infra to provision; runs on GitHub's free-tier minutes (2,000 free/mo for private repos). Pure: yes; cheap: yes; fast: per-job startup ~30s vs Batch's ~5s. Best for ≤20 parallel jobs (GitHub's concurrency limit for free tier).
- **Option C — Self-hosted runner on a single rented box:** Hetzner CPX31 (€11/mo, 4 cores), `make run-parallel`. No cloud-native dispatcher but cheaper than Batch for sustained use. Single point of failure.

**Recommendation:** GitHub Actions matrix (Option B) for the first sweep. Free; we already have a GitHub repo; no AWS account / IAM to set up. Migrate to AWS Batch only if GitHub's 20-job concurrency limit becomes the bottleneck OR if a sweep exceeds the 6-hour-per-job limit.

## Tradeoffs

| Dimension | Local MacBook (status quo) | Cloud (proposed) |
|---|---|---|
| Wall-time for 30-backtest sweep | ~7.5 hr (sequential) | ~15-30 min (parallel) |
| Director CPU contention | High | None |
| Setup cost (one-time) | $0 | ~7 hr engineering + GitHub config |
| Per-sweep cost | $0 (laptop electricity) | $0 (GitHub free tier) or ~$0.30-1 (AWS) |
| Determinism guarantee | Strong (same machine, same seed) | Equivalent IF container is pinned + workers use same seed scheme |
| Trade-log retention | Local data/trade_logs/ | S3 with lifecycle policy (keep 90 days, archive to Glacier) |
| Debugging story | Live laptop, fast iteration | Pull container logs, slower iteration |
| Failure modes | One run dies → manual restart | One run dies → re-fire single matrix job |

## What this does NOT include (deferred)

- ML training. Same infra works but model artifacts add cost + governance.
- Live trading. NEVER move broker credentials to cloud workers in this scope.
- Real-time dashboards. Cockpit stays local-only.
- Cross-region replication. Single region is enough.

## Honest unknowns

- **Cold-start latency on GitHub Actions.** ~30s per job startup × 30 jobs ≈ 15 min overhead. Means a "fast" sweep is 30 min, not 15.
- **Container build cache.** First-ever build is ~5 min (apt-get + pip install). With GitHub's layer cache and a stable requirements.txt, subsequent runs are ~30 sec. Need to verify.
- **Determinism across architectures.** Local Mac M-series ARM vs GitHub linux/amd64 may produce micro-differences in numpy/scipy operations. T-061/T-065 tolerance pattern probably absorbs this, but the cockpit `canon_md5` is a much tighter equality check; we'd need to verify that's stable across architectures (or relax to a per-architecture canon).

## Decision point for the user

Three forks:

1. **Defer.** Stay on local. Next sweep takes another 7-12 hours. Cost: $0 infra, $0 time.
2. **Spike GitHub Actions only.** ~5 hr to wire (Dockerfile + .github/workflows/sweep.yml + the upload-artifact hook for trade logs). No S3, no AWS. Validates the basic shape before deeper investment.
3. **Spike the full stack (Docker + S3 + AWS Batch).** ~7-10 hr. Future-proof for multi-day sweeps and the eventual moonshot statistical scans (post-Path-1 timeline).

My read: **(2) is the right next swing.** Smallest investment, fastest validation, and the result is reusable as a building block for (3) if needed. Concrete artifact would be `.github/workflows/sweep.yml` + a `Dockerfile` + a one-line update to `scripts/run_backtest.py` for the artifact upload.

If (2) gets approved, the spike is itself a single dispatchable task for an agent — wouldn't compete with A or B's in-flight work.
