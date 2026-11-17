#!/usr/bin/env bash
# Run the reviewer's simulation and the three variants, then assert the runbook's
# D+1/D+2/D+3 expectations. No network, no broker, no AWS: a fake flat broker at the
# 2026-11-16 closes drives the REAL scripts/run_paper_cloud_day.main().
# usage: bash run_sims.sh <repo_root>     (writes only under a fresh mktemp directory)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "${1:?usage: run_sims.sh <repo_root>}" && pwd)"
PY="${PY:-$REPO/.venv/bin/python}"; [ -x "$PY" ] || PY=python
T="$(mktemp -d "${TMPDIR:-/tmp}/acct2_sims.XXXXXX")"
echo "sim work + outputs under $T"
run() {  # name cash [rebase]
  PYTHONDONTWRITEBYTECODE=1 "$PY" -I "$HERE/$2" "$REPO" "$T/work_$1" "${@:3}" > "$T/$1.txt" 2> "$T/$1.err" \
    || echo "note: $1 exited non-zero (expected only if the driver failed) — see $T/$1.err"
}
run base sim_reset.py 103514.78
run rebase10k sim_variant.py 103514.78 2026-11-20
run acctA10k sim_variant.py 10000
run acctA10k_rebase sim_variant.py 10000 2026-11-20
"$PY" -I "$HERE/check_sims.py" "$T"
