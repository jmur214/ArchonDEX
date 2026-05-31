#!/bin/bash
# stop_freshness.sh — ADVISORY ONLY. Must NEVER block session end.
#
# INVARIANT: this hook must always allow the stop. It writes nudges to STDERR
# and exits 0. It must NEVER emit a `{"decision":"block"}` JSON to stdout and
# must NEVER exit 2 (exit 2 = a blocking error to Claude Code's Stop hook, and
# a blocked stop has NO user force-end — it would brick session-end). The
# settings.json wrapper ALSO forces `; exit 0`, so even a bug here cannot brick.
#
# Externalized from settings.json (Phase 2, T-096) precisely so it is
# version-controlled and syntax-checkable: a dense inline bash -c one-liner with
# a typo exits 2 and bricks; an external file can be vetted.
# GATE EVERY EDIT ON:  bash -n .claude/hooks/stop_freshness.sh
#
# If this hook is ever changed to actually block, it MUST additionally (a) honor
# stop_hook_active from stdin and (b) ship a documented in-band override. As
# written it is advisory and always exits 0.

# All freshness logic runs in a swallowed subshell so no error can escape.
(
  cs="docs/State/CURRENT_STATE.md"
  threshold_days=7
  if [ -f "$cs" ]; then
    stamp=$(grep -iE "Last reconciled" "$cs" 2>/dev/null | head -1 | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}" | head -1)
    if [ -n "$stamp" ]; then
      now=$(date +%s 2>/dev/null)
      # BSD (darwin) date first, then GNU date, then empty -> skip (fail-open).
      then_ts=$(date -j -f "%Y-%m-%d" "$stamp" +%s 2>/dev/null || date -d "$stamp" +%s 2>/dev/null || echo "")
      if [ -n "$now" ] && [ -n "$then_ts" ]; then
        age=$(( (now - then_ts) / 86400 ))   # divisor is the constant 86400 — never zero
        if [ "$age" -gt "$threshold_days" ]; then
          echo "WARN: docs/State/CURRENT_STATE.md last reconciled $stamp ($age days ago, threshold ${threshold_days}d). If you did substantive work this session, reconcile CURRENT_STATE.md before ending. Non-blocking nudge — the session may still end." >&2
        fi
      fi
    fi
  fi
) || true

# Standing session-end reminder (preserves the original Stop-hook behavior, now
# with the CURRENT_STATE reconcile step folded in). Always to stderr.
ym=$(date +%Y-%m 2>/dev/null)
ymd=$(date +%Y-%m-%d 2>/dev/null)
echo "Session ending. If substantive work was done: reconcile docs/State/CURRENT_STATE.md (live-state dashboard); write a summary to docs/Sessions/${ym}/${ymd}_session.md using docs/Sessions/_template.md (skip if trivial); update execution_manual.md if new CLI was used; mark roadmap items [x] if completed; append docs/State/health_check.md findings; run sync_docs.py if engines/ files changed." >&2

exit 0
