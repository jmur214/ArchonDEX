#!/bin/bash
# Nightly janitor wrapper — Phase-6 rung 0 (autonomous development pilot).
# Scheduled via launchd (com.archondex.janitor, 03:00 local daily).
#
# Follows the T-136 archiver pattern deliberately, including its hard-won lesson:
# NEVER a bare `python` — launchd runs with a minimal PATH and a bare interpreter
# name resolves to nothing, which previously surfaced as a misdiagnosed "FRED is
# down" rather than "the wrapper never started" (2026-07-08 fresh-eyes finding #1).
#
# The janitor reports check FAILURES in its own report and ledger rather than
# exiting non-zero for them — a red suite is the janitor doing its job, not the
# janitor breaking. A non-zero rc here means the JANITOR ITSELF could not run,
# which is the only thing worth waking someone for.
set -u
REPO="/Users/jacksonmurphy/Dev/trading_machine-agent-b"
PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || PY="/Users/jacksonmurphy/Dev/trading_machine-2/.venv/bin/python"
LOG_DIR="$REPO/data/logs/janitor"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/janitor_$(date +%Y-%m-%d).log"
SNS_TOPIC="arn:aws:sns:us-east-1:407539788432:archondex-paper-alerts"

{
  echo "=== janitor $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
  cd "$REPO" || exit 1
  # Refresh the base so 'behind origin/main' is meaningful; never merges, never resets.
  git fetch origin --quiet 2>&1 || echo "JANITOR_FETCH_FAILED (continuing; base may be stale)"
  "$PY" scripts/janitor_nightly.py "$@" 2>&1
  RC=$?
  echo "=== janitor rc=$RC ==="
  if [ "$RC" -ne 0 ]; then
    # Loud-failure marker (grep target) + the alarm channels. This fires only when
    # the janitor itself failed — check failures are REPORTED, not alarmed here.
    echo "JANITOR_RUN_FAILED rc=$RC"
    aws sns publish --profile archondex --region us-east-1 \
      --topic-arn "$SNS_TOPIC" \
      --subject "ArchonDEX nightly janitor FAILED (launchd)" \
      --message "run_janitor_nightly.sh $(date '+%Y-%m-%d %H:%M %Z'): rc=$RC. See $LOG" \
      2>&1 || echo "JANITOR_SNS_PUBLISH_FAILED (falling back to local notification)"
    osascript -e "display notification \"nightly janitor FAILED rc=$RC — see log\" with title \"ArchonDEX ALERT\" sound name \"Basso\"" \
      2>&1 || echo "JANITOR_LOCAL_NOTIFY_FAILED"
  fi
} >> "$LOG" 2>&1
