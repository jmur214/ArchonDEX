#!/bin/bash
# scripts/run_t295_gated_population.sh
# ---------------------------------------------------------------------------
# T-295 rate-path population — the POLITE gated protocol, on a scheduler.
#
# Yahoo (the only remaining free ZQ source) is globally 429-throttling its
# unauthenticated chart API — confirmed from 3 distinct IPs (dev, AWS, hotspot)
# on 2026-07-08. The ban resets on contact, so patience is the fix and this job
# must spend AT MOST ONE Yahoo contact per firing:
#
#   1. FRED health-gate (non-Yahoo, free) — the script needs FRED for its
#      validation step. If FRED is down, ABORT before touching Yahoo.
#   2. ONE no-retry Yahoo probe. NOT the populate script directly — its _get()
#      has 429 backoff, so a script run = several contacts, each resetting the
#      ban. A single probe = exactly one contact.
#   3. Only on HTTP 200 do we run the real population + upload the 2 parquets.
#
# On success it writes rate_path_reconstructed.parquet + fed_tracker_
# minneapolis.parquet, prints the meeting-prob confirmation, and touches a DONE
# sentinel so the next session just reads this log and makes the "T-295 done"
# ledger call. Scheduled twice (22:30 + 06:30 CT) via
# com.archondex.t295-population.plist. Unload once T-295 closes:
#   launchctl bootout gui/$(id -u)/com.archondex.t295-population
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="/Users/jacksonmurphy/Dev/trading_machine-2"
cd "$ROOT" || exit 1
LOG_DIR="$ROOT/data/macro_data/alt/logs"
mkdir -p "$LOG_DIR"
DONE="$LOG_DIR/t295_population.DONE"
STAMP="$(date '+%Y-%m-%dT%H:%M:%S%z')"

echo "===== T-295 gated population @ $STAMP ====="

# Idempotent: if a prior firing already succeeded, do nothing (spend no contact).
if [ -f "$DONE" ]; then
    echo "already DONE ($(cat "$DONE")) — nothing to do; unload the job."
    exit 0
fi

BUCKET="archondex-results-407539788432"
DEST="s3://$BUCKET/altdata/data/macro_data/alt"

# 1) FRED health-gate (no Yahoo contact).
FRED=$(python - <<'PY'
import urllib.request
ua={'User-Agent':'Mozilla/5.0'}
try:
    r=urllib.request.urlopen(urllib.request.Request(
        'https://fred.stlouisfed.org/graph/fredgraph.csv?id=EFFR', headers=ua), timeout=30)
    print('UP' if r.getcode()==200 else 'DOWN')
except Exception:
    print('DOWN')
PY
)
echo "FRED health: $FRED"
if [ "$FRED" != "UP" ]; then
    echo "ABORT: FRED down — not spending the Yahoo contact. Next firing will retry."
    exit 0
fi

# 2) ONE no-retry Yahoo probe.
YH=$(python - <<'PY'
import urllib.request, urllib.error
ua={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
try:
    r=urllib.request.urlopen(urllib.request.Request(
        'https://query1.finance.yahoo.com/v8/finance/chart/ZQ%3DF?range=5d&interval=1d',
        headers=ua), timeout=25)
    print('OK' if r.getcode()==200 else f'HTTP{r.getcode()}')
except urllib.error.HTTPError as e:
    print(f'HTTP{e.code}')
except Exception as e:
    print(f'ERR{type(e).__name__}')
PY
)
echo "Yahoo single probe: $YH"
if [ "$YH" != "OK" ]; then
    echo "STILL THROTTLED ($YH) — stopping, no retries. Next firing will try again."
    exit 0
fi

# 3) Ban lifted → populate ONCE, then upload the 2 produced parquets.
echo "=== Yahoo reachable; running T-295 population ==="
if python -m scripts.build_rate_path_history_t295; then
    echo "=== population OK; uploading parquets to $DEST ==="
    aws s3 cp "$ROOT/data/macro_data/alt/rate_path_reconstructed.parquet" \
        "$DEST/rate_path_reconstructed.parquet" --profile archondex --no-progress
    aws s3 cp "$ROOT/data/macro_data/alt/fed_tracker_minneapolis.parquet" \
        "$DEST/fed_tracker_minneapolis.parquet" --profile archondex --no-progress
    # meeting-prob confirmation for the next session to read
    echo "=== meeting-prob end-to-end confirmation ==="
    python - <<'PY'
import pandas as pd
df = pd.read_parquet('data/macro_data/alt/rate_path_reconstructed.parquet')
print('series_type counts:', df['series_type'].value_counts().to_dict())
mp = df[df['series_type'] == 'meeting_prob']
print(f'meeting_prob rows: {len(mp)}')
if len(mp):
    cols = [c for c in ('date','contract','prob_25bp_move','direction','implied_change_bp') if c in mp.columns]
    print(mp[cols].head(10).to_string(index=False))
PY
    echo "T-295 populated $STAMP" > "$DONE"
    echo "===== T-295 POPULATION SUCCEEDED — parquets written + uploaded; make the ledger call ====="
else
    echo "populate script FAILED after a 200 probe (transient?) — DONE sentinel NOT written; next firing retries."
fi
