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
#
# BOOTSTRAP — learned the hard way (2026-09-10, caught with three hours to spare):
# a SELF-SYNCING wrapper cannot bootstrap itself. The sync below only runs if the
# ALREADY-CHECKED-OUT copy of this file contains it, so a freshly created (or
# recreated) runner worktree still holds whatever wrapper its checkout had. After
# `git worktree add`, advance it to origin/main ONCE BY HAND:
#     git -C <runner> fetch origin && git -C <runner> checkout --detach origin/main
# Skip that and the job silently executes the old checkout's instructions — which is
# exactly the venue defect this design exists to close, wearing the fix's clothes.
set -u
# SELF-LOCATING. A wrapper that hardcodes a worktree IS the venue bug in miniature:
# the nightly job ran for nine nights against whatever branch an agent had left
# checked out, because the path was baked in here. Derive the repo from this
# script's own location so the wrapper operates on the worktree it lives in.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || PY="/Users/jacksonmurphy/Dev/trading_machine-2/.venv/bin/python"
LOG_DIR="$REPO/data/logs/janitor"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/janitor_$(date +%Y-%m-%d).log"
SNS_TOPIC="arn:aws:sns:us-east-1:407539788432:archondex-paper-alerts"

{
  # SAY WHERE YOU RAN. The venue defect was invisible for nine nights precisely
  # because nothing recorded which tree the job used. A log that names its own repo
  # and HEAD makes "where did this run?" answerable from the log alone, without
  # reconstructing what branch happened to be checked out that night.
  echo "=== janitor $(date '+%Y-%m-%d %H:%M:%S %Z') repo=$REPO ==="
  cd "$REPO" || exit 1
  echo "    HEAD=$(git rev-parse --short HEAD 2>/dev/null) origin/main=$(git rev-parse --short origin/main 2>/dev/null)"
  # Refresh the base so 'behind origin/main' is meaningful; never merges, never resets.
  git fetch origin --quiet 2>&1 || echo "JANITOR_FETCH_FAILED (continuing; base may be stale)"
  # SYNC THE RUNNER TO CANONICAL CODE. Only safe in a DEDICATED runner worktree —
  # never in one an agent works in, which is why the worktree is a precondition and
  # not a nicety. `checkout --detach` moves HEAD without `reset --hard` (deny-listed);
  # it refuses rather than clobbers if the tree is dirty, so a failure here is loud
  # and the run proceeds on the old checkout with runner_canon recording that fact.
  SELF="${BASH_SOURCE[0]}"
  BEFORE="$(shasum "$SELF" 2>/dev/null | cut -d' ' -f1)"
  if [ -z "$(git status --porcelain)" ]; then
    git checkout --detach origin/main --quiet 2>&1 \
      || echo "JANITOR_SYNC_FAILED (running previous checkout; runner_canon will say so)"
  else
    echo "JANITOR_SYNC_SKIPPED: runner worktree is DIRTY — not a clean runner venue"
  fi
  echo "    post-sync HEAD=$(git rev-parse --short HEAD 2>/dev/null)"

  # RE-EXEC IF THIS SCRIPT ITSELF CHANGED.
  # A self-updating wrapper otherwise runs ONE GENERATION BEHIND for its own code:
  # bash reads the script into memory at invocation, so the sync above rewrites the
  # FILE but not the RUNNING PROCESS. The janitor it launches is current; the
  # wrapper's own behaviour is a night stale. That is not hypothetical — on
  # 2026-09-15 the pre-merge wrapper ran the post-merge janitor without the
  # --trigger flag, and a genuinely scheduled 03:02 run was recorded as 'manual' in
  # the permanent record. The env guard makes exactly one hop, so a wrapper that
  # somehow keeps changing cannot loop.
  AFTER="$(shasum "$SELF" 2>/dev/null | cut -d' ' -f1)"
  if [ -n "$BEFORE" ] && [ "$BEFORE" != "$AFTER" ] && [ -z "${JANITOR_REEXECED:-}" ]; then
    echo "JANITOR_WRAPPER_UPDATED ${BEFORE:0:8}->${AFTER:0:8} — re-executing the new wrapper"
    export JANITOR_REEXECED=1
    exec /bin/bash "$SELF" "$@"
  fi
  # Only the SCHEDULED path may claim the scheduled trigger.
  "$PY" scripts/janitor_nightly.py --trigger nightly_schedule "$@" 2>&1
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
