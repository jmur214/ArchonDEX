# Cloud bootstrap — lessons learned from the first real campaigns

**Date:** 2026-05-24
**Context:** First end-to-end production cloud campaigns ran on 2026-05-23 → 2026-05-24 (T-057b, T-055g v1+v2). The AWS Batch infra had shipped 2026-05-09 (e0d9ab3) but had **zero historical jobs** before this cycle. Today's bootstrap hit 5 real gotchas worth recording before they're forgotten.

This doc is operational addendum to [`CLOUD_USAGE.md`](CLOUD_USAGE.md) (how to use it day-to-day) and [`CLOUD_RUNBOOK.md`](CLOUD_RUNBOOK.md) (the original setup sequence).

---

## Gotcha #1 — Architecture mismatch (amd64 vs arm64)

**The bug:** First smoke test FAILED with `CannotPullContainerError: pull image manifest has been retried 7 time(s): image Manifest does not contain descriptor matching platform 'linux/arm64 v8'`.

**Root cause:** I built `--platform=linux/amd64` by assumption. The Batch job definition has `runtimePlatform.cpuArchitecture: ARM64` (Graviton Fargate — cheaper than Intel by ~40%). Image arch didn't match → Batch couldn't pull.

**Fix:** Rebuild with `--platform=linux/arm64`. Mac M-series is arm64 native → faster build (no emulation), and the cross-architecture determinism risk evaporates (host + target same arch).

**Diagnostic time:** ~2 min from FAILED status to root cause via `aws batch describe-jobs ... statusReason`. Fast cycle.

**Permanent fix:** the existing Dockerfile uses unpinned `FROM python:3.14-slim`. If you want defense-in-depth, change to `FROM --platform=linux/arm64 python:3.14-slim` so the platform is baked in (vs. depending on the `docker buildx build --platform` flag).

**Pre-flight check before any build:**
```bash
aws batch describe-job-definitions --profile archondex --region us-east-1 \
  --job-definition-name archondex-backtest --status ACTIVE \
  --query 'jobDefinitions[0].containerProperties.runtimePlatform' --output json
```
Must show `cpuArchitecture: ARM64` (or whatever you intend to build for).

---

## Gotcha #2 — Docker Desktop VM disk fills during iterations

**The bug:** Third rebuild attempt FAILED with `ResourceExhausted: failed to copy files: copy file range failed: no space left on device`.

**Root cause:** Docker Desktop maintains a virtual disk for the daemon. Multiple rebuilds + the buildx cache accumulated 30+ GB. The VM auto-grows but eventually hits a host-disk ceiling.

**Fix:** `docker builder prune -af` reclaimed 15.68 GB of buildx cache. The cycle's intermediate layers are usually safe to drop.

**Diagnostic command:**
```bash
docker system df  # shows Images, Containers, Build Cache sizes
```

**Operational rule:** between any 2 build iterations, prune the cache. The build is fast on cached layers anyway (~60-90 sec for the rebuilt entrypoint vs ~3 min cold).

---

## Gotcha #3 — Verify-first protocol (the T-055g v1 disaster)

**The bug:** Spent $1.50 + 67 min cloud wall on a 75-cell A/B campaign where ALL 5 arms produced near-identical results. Smoking gun: every arm's 2025 Sharpe was exactly 1.717 (matching OFF baseline) — that's not "no signal," that's "patches didn't apply."

**Root cause:** My T-055g v1 spec patched the config with keys like `risk.vol_target.enabled` (3-level dotted path). The actual `RiskConfig` dataclass reads FLAT keys with `portfolio_` prefix: `portfolio_vol_target_enabled`, `portfolio_vol_target_regime_aware`, etc. My patches landed in a `risk.vol_target.X` JSON subsection that no loader ever reads → all arms silently ran with vol-target OFF.

This is the same class as the T-055c env-suffixed-config silent-mismatch bug (memory: `feedback_env_suffixed_config_patches_2026_05_22.md`). Patch happens, but value lands somewhere the loader never reads.

**Fix protocol** — verify-first is now mandatory:

1. Before launching a full A/B campaign (>2 cells), run a 2-cell verify spec:
   - 1 cell OFF (empty patch)
   - 1 cell ON (smallest patch that should change behavior)
2. Check that `canon_md5` differs between OFF and ON cells. If they match → patch didn't apply, fix BEFORE spending money on the full grid.

**Sample verify spec** ([`data/cloud_runs/specs/t055g_verify.json`](../../data/cloud_runs/specs/t055g_verify.json) in this repo):
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

**Time cost of verify:** ~5-7 min wall per cell × 2 cells = ~10-15 min. Cost: ~$0.04. Tiny insurance vs $1-3 lost on a malformed full campaign.

**Key-namespace discipline:** before writing a patch, grep the actual config-load path:
```bash
grep -n "portfolio_vol_target\|<field-name>" engines/engine_<X>/<engine>.py
```
The dataclass field names are the patch keys. NOT the dotted-namespace inferred from "logical structure."

---

## Gotcha #4 — Cross-container determinism not visible locally

**The bug:** 3 of 10 (arm × year) cells in T-057b cloud campaign had 1-rep canon_md5 drift across 5 reps. Same behavior never reproduced under local `run_isolated --runs 5`.

**Root cause** (B's T-057c-determinism diagnosis):
- `signal_processor.process()` weighted_sum aggregation iterates `self.edges.items()` in insertion order
- Cross-container init order varies based on filesystem read order, import resolution timing, container start sequencing
- Aggregating same edge contributions in different orders produces FP residue (0.0 vs 8.8e-18)
- At zero crossings the sign of the residue flips trade direction → different trade → different canon

**Smoking gun:** REGN/2024-03-13 trade meta showed identical edges fired with identical raw scores, but `target_weight = 0.0` in one container vs `target_weight = 8.8e-18` in another → opposite-side trade.

**Bimodal not random:** 3 affected cells split 2/3 reps across two stable equilibria. Not noise — two deterministic outcomes that depend on container init order.

**Why local `--runs N` missed it:** local filesystem happens to return edges alphabetical by coincidence. Single-process multi-run uses the same in-memory `self.edges` for all reps within the process.

**Fix:** 2-line defensive sort in `engines/engine_a_alpha/signal_collector.py` (T-057c-det, commit `02251dc`).

**Permanent rule:** local `--runs N` is NECESSARY but NOT SUFFICIENT for determinism validation. **Cross-container canon comparison is the actual test.** Run any new harness through a 2-cell cloud campaign (OFF vs OFF, both empty patch) and verify canon matches. If not → the harness has cross-container drift.

**Wider audit target:** any other place in the codebase that aggregates over `dict.items()` in insertion order is at-risk. Engine A/C/D are the likely zones. Worth a code-health pass when you have time.

---

## Gotcha #5 — Manifest path mismatch in initial launcher

**The bug:** First successful smoke (smoke #2) showed `run_id=None`, `canon_md5=None`, `sharpe=None` in the summary JSON — even though S3 had the actual files.

**Root cause:** The entrypoint uploads to `s3://<bucket>/<cell_id>/<run_id>/manifest.json` (with a `<run_id>` subdirectory). The launcher's `fetch_manifests()` was looking at `s3://<bucket>/<cell_id>/manifest.json` (no run_id). Path mismatch → fetch silently returned nothing → all manifest fields None.

**Fix:** the launcher now does `aws s3 ls <cell_prefix>/` to discover the run_id subdir, then fetches manifest from `<cell_prefix>/<run_id>/manifest.json`. See [`scripts/submit_arms_campaign.py:fetch_manifests`](../../scripts/submit_arms_campaign.py).

**Operational tip:** if you ever see manifest fields all-None in the summary but S3 has data, the path-discovery probably broke. The S3 paths are authoritative.

---

## Cycle metrics worth remembering

| Stage | Time | Notes |
|---|---|---|
| Build (arm64 native, all layers fresh) | ~85-90 sec | First-ever build |
| Build (entrypoint-only change, layer-cached) | ~60-70 sec | Subsequent rebuild |
| Push to ECR (1.36 GB, all layers fresh) | ~5-7 min | Residential connection |
| Push to ECR (entrypoint-only change) | ~1-2 min | Only changed layers transit |
| Fargate cold start (first cell of campaign) | ~2-3 min | Subsequent cells warm |
| Backtest cell wall (5-yr window, ~600 tickers) | ~5-7 min | Includes S3 upload |
| Backtest cell wall (12-yr window — expected) | ~12-15 min | 2.5x bars × similar overhead |
| Cost per cell (Fargate on-demand, 1 vCPU, 4 GB, 6 min) | ~$0.02 | $1-1.50 for 50-75 cell campaign |

**Practical campaign budgets:**
- 10-cell verify: ~$0.20, ~10 min
- 30-cell 3-rep × 5-year campaign: ~$0.60, ~40 min
- 50-cell 5-rep × 5-year campaign: ~$1.00, ~50 min
- 75-cell 3-rep × 5-year × 5-arm campaign: ~$1.50, ~60-70 min
- 150-cell substrate measurement: ~$3.00, ~90 min

All numbers are arm64 (Graviton). Intel Fargate would be ~40% more.

---

## Order-of-operations checklist for any future cloud campaign

1. [ ] `aws sts get-caller-identity --profile archondex` succeeds
2. [ ] `docker info` shows daemon up (start Docker Desktop manually if not)
3. [ ] `aws batch describe-job-definitions ... cpuArchitecture` confirms target arch
4. [ ] `docker system df` shows < 5 GB build cache (else `docker builder prune -af`)
5. [ ] grep target config file for actual field names; patch spec uses THOSE keys
6. [ ] Rebuild image with correct `--platform=linux/arm64`
7. [ ] Push to ECR (~5 min)
8. [ ] Run verify spec (2 cells: OFF + ON-with-minimal-patch); confirm canon differs
9. [ ] Launch full campaign
10. [ ] Pull manifests via launcher; spot-check 1-2 cells' Sharpes match expectation
11. [ ] If new harness, also run a 2-cell OFF-vs-OFF empty-patch cross-container canon-match check (would catch cross-container drift)

Steps 4, 5, and 8 would have caught the three campaign-killing bugs I hit today. Cheap insurance.

---

## What's still unsolved / open

- **CI auto-rebuild** (`.github/workflows/build_backtest_image.yml`) waits on user setting `AWS_ROLE_TO_ASSUME` GitHub secret. Until then, image stays at whatever was manually pushed.
- **The `submit_substrate_run.py` legacy launcher** still has the original hardcoded substrate-measurement shape. `submit_arms_campaign.py` (T-085) is its general-case replacement. Worth consolidating after 1-2 more campaigns prove the generic launcher is sufficient.
- **Multi-year window support** in launcher (Part A of T-053b, A is working on this now) — once landed, all future campaigns can use 11+ yr windows without bespoke harness scripts.
- **Wider code-health audit for dict-iteration-order in aggregations.** Engine A/C/D likely have other instances of the T-057c-det root cause class.
