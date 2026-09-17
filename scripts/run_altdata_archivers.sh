#!/bin/bash
# Daily alt-data archiver wrapper — Info-Layer program Lane 2.1 Phase A (2026-07-07).
# Runs both idempotent snapshot archivers; scheduled via launchd
# (com.archondex.altdata-archive, 17:30 CT = 18:30 ET daily).
#
# HARDENED 2026-07-08 (fresh-eyes finding #1): the archiver scripts return 0
# unconditionally and report failures as strings, so exit codes alone can
# never catch silent capture loss. After both runs, verify_altdata_snapshot.py
# checks that TODAY's snap_date rows actually landed in the 24/7 snapshot
# parquets; any failure (archiver rc, zero fresh rows, or verifier error)
# publishes to the existing archondex-paper-alerts SNS topic (email).
#
# This launchd path is PERMANENT (plan amended): it is the canonical ~EOD
# (18:30 ET) local snapshot; the cloud pulse's 09:45 ET capture (T-290
# Phase B) is a separate pre-open series on S3 — different time-of-day by
# design, so neither is retired into the other (fresh-eyes finding #3).
set -u
REPO="/Users/jacksonmurphy/Dev/trading_machine-2"
PY="$REPO/.venv/bin/python"
# The aws CLI, resolved ABSOLUTELY. launchd's PATH is /usr/bin:/bin:/usr/sbin:/sbin
# and the CLI lives in /opt/homebrew/bin, so the bare `aws sns publish` below
# resolved to NOTHING at 18:30 while working perfectly from an interactive shell.
# This is the SNS channel meant to catch silent capture loss: it fires only when an
# archiver fails, so it had never been exercised on the scheduled path — the alarm
# was dead for as long as it has existed and nothing could have revealed that except
# an actual failure, which is the worst possible moment to discover it.
AWS="$(command -v aws 2>/dev/null || true)"
if [ ! -x "${AWS:-}" ]; then
  for c in /opt/homebrew/bin/aws /usr/local/bin/aws /usr/bin/aws; do
    [ -x "$c" ] && AWS="$c" && break
  done
fi
AWS="${AWS:-aws}"
LOG_DIR="$REPO/data/macro_data/alt/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/archive_$(date +%Y-%m-%d).log"
SNS_TOPIC="arn:aws:sns:us-east-1:407539788432:archondex-paper-alerts"

{
  echo "=== altdata archivers $(date '+%Y-%m-%d %H:%M:%S %Z') aws=$AWS ==="
  cd "$REPO" || exit 1

  # ALARM DRILL (ARCHONDEX_ALARM_DRILL=1): take the failure branch WITHOUT running
  # the archivers or touching any data. Built in permanently and deliberately: the
  # reason this channel was dead for months is that exercising it required a real
  # failure, so nobody ever did. "The drill is the verification" only works if a
  # drill is possible on an ordinary Tuesday.
  if [ -n "${ARCHONDEX_ALARM_DRILL:-}" ]; then
    echo "ALARM DRILL — forcing the failure branch; archivers NOT run, no data touched"
    RC1=99; RC2=99; RC3=99
  else
  "$PY" scripts/archive_altdata_t136.py 2>&1
  RC1=$?
  "$PY" scripts/archive_positioning_t136.py 2>&1
  RC2=$?
  "$PY" scripts/verify_altdata_snapshot.py 2>&1
  RC3=$?
  fi
  echo "=== exit codes: altdata=$RC1 positioning=$RC2 verify=$RC3 ==="
  if [ "$RC1" -ne 0 ] || [ "$RC2" -ne 0 ] || [ "$RC3" -ne 0 ]; then
    # Loud-failure marker (grep target) + the alarm channels: SNS email
    # (needs sns:Publish on the topic for user claude-code-cli — pending the
    # user's IAM grant as of 2026-07-08), with a local macOS notification as
    # the always-available fallback.
    echo "ALTDATA_ARCHIVER_FAILED rc1=$RC1 rc2=$RC2 verify=$RC3"
    "$AWS" sns publish --profile archondex --region us-east-1 \
      --topic-arn "$SNS_TOPIC" \
      --subject "ArchonDEX altdata archiver FAILED (launchd)" \
      --message "run_altdata_archivers.sh $(date '+%Y-%m-%d %H:%M %Z'): rc1=$RC1 rc2=$RC2 verify=$RC3. See $LOG" \
      2>&1 || echo "ALTDATA_SNS_PUBLISH_FAILED (falling back to local notification)"
    osascript -e "display notification \"altdata archiver FAILED rc1=$RC1 rc2=$RC2 verify=$RC3 — see log\" with title \"ArchonDEX ALERT\" sound name \"Basso\"" \
      2>&1 || echo "ALTDATA_LOCAL_NOTIFY_FAILED"
  fi
} >> "$LOG" 2>&1
