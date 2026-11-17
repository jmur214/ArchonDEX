#!/usr/bin/env bash
# Run the reviewer's simulation, the three variants and the two stray-run simulations, then
# assert the runbook's D+1/D+2/D+3 expectations. No network, no broker, no AWS: a fake broker
# at the 2026-11-16 closes drives the REAL scripts/run_paper_cloud_day.main().
# usage: bash run_sims.sh <repo_root>     (writes only under a fresh mktemp directory)
#
# INTERPRETER: the simulations import the repo (pandas, alpaca-py 0.43.2, python-dotenv), so
# they need the repo's virtualenv interpreter. It is taken from $PY, else <repo_root>/.venv/bin/python.
# A git worktree has no .venv of its own: point PY at the main checkout's, e.g.
#   PY=/path/to/trading_machine-2/.venv/bin/python bash run_sims.sh .
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "${1:?usage: run_sims.sh <repo_root>}" && pwd)"
PY="${PY:-$REPO/.venv/bin/python}"
if [ ! -x "$PY" ]; then
  echo "STOP: no interpreter at '$PY'. These simulations need the repo's virtualenv Python" >&2
  echo "      (pandas, alpaca-py 0.43.2, python-dotenv). Set PY=<checkout>/.venv/bin/python." >&2
  exit 2
fi
"$PY" -I -c 'import pandas, dotenv, alpaca' 2>/dev/null || {
  echo "STOP: '$PY' cannot import pandas / python-dotenv / alpaca-py — not the repo's virtualenv." >&2
  echo "      Set PY=<checkout>/.venv/bin/python." >&2
  exit 2; }
T="$(mktemp -d "${TMPDIR:-/tmp}/acct2_sims.XXXXXX")"
echo "interpreter $PY; sim work + outputs under $T"
run() {  # name script args...
  local name="$1" script="$2"; shift 2
  PYTHONDONTWRITEBYTECODE=1 "$PY" -I "$HERE/$script" "$REPO" "$T/work_$name" "$@" > "$T/$name.txt" 2> "$T/$name.err" \
    || echo "note: $name exited non-zero — see $T/$name.err"
}
run base sim_reset.py 103514.78
run rebase10k sim_variant.py 103514.78 2026-11-20
run acctA10k sim_variant.py 10000
run acctA10k_rebase sim_variant.py 10000 2026-11-20
run stray_wedge sim_stray.py wedge
run stray_recover sim_stray.py recover
"$PY" -I "$HERE/check_sims.py" "$T"
