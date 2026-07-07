#!/bin/bash
# Daily alt-data archiver wrapper — Info-Layer program Lane 2.1 Phase A (2026-07-07).
# Runs both idempotent snapshot archivers; scheduled via launchd
# (com.archondex.altdata-archive, 17:30 CT = 18:30 ET daily).
# Phase B (cloud-pulse integration, owner B) will supersede this; run both in
# parallel ~2 weeks before retiring the launchd job.
set -u
REPO="/Users/jacksonmurphy/Dev/trading_machine-2"
PY="$REPO/.venv/bin/python"
LOG_DIR="$REPO/data/macro_data/alt/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/archive_$(date +%Y-%m-%d).log"

{
  echo "=== altdata archivers $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
  cd "$REPO" || exit 1
  "$PY" scripts/archive_altdata_t136.py 2>&1
  RC1=$?
  "$PY" scripts/archive_positioning_t136.py 2>&1
  RC2=$?
  echo "=== exit codes: altdata=$RC1 positioning=$RC2 ==="
  # Loud-failure marker: a monitoring grep (and the director's 3-day check)
  # looks for this token; dedupe would otherwise hide silent API breakage.
  if [ "$RC1" -ne 0 ] || [ "$RC2" -ne 0 ]; then
    echo "ALTDATA_ARCHIVER_FAILED rc1=$RC1 rc2=$RC2"
  fi
} >> "$LOG" 2>&1
