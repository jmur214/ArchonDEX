#!/bin/bash
# Intraday options snapshot wrapper (T-418, 2026-11-24): the second daily capture of the T-416
# options archive, taken while the market is OPEN. Scheduled via launchd
# (com.archondex.options-intraday, 11:30 CT = 12:30 ET, Monday-Friday).
#
# WHY. The first eod file (2026-11-24) showed the XSP closing quote is real but too wide to
# price a trade: near the money the median spread was 18 % of the mid (SPY: 2 %), with a size
# of 1 on a side in 37 % of rows. Midday the XSP market is tight. This capture is the one a
# cost model can use; the 17:30 CT eod capture stays as it is.
#
# WHY 12:30 ET. It is inside the session on EVERY trading day, half-days included (those
# close 13:00 ET), so no early-close branch is needed. Rows carry slot "near_close" (the
# archiver's name for its intraday slot); snap_ts and quote_ts hold the true times.
#
# A LATE FIRING IS A MISS, NOT A FAILURE. launchd runs a missed job when the laptop wakes. If
# that is outside 09:35-12:55 ET the capture is skipped and logged as OPTIONS_INTRADAY_MISSED
# with a local notification only (no email): the archiver would refuse the slot anyway, and
# an email for every afternoon the lid was closed is an alarm that cries wolf. The gap is
# visible in the data: that day's file has no near_close rows.
#
# Inside the window the archiver's exit code is the gate: 0 = OK or a closed day (SKIP),
# 1 = FAILED (no real quotes, or coverage below the floor), 2 = broken, 142 = killed by the
# hard bound. Any non-zero code takes the same alarm branch as the eod wrapper (SNS + local).
set -u
REPO="/Users/jacksonmurphy/Dev/trading_machine-2"
PY="$REPO/.venv/bin/python"
# The aws CLI, resolved ABSOLUTELY (launchd's PATH does not hold /opt/homebrew/bin; see
# run_altdata_archivers.sh for the outage a bare name caused).
AWS="$(command -v aws 2>/dev/null || true)"
if [ ! -x "${AWS:-}" ]; then
  for c in /opt/homebrew/bin/aws /usr/local/bin/aws /usr/bin/aws; do
    [ -x "$c" ] && AWS="$c" && break
  done
fi
AWS="${AWS:-aws}"
OPT_TIMEOUT="${ARCHONDEX_OPTIONS_TIMEOUT_S:-2400}"
case "$OPT_TIMEOUT" in ''|*[!0-9]*|0*) OPT_TIMEOUT=2400 ;; esac
WIN_OPEN=935
WIN_CLOSE=1255
LOG_DIR="$REPO/data/macro_data/alt/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/options_intraday_$(date +%Y-%m-%d).log"
SNS_TOPIC="arn:aws:sns:us-east-1:407539788432:archondex-paper-alerts"

{
  echo "=== options intraday $(date '+%Y-%m-%d %H:%M:%S %Z') aws=$AWS ==="
  cd "$REPO" || exit 1
  # ARCHONDEX_INTRADAY_NOW_ET (HHMM) overrides the clock for tests and drills only.
  NOW_ET="${ARCHONDEX_INTRADAY_NOW_ET:-$(TZ=America/New_York date +%H%M)}"
  NOW_NUM=$((10#$NOW_ET))
  if [ -n "${ARCHONDEX_ALARM_DRILL:-}" ]; then
    echo "ALARM DRILL — forcing the failure branch; archiver NOT run, no data touched"
    RC=99
  elif [ "$NOW_NUM" -lt "$WIN_OPEN" ] || [ "$NOW_NUM" -gt "$WIN_CLOSE" ]; then
    echo "OPTIONS_INTRADAY_MISSED fired at $NOW_ET ET, outside 09:35-12:55 ET; no capture today"
    osascript -e "display notification \"intraday options capture missed (fired $NOW_ET ET)\" with title \"ArchonDEX\"" \
      2>&1 || echo "OPTIONS_INTRADAY_LOCAL_NOTIFY_FAILED"
    echo "=== exit codes: options_intraday=missed ==="
    exit 0
  else
    /usr/bin/perl -e 'alarm shift; exec @ARGV; exit 127' "$OPT_TIMEOUT" \
      "$PY" scripts/archive_options_snapshots.py --slot near_close 2>&1
    RC=$?
  fi
  echo "=== exit codes: options_intraday=$RC ==="
  if [ "$RC" -ne 0 ]; then
    echo "OPTIONS_INTRADAY_FAILED rc=$RC"
    "$AWS" sns publish --profile archondex --region us-east-1 \
      --topic-arn "$SNS_TOPIC" \
      --subject "ArchonDEX intraday options capture FAILED (launchd)" \
      --message "run_options_intraday.sh $(date '+%Y-%m-%d %H:%M %Z'): rc=$RC. See $LOG" \
      2>&1 || echo "OPTIONS_INTRADAY_SNS_PUBLISH_FAILED (falling back to local notification)"
    osascript -e "display notification \"intraday options capture FAILED rc=$RC — see log\" with title \"ArchonDEX ALERT\" sound name \"Basso\"" \
      2>&1 || echo "OPTIONS_INTRADAY_LOCAL_NOTIFY_FAILED"
  fi
} >> "$LOG" 2>&1
