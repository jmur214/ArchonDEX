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
YEAR_ARG=""
if [ -n "${ARCHONDEX_YEAR:-}" ]; then
    YEAR_ARG="--year ${ARCHONDEX_YEAR}"
fi
python -m scripts.run_isolated --runs 1 --task q1 $YEAR_ARG 2>&1 | tee "$HARNESS_LOG"

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

aws s3 cp --recursive --no-progress "$RUN_DIR" "$S3_PREFIX/" \
    --metadata "canon-md5=${CANON_MD5},sharpe=${SHARPE},cell-id=${CELL_ID}"

# Also upload a small manifest summarizing the run for the launcher
MANIFEST=/tmp/manifest.json
cat > "$MANIFEST" <<EOF
{
  "run_id":         "$RUN_ID",
  "cell_id":        "$CELL_ID",
  "canon_md5":      "$CANON_MD5",
  "sharpe":         "$SHARPE",
  "s3_prefix":      "$S3_PREFIX",
  "completed_at":   "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
aws s3 cp --no-progress "$MANIFEST" "$S3_PREFIX/manifest.json"

# Stdout markers the parent launcher parses
echo "CANON_MD5=$CANON_MD5"
echo "CELL_ID=$CELL_ID"
echo "S3_PREFIX=$S3_PREFIX"
echo "SHARPE=$SHARPE"
