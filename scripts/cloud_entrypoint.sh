#!/usr/bin/env bash
# scripts/cloud_entrypoint.sh
#
# Container entrypoint for AWS Batch / Fargate runs.
#
# Wraps `python -m scripts.run_isolated --runs 1` so trade logs +
# performance_summary land in S3 instead of ephemeral container disk.
#
# Why a wrapper script: Fargate task disk is gone the moment the container
# exits, so the harness's local `data/trade_logs/<run_id>/` files are lost
# unless we explicitly upload them. This script does the upload.
#
# Required environment (set by the Batch job definition or submit-time):
#   ARCHONDEX_RESULTS_BUCKET — e.g., archondex-results-407539788432
#   ARCHONDEX_CELL_ID        — director-supplied cell identifier (rep × arm)
#                              used as the S3 prefix; falls back to the
#                              run-uuid if unset.
#
# Stdout pattern (so the parent launcher can parse):
#   CANON_MD5=<hex32>
#   CELL_ID=<id>
#   S3_PREFIX=<s3://...>

set -euo pipefail

# T-2026-06-10-140 — Vector B fix (cross-task LAPACK nondeterminism).
# Multi-threaded OpenBLAS/LAPACK reductions partition work by runtime
# conditions, changing FP summation order per task: probe evidence =
# eigh md5 5-vs-1 split unpinned vs 6/6 unanimous with these pins
# (T-128 forensics, docs/Audit/spot_sleeve_closeout_t128_2026_06_10.md).
# The MVO path (scipy.optimize over w·Σ·w) hits this op class every
# solver iteration; ±0.21 Sharpe swing at 26-yr. Belt + suspenders:
# these exports cover ad-hoc job defs; the registered job definitions
# carry the same env (set at job-def registration).
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_DYNAMIC=FALSE

# T-2026-06-17-194 (D's T-189): a cloud/anchor run IS a canonical measurement →
# fail-closed at the data-load source. With this set, a missing load-bearing input
# for an ACTIVE consumer (simfin panel for value edges; membership panel for a
# historical-universe run) HALTs at the loader (exit non-zero) instead of silently
# publishing a degraded number (the T-175 simfin-blind 0.751 / T-167 truncated
# universe). Local/paper/test runs do NOT set this → graceful degradation preserved.
export ARCHONDEX_MEASURED=1

if [ -z "${ARCHONDEX_RESULTS_BUCKET:-}" ]; then
    echo "ERROR: ARCHONDEX_RESULTS_BUCKET not set" >&2
    exit 64
fi

# T-085: per-cell config patch (optional).
# If ARCHONDEX_CONFIG_PATCH_B64 is set, decode and apply it BEFORE the
# harness runs. The patch is a JSON object mapping config-file paths to
# dotted-key updates:
#
#   {
#     "config/risk_settings.prod.json": {
#       "vol_target.enabled": true,
#       "vol_target.regime_aware": true,
#       "vol_target.cautious_target_multiplier": 0.90
#     },
#     "config/alpha_settings.json": {
#       "confidence_gate.enabled": true,
#       "confidence_gate.n_threshold": 3
#     }
#   }
#
# Dotted keys auto-create nested dicts. Existing values are overwritten.
# Lets the campaign launcher per-cell A/B without rebuilding the image.
if [ -n "${ARCHONDEX_CONFIG_PATCH_B64:-}" ]; then
    PATCH_FILE=/tmp/cell_config_patch.json
    echo "$ARCHONDEX_CONFIG_PATCH_B64" | base64 -d > "$PATCH_FILE" || {
        echo "ERROR: failed to base64-decode ARCHONDEX_CONFIG_PATCH_B64" >&2
        exit 67
    }
    echo "[entrypoint] Applying config patch:"
    cat "$PATCH_FILE"
    python - "$PATCH_FILE" <<'PYAPPLY' || exit 68
import json
import sys
from pathlib import Path

patch = json.loads(Path(sys.argv[1]).read_text())
for cfg_path, updates in patch.items():
    p = Path(cfg_path)
    if not p.exists():
        print(f"[entrypoint] WARN: {cfg_path} does not exist; creating", file=sys.stderr)
        cfg = {}
    else:
        cfg = json.loads(p.read_text())
    for dotted_key, value in updates.items():
        keys = dotted_key.split(".")
        target = cfg
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2))
    print(f"[entrypoint] Patched {cfg_path}")
PYAPPLY
fi

# Run the harness and capture its stdout (canon md5 lives there).
# `tee` so the same lines also stream to CloudWatch.
HARNESS_LOG=/tmp/harness.log
# T-053b: window args — precedence matches scripts/run_isolated.py:
# --start-date/--end-date > --year > default 2025.
# When ARCHONDEX_START_DATE + ARCHONDEX_END_DATE are both set, they
# override ARCHONDEX_YEAR. Backward-compat: existing year-based
# campaigns keep working unchanged.
WINDOW_ARG=""
if [ -n "${ARCHONDEX_START_DATE:-}" ] && [ -n "${ARCHONDEX_END_DATE:-}" ]; then
    WINDOW_ARG="--start-date ${ARCHONDEX_START_DATE} --end-date ${ARCHONDEX_END_DATE}"
elif [ -n "${ARCHONDEX_START_DATE:-}" ] || [ -n "${ARCHONDEX_END_DATE:-}" ]; then
    echo "ERROR: ARCHONDEX_START_DATE and ARCHONDEX_END_DATE must both be set when either is" >&2
    exit 69
elif [ -n "${ARCHONDEX_YEAR:-}" ]; then
    WINDOW_ARG="--year ${ARCHONDEX_YEAR}"
fi
# T-2026-06-24-215: the harness runs its OWN census gate and exits non-zero on a
# NON-CANONICAL run. Under `set -euo pipefail` (line 24), that `exit` propagated
# through the `| tee` pipeline and aborted THIS script HERE — BEFORE the
# forensics-upload below — so census-FAILED cells uploaded NOTHING (equity lost;
# the verdict-blocking bug that cost a 30h re-run). The entrypoint's own census
# gate (further down) is the SINGLE source of the cell's canonical verdict + exit
# code; the harness exit must NOT short-circuit the upload. Isolate it from
# pipefail and capture it via PIPESTATUS so the script ALWAYS reaches the upload.
set +e
python -m scripts.run_isolated --runs 1 --task q1 $WINDOW_ARG 2>&1 | tee "$HARNESS_LOG"
HARNESS_RC=${PIPESTATUS[0]}
set -e
if [ "${HARNESS_RC:-0}" -ne 0 ]; then
    echo "[entrypoint] harness exited rc=$HARNESS_RC (often a census-fail) — continuing to upload artifacts for forensics; the entrypoint census gate below sets the canonical verdict + final exit." >&2
fi

CANON_MD5=$(grep -E "trades_canon_md5:" "$HARNESS_LOG" | awk '{print $NF}' | tr -d '[:space:]')
RUN_ID=$(grep -E "^\s+run_id:" "$HARNESS_LOG" | awk '{print $NF}' | tr -d '[:space:]')
SHARPE=$(grep -E "^\s+Sharpe:" "$HARNESS_LOG" | awk '{print $NF}' | tr -d '[:space:]')
CELL_ID="${ARCHONDEX_CELL_ID:-$RUN_ID}"

if [ -z "$RUN_ID" ] || [ "$RUN_ID" = "?" ]; then
    echo "ERROR: harness did not produce a run_id; nothing to upload" >&2
    exit 65
fi

S3_PREFIX="s3://${ARCHONDEX_RESULTS_BUCKET}/${CELL_ID}/${RUN_ID}"

# Upload everything in the run dir
RUN_DIR="/app/data/trade_logs/${RUN_ID}"
if [ ! -d "$RUN_DIR" ]; then
    echo "ERROR: run dir $RUN_DIR not found" >&2
    exit 66
fi

# T-181 execution-census gate — the SAME assert_census the local paths call
# (run_isolated PASS-gate, run_substrate_arms smoke gate), so cloud and local
# cannot diverge on the canonical/non-canonical verdict. A NON-CANONICAL run
# still uploads its artifacts (for forensics) but the cell exits non-zero and
# is marked non-canonical so the launcher never certifies/counts it.
PERF_JSON="${RUN_DIR}/performance_summary.json"
CENSUS_RC=0
python -m core.census "$PERF_JSON" || CENSUS_RC=$?
if [ "$CENSUS_RC" -eq 0 ]; then
    CENSUS_CANONICAL=true
else
    CENSUS_CANONICAL=false
    echo "[entrypoint] CENSUS NON-CANONICAL (rc=$CENSUS_RC) — uploading artifacts for forensics, marking cell non-canonical." >&2
fi

aws s3 cp --recursive --no-progress "$RUN_DIR" "$S3_PREFIX/" \
    --metadata "canon-md5=${CANON_MD5},sharpe=${SHARPE},cell-id=${CELL_ID},census-canonical=${CENSUS_CANONICAL}"

# Also upload a small manifest summarizing the run for the launcher
MANIFEST=/tmp/manifest.json
cat > "$MANIFEST" <<EOF
{
  "run_id":         "$RUN_ID",
  "cell_id":        "$CELL_ID",
  "canon_md5":      "$CANON_MD5",
  "sharpe":         "$SHARPE",
  "s3_prefix":      "$S3_PREFIX",
  "census_canonical": $CENSUS_CANONICAL,
  "census_rc":      $CENSUS_RC,
  "completed_at":   "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
aws s3 cp --no-progress "$MANIFEST" "$S3_PREFIX/manifest.json"

# Stdout markers the parent launcher parses
echo "CANON_MD5=$CANON_MD5"
echo "CELL_ID=$CELL_ID"
echo "S3_PREFIX=$S3_PREFIX"
echo "SHARPE=$SHARPE"
echo "CENSUS_CANONICAL=$CENSUS_CANONICAL"

# Fail the cell (after artifacts are safely uploaded) if non-canonical, so the
# launcher's exit-code check never certifies a clouded number.
if [ "$CENSUS_CANONICAL" != "true" ]; then
    echo "ERROR: run is NON-CANONICAL per execution census (rc=$CENSUS_RC); do not certify this cell" >&2
    exit 70
fi
