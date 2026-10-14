#!/usr/bin/env bash
# RR-1 RE-SCORE campaign — eight cells, SEQUENTIAL, local (director ruling 2026-09-30).
#
# RE-SCORE, not new trials (N_trials 0). Ordered by PAIR, not by arm: each before/after
# pair completes together, so a pair that has finished is a usable result even if a later
# cell fails.
#
# Rails:
#   * sequential — run_isolated and the foundry harness write this worktree's live
#     governor files on entry; two cells at once would collide;
#   * caffeinate -i — a sleeping Mac kills a multi-hour cell;
#   * disk floor — the driver refuses below 5 GB (exit 3); this script then STOPS;
#   * ANY non-zero exit STOPS the campaign. The exit is captured before anything else:
#     an unexplained early end that takes its evidence with it is the failure to avoid.
#   * CENSUS_EXPECTED_DORMANT=news_sentiment_edge on ALL EIGHT cells, both arms
#     identically — the referee's own per-run switch, for these cells only.
set -u
cd "$(dirname "$0")/.."
LOGDIR="${RR1_LOGDIR:-/tmp/rr1_rescore_logs}"
mkdir -p "$LOGDIR"
DORMANT="news_sentiment_edge"
# run_isolated re-execs itself unless these are set BEFORE python starts, and a re-exec
# would discard the before arm's in-process getter — both arms would run the fixed code.
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_DYNAMIC=FALSE

# label | kind | extra args
CELLS=(
  "anchor26|baseline|--start 2000-01-01 --end 2025-12-31"
  "t196_triple_witching|feature|--feature triple_witching_premium"
  "t196_january|feature|--feature january_effect"
  "t196_mom_12_1|feature|--feature mom_12_1"
)

for spec in "${CELLS[@]}"; do
  IFS='|' read -r label kind extra <<<"$spec"
  for arm in before after; do
    log="$LOGDIR/${label}_${arm}.log"
    echo "[$(date '+%F %T')] START $label/$arm  (free: $(df -g . | tail -1 | awk '{print $4}') GB)  log: $log"
    # shellcheck disable=SC2086
    caffeinate -i python scripts/rescore_rr1.py --arm "$arm" --cell "$kind" $extra \
        --label "$label" --census-expected-dormant "$DORMANT" >"$log" 2>&1
    rc=$?
    echo "exit=$rc" >>"$log"
    echo "[$(date '+%F %T')] END   $label/$arm  exit=$rc  $(grep '^\[RESCORE\]' "$log" | tail -1)"
    if [ "$rc" -ne 0 ]; then
      echo "[$(date '+%F %T')] CAMPAIGN STOPPED at $label/$arm (exit=$rc). Record + log kept; investigate before resuming."
      exit "$rc"
    fi
  done
done
echo "[$(date '+%F %T')] CAMPAIGN COMPLETE — 8/8 cells"
