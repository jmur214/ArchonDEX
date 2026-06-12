# T-2026-06-11-155 — Earnings-dates pin + deferred image bundle (+ the anchor handoff)

**Date:** 2026-06-11 | **Branch:** `feature/earnings-pin-bundle-t155` | **Worker:** Agent B
**Status:** Parts 1-2-4 DONE + verified; Part 3 (cloud rebuild + 9 anchor cells) BLOCKED on host disk — exact handoff below.

## TL;DR
1. **Earnings pin (the T-142 fix): DONE + the best-case verify.** One-time sanctioned fetch over the canonical 109-ticker universe → `data/earnings/earnings_dates_pinned.parquet` (2,668 rows, **107/109 tickers**; SPY/QQQ = ETFs with no earnings calendar — identical semantics to the live fetch's empty result). `earnings_vol_edge` repointed: parquet is primary for local AND cloud (zero network); ticker-absent = pinned no-data; legacy network path only if the parquet is missing entirely. Refresh procedure = `scripts/pin_earnings_dates.py` + manifest regen + commit (anchor-update pattern, documented in-script).
2. **VERIFY (strict hermetic, full local 2022 cell): exit 0, ZERO blocked calls, canon `0145c03a6496…` / Sharpe 0.464 — BITWISE IDENTICAL to the historical local OFF-canon.** The pin reproduces exactly the dates the live fetches returned → **canon continuity, not a re-baseline**: T-142's local-contamination finding is closed at the data layer with the established reference INTACT. (T-142's blocked-mode canon `f47b63b2…` was the no-data regime; the pin restores the data.) Cloud canons should now CONVERGE toward the local family (cloud previously timed out = no data) — the 9 anchor cells settle that empirically.
3. **Bundle: DONE.** `requirements.lock.txt` += hypothesis==6.155.2, openpyxl==3.1.5, xlrd==2.0.2 (user-approved); `data/processed/SP500TR_1d_pinned.parquet` (6,902 rows, 1999-01-04→2026-06-11, source yfinance `^SP500TR` auto_adjust=False, vintage-stamped); disk pre-flight in `build_backtest_image.sh` (12GB local / 6GB registry-direct, fail-loud exit 75); **manifest regenerated in-commit: 14,083 files, md5 `07dd0d9e4fd58ee88c2db90195bb78f6`**.
4. **`:dev` retired** in CLOUD_USAGE.md — sha-tags + env-pinned job def only; registry-direct build documented as preferred.

## Part 3 handoff (BLOCKED: host at ~1.2 GiB free — Docker Desktop VM file needs a reclaim)
After disk reclaim, on this branch (or post-merge main):
```bash
ARCHONDEX_BUILD_PUSH=1 bash scripts/build_backtest_image.sh HEAD \
  407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:sha-<short>
# register env-pinned job def on that sha tag (T-140 pattern), then 9 cells:
#   2022 canary x3, 16yr x3, 26yr x3 (timeouts 3600/14400/21600)
#   via submit_arms_campaign (canary rides along; reps via --reps 3)
# UNANIMITY expected by construction (threads pinned + zero network).
# ANY split = STOP, new finding. Publish canon+Sharpe per window = THE anchors.
```
Expectation to pre-register: 2022 cloud canon should now equal local `0145c03a…` if the historical local↔cloud divergence was the yfinance-outcome difference (T-142 hypothesis) — if it does, that mystery closes too.

## Acceptance
| Criterion | Status |
|---|---|
| Parquet full-coverage + repoint + full local hermetic cell, no misses | DONE — strict mode, 0 misses, canon bitwise-preserved |
| Bundle (lock + ^SP500TR + pre-flight + manifest) one commit | DONE |
| Rebuild + N=3 anchors unanimous | BLOCKED on disk — handoff above |
| :dev retired; docs | DONE |
| Audit + row in outbox | DONE |

## Files
NEW `scripts/pin_earnings_dates.py`, `data/earnings/earnings_dates_pinned.parquet`, `data/processed/SP500TR_1d_pinned.parquet` (data: manifest-pinned, not git), this audit. MOD `engines/engine_a_alpha/edges/earnings_vol_edge.py` (parquet-primary), `requirements.lock.txt`, `scripts/build_backtest_image.sh` (pre-flight), `config/substrate_manifest.sha256` (07dd0d9e), `docs/Cloud/CLOUD_USAGE.md` (:dev retired).

---

# Part 3 — COMPLETED (2026-06-12): THE ANCHORS (9/9 cells, every window 3/3 bitwise-unanimous)

## THE PUBLISHED RELAUNCH ANCHORS (image `sha-5323a3c`, arm64, hermetic, substrate `553edca7…`, job def `archondex-backtest-t155-anchor:3`)

| Window | canon_md5 | Sharpe | Unanimity | Wall/cell | Continuity |
|---|---|---|---|---|---|
| 2022 | `0a62b7541d3dfe697905d279b3eb1431` | 1.6 | **3/3** | ~5.8-6.2 min (~25% faster than historic ~8) | ≡ historical cloud 2022 canon |
| 16-yr | `62db5c0db75f4d6c148a7e53d472cb1e` | 1.021 | **3/3** | ~1.9 h | ≡ T-109's 16-yr — **the T-128 lottery is RESOLVED: with thread-pins, 1.021/`62db5c0d` is THE deterministic 16-yr**; T-125's 0.945/`9153ff15` and T-134's banked native-16 were the other attractor |
| 26-yr | `529e55204a92462337169fb0b3f3a4fd` | 0.237 | **3/3** | ~3.8 h | **≡ T-127's clean baseline bitwise** — canon continuity across earnings-pin + hermetic + arm64-pinned build |

**Unanimity by construction confirmed** — zero splits across 9 tasks. The relaunches fire on these anchors.

## Findings of record

1. **Local↔cloud divergence hypothesis REFUTED:** with byte-identical pinned earnings data, identical substrate, same arch (arm64 both sides) and hermetic on, cloud 2022 = `0a62b754…` while local = `0145c03a…` — the split persists, so the mechanism is platform-level FP (macOS Accelerate vs Linux OpenBLAS), NOT data. **Cloud is the measurement substrate of record**; local canons are a parallel (internally-consistent) family.
2. **Canon continuity everywhere:** the earnings pin + hermetic mode + the CI-built arm64 image changed NO window's canon vs its best prior clean reference (2022 ≡ historic, 16-yr ≡ T-109, 26-yr ≡ T-127). T-142's feared re-baseline did not materialize — the cloud cells' yfinance calls were evidently returning nothing usable all along.
3. **Hermetic wall-time, honest:** ~25% on 1-yr cells; negligible at 26-yr (the ~42 memoized earnings calls are fixed overhead — the "52% of wall" T-134 profile was a 1-yr-cell phenomenon and does not extrapolate to depth).
4. **THE FLEET IS ARM64** (discovery): Batch job defs pin `runtimePlatform cpuArchitecture=ARM64`; every historical image was an Apple-Silicon-native build. CI images must be arm64 (QEMU cross-build, now the workflow default).

## CI build path — the durable outcome (fix chain, one-time costs all paid)

OIDC trust repo-rename + ref-pin (`repo:jmur214/ArchonDEX:*`, StringLike) → role S3 read (`s3:GetObject/ListBucket` on the results bucket) → `--provenance=false --sbom=false` (attestation manifests broke Fargate: "exec format error") → `--platform linux/arm64` + QEMU → `timeout-minutes: 60` (QEMU pip > 20 min) → ref-scoped concurrency group (main pushes were cancelling branch dispatches). **Residual cosmetic gap:** the role lacks `ecr:BatchGetImage`, so the SECOND tag push fails after the first succeeds — one-line IAM addendum recommended. Local Docker remains corrupted (buildkit `metadata_v2.db`) — CI is now the canonical build path, making the local daemon non-critical.
