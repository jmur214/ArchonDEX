#!/bin/bash
# Director-pass wrapper — Phase-6 rung 0, second half.
# Scheduled via launchd (com.archondex.director-pass, 07:00 local daily).
#
# Shares the janitor's DEDICATED RUNNER WORKTREE deliberately — that venue is already
# proven (runner_canon, nightly re-sync, never an agent's workspace) and the two jobs
# do not overlap (03:00 vs 07:00). What makes sharing safe is that this pass writes
# NOTHING tracked into the runner: the approvals queue, the report and the ledger all
# resolve to the CANONICAL worktree, so the runner's `git checkout --detach` re-sync
# still finds a clean tree.
#
# Carries the janitor wrapper's hard-won lessons verbatim, because they are the same
# lessons: self-locating REPO (a hardcoded worktree IS the venue bug), absolute
# interpreter and aws (launchd's PATH is /usr/bin:/bin:/usr/sbin:/sbin), re-exec when
# the sync changes this file (a self-updating wrapper otherwise runs one generation
# behind ITSELF), and a log that names the venue it ran in.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || PY="/Users/jacksonmurphy/Dev/trading_machine-2/.venv/bin/python"
AWS="$(command -v aws 2>/dev/null || true)"
if [ ! -x "${AWS:-}" ]; then
  for c in /opt/homebrew/bin/aws /usr/local/bin/aws /usr/bin/aws; do
    [ -x "$c" ] && AWS="$c" && break
  done
fi
AWS="${AWS:-aws}"
LOG_DIR="$REPO/data/logs/director_pass"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/director_$(date +%Y-%m-%d).log"
SNS_TOPIC="arn:aws:sns:us-east-1:407539788432:archondex-paper-alerts"

{
  echo "=== director pass $(date '+%Y-%m-%d %H:%M:%S %Z') repo=$REPO aws=$AWS ==="
  cd "$REPO" || exit 1
  git fetch origin --quiet 2>&1 || echo "DIRECTOR_FETCH_FAILED (continuing; base may be stale)"

  SELF="${BASH_SOURCE[0]}"
  BEFORE="$(shasum "$SELF" 2>/dev/null | cut -d' ' -f1)"
  if [ -z "$(git status --porcelain)" ]; then
    git checkout --detach origin/main --quiet 2>&1 \
      || echo "DIRECTOR_SYNC_FAILED (running previous checkout)"
  else
    echo "DIRECTOR_SYNC_SKIPPED: runner worktree is DIRTY — not a clean runner venue"
  fi
  echo "    post-sync HEAD=$(git rev-parse --short HEAD 2>/dev/null)"
  AFTER="$(shasum "$SELF" 2>/dev/null | cut -d' ' -f1)"
  if [ -n "$BEFORE" ] && [ "$BEFORE" != "$AFTER" ] && [ -z "${DIRECTOR_REEXECED:-}" ]; then
    echo "DIRECTOR_WRAPPER_UPDATED ${BEFORE:0:8}->${AFTER:0:8} — re-executing the new wrapper"
    export DIRECTOR_REEXECED=1
    exec /bin/bash "$SELF" "$@"
  fi

  # OBSERVE-ONLY by ruling until one real pass report has been reviewed (2026-09-18).
  # Only the SCHEDULED path may claim the scheduled trigger.
  "$PY" scripts/director_pass.py --mode observe --trigger scheduled_pass "$@" 2>&1
  RC=$?
  echo "=== director pass rc=$RC ==="
  if [ "$RC" -ne 0 ]; then
    echo "DIRECTOR_PASS_FAILED rc=$RC"
    "$AWS" sns publish --profile archondex --region us-east-1 \
      --topic-arn "$SNS_TOPIC" \
      --subject "ArchonDEX director pass FAILED (launchd)" \
      --message "run_director_pass.sh $(date '+%Y-%m-%d %H:%M %Z'): rc=$RC. See $LOG" \
      2>&1 || echo "DIRECTOR_SNS_PUBLISH_FAILED (falling back to local notification)"
    osascript -e "display notification \"director pass FAILED rc=$RC — see log\" with title \"ArchonDEX ALERT\" sound name \"Basso\"" \
      2>&1 || echo "DIRECTOR_LOCAL_NOTIFY_FAILED"
  fi
} >> "$LOG" 2>&1
