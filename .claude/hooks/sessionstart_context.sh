#!/bin/bash
# sessionstart_context.sh — emits the session-prelude context to STDOUT.
# Claude Code captures a SessionStart hook's stdout and injects it into the
# session as a system reminder (before the first prompt). This hook CANNOT
# block anything; worst case on error is partial/no context injected.
#
# Externalized from settings.json (Phase 2, T-096) so it is version-controlled
# and syntax-checkable. GATE EVERY EDIT ON:  bash -n .claude/hooks/sessionstart_context.sh
#
# Run from repo root (settings.json invokes it with cwd = project root, matching
# the existing relative-path hook convention).

echo "=== CURRENT STATE (docs/State/CURRENT_STATE.md) ==="
if [ -f docs/State/CURRENT_STATE.md ]; then
  cat docs/State/CURRENT_STATE.md
else
  echo "(CURRENT_STATE.md not found — it is the at-a-glance live-state dashboard; create docs/State/CURRENT_STATE.md.)"
fi
echo
echo "=== LAST 3 SESSION SUMMARIES ==="
ls -t docs/Sessions/*/*_session*.md 2>/dev/null | head -3 | while read -r f; do
  echo "--- $f ---"
  head -25 "$f"
  echo
done
echo
echo "=== RECENT GIT ACTIVITY ==="
git log --oneline -10 2>/dev/null
echo
echo "=== HEALTH CHECK STATE ==="
grep -E "^### \[(HIGH|MEDIUM)\]" docs/State/health_check.md 2>/dev/null | head -10
echo
echo "Reading order: CLAUDE.md -> docs/State/CURRENT_STATE.md -> docs/Core/SESSION_PROCEDURES.md -> docs/README.md (for navigation)"
