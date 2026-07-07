#!/bin/bash
# T-289 — durable one-shot: complete the resumable news-panel backfill, then run the frozen interaction tests.
# Run under launchd (survives interactive-session boundaries) via com.archondex.t289.plist, per the director's
# standing note (>30min unattended work → launchd/cloud, not an interactive background job).
set -o pipefail
cd /Users/jacksonmurphy/Dev/trading_machine-agent-d || exit 1
PY=/Users/jacksonmurphy/Dev/trading_machine-2/.venv/bin/python3
echo "=== T-289 backfill start $(date -u +%FT%TZ) ==="
"$PY" -m scripts.build_news_panel_t289 --all
rc=$?
echo "=== backfill exit=$rc $(date -u +%FT%TZ) ==="
if [ "$rc" -eq 0 ]; then
  echo "=== BACKFILL DONE — running interaction tests ==="
  "$PY" -m scripts.news_interaction_tests_t289
  echo "=== tests exit=$? $(date -u +%FT%TZ) ==="
fi
