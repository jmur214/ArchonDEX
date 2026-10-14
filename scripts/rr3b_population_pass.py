"""RR-3 Option B — the population pass (pre-registered in the proposal's §8 before the pull).

    python -m scripts.rr3b_population_pass --s3-mirror data/observability/rr3b_s3_mirror_2026-10-13

Measures what Option B's registry would contain, so R can read the design against numbers. Read-only over
run evidence and the current registry. Writes exactly two files, NEITHER named `n_effective_*.json`:
`mbl_gate.latest_n_effective_artifact()` takes the newest file matching that pattern, so an `n_effective_*`
output would silently become the live gate's input on main.

Reuses `scripts/rr3_empirical_rho.py`'s discovery, validity filters and trial-key hashing, so the trial
definition here cannot drift from the one RR-3 merged.

N_trials consumed: 0.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.measurement.mbl_gate import N_EFF_FLOOR, compute_mbl_min, n_eff_equicorrelated  # noqa: E402
from scripts import rr3_empirical_rho as rho  # noqa: E402

TASK_TOKEN = re.compile(r"(?<![0-9a-z])t(\d{3}[a-z]?)(?![0-9])", re.IGNORECASE)


def trial_keys(runs: Dict[str, Dict]) -> Dict[str, Dict]:
    """{run_id: {"trial_key", "campaign", "source"}} for VALID runs — the same filters and the same equity
    hash as rr3_empirical_rho.run(), so a 'distinct trial' means the same thing in both."""
    out: Dict[str, Dict] = {}
    for rid, meta in sorted(runs.items()):
        if rho.census_md5(meta["summary"]) == rho.EMPTY_MD5:
            continue
        eq = rho.daily_equity(meta["snapshot"])
        if eq is None or not np.all(np.isfinite(eq.values)) or (eq.values <= 0).any():
            continue
        r = eq.pct_change().dropna()
        sd = r.std()
        if len(r) < rho.MIN_RETURNS or sd is None or sd < 1e-12 or not np.isfinite(sd):
            continue
        key = rho.trial_key(eq)
        out[rid] = {"trial_key": key, "campaign": meta["campaign"],
                    "source": "s3" if meta["campaign"].startswith("s3") else "local"}
    return out


def campaign_tasks(campaign: str) -> List[str]:
    """Task ids carried by a campaign prefix ('s3:foundry-t196' -> ['T-196']). Pre-stated rule, §8 item 3."""
    name = campaign.split(":", 1)[-1]
    return sorted({f"T-{m.group(1).lower()}" for m in TASK_TOKEN.finditer(name)})


def run(s3_mirror: Path, trade_logs: Path, registry: Path, out: Path, rho_out: Path) -> Dict:
    runs = rho.discover_runs([("disk", trade_logs), ("s3", s3_mirror)])
    tk = trial_keys(runs)
    distinct = {v["trial_key"] for v in tk.values()}

    # 1. the executed universe, by source and by campaign
    by_source = {s: len({v["trial_key"] for v in tk.values() if v["source"] == s}) for s in ("s3", "local")}
    by_campaign: Dict[str, set] = defaultdict(set)
    for v in tk.values():
        by_campaign[v["campaign"]].add(v["trial_key"])
    shared_sources = len({v["trial_key"] for v in tk.values() if v["source"] == "s3"}
                         & {v["trial_key"] for v in tk.values() if v["source"] == "local"})

    # 2. the current registry: its run rows' evidence, and its ledger rows by task
    con = sqlite3.connect(f"file:{registry}?mode=ro", uri=True)
    reg = con.execute("SELECT run_id, source FROM runs").fetchall()
    con.close()
    reg_runs = [r for r, s in reg if s is None]
    ledger = Counter(s.split(":", 1)[1] for _, s in reg if s and s.startswith("ledger:"))
    reg_runs_with_evidence = sum(1 for r in reg_runs if r in runs)

    # 3. ledger <-> run overlap (pre-stated: max(k_ledger, k_runs), never sum, never min)
    runs_by_task: Dict[str, set] = defaultdict(set)
    for camp, keys in by_campaign.items():
        for t in campaign_tasks(camp):
            runs_by_task[t] |= keys
    overlap, ledger_only = {}, {}
    for task, k in sorted(ledger.items()):
        k_runs = len(runs_by_task.get(task, set()))
        if k_runs:
            overlap[task] = {"k_ledger": k, "k_runs": k_runs, "counted": max(k, k_runs),
                             "ledger_excess_added": max(0, k - k_runs)}
        else:
            ledger_only[task] = k

    # 4. Option B's N_raw — a bracket, because the §2D substrate table is not written yet
    n_exec = len(distinct)
    n_absent = len(reg_runs) - reg_runs_with_evidence
    excess = sum(v["ledger_excess_added"] for v in overlap.values())
    n_ledger_only = sum(ledger_only.values())
    n_all = n_exec + n_absent + excess + n_ledger_only
    n_floor = n_exec + n_absent + excess

    # 5. ρ̄ / N_eff over the executed population (RR-3's own code), to a NON-gate filename
    art = rho.run(s3_mirror, trade_logs, registry, rho_out)
    gi = art["gate_inputs"]
    prior = json.loads((ROOT / "data/observability/n_effective_2026-09-30.json").read_text())

    def _neff(n: int) -> Dict:
        eq = n_eff_equicorrelated(n, float(gi["rho_bar"]))
        onc = max(N_EFF_FLOOR, min(float(n), n * float(gi["onc_compression"])))
        cons = max(eq, onc)
        return {"N_raw": n, "N_eff_equicorr": round(eq, 2), "N_eff_onc": round(onc, 2),
                "N_eff_conservative": round(cons, 2), "MinBTL_yrs_SR1": round(compute_mbl_min(cons, 1.0), 2)}

    result = {
        "schema": "rr3b_population/v1",
        "as_of": _dt.date.today().isoformat(),
        "spec": "docs/Sources/referee_repair_proposal_RR-3B_2026-10-13.md §8 (pre-registered, commit 17ec6db)",
        "n_trials_consumed": 0,
        "executed_universe": {
            "discovered_runs": len(runs), "valid_runs": len(tk), "distinct_trial_keys": n_exec,
            "distinct_by_source": by_source, "distinct_in_both_sources": shared_sources,
            "campaigns": len(by_campaign),
            "distinct_by_campaign": dict(sorted(((c, len(k)) for c, k in by_campaign.items()),
                                                key=lambda x: -x[1])),
        },
        "current_registry": {
            "rows": len(reg), "run_rows": len(reg_runs), "run_rows_with_evidence_now": reg_runs_with_evidence,
            "ledger_rows": sum(ledger.values()), "ledger_tasks": len(ledger),
        },
        "ledger_run_overlap": overlap,
        "ledger_only_tasks": ledger_only,
        "option_b_n_raw": {
            "components": {"distinct_executed_trials": n_exec, "absent_evidence_registry_rows": n_absent,
                           "ledger_excess_over_runs": excess, "ledger_only_rows": n_ledger_only},
            "all_ledger_rows_kept": n_all,
            "floor_no_ledger_only_rows": n_floor,
            "note": ("The §2D audit-cited substrate table decides where between these two the figure lands. "
                     "Tagging the 26 tasks from memory tonight would be exactly an un-cited classification, so "
                     "the bracket is reported instead of a single 'without T-306' number."),
        },
        "rho_tonight": {"rho_bar": art["rho_bar"], "rho_bar_ci95": art["rho_bar_ci95"],
                        "onc_compression": art["onc_compression"], "gate_inputs": gi,
                        "funnel": art["funnel"], "verdict": art["prereg"]["verdict"]},
        "rho_2026_09_30": {"rho_bar": prior["rho_bar"], "rho_bar_ci95": prior["rho_bar_ci95"],
                           "gate_inputs": prior["gate_inputs"], "funnel": prior["funnel"]},
        "n_eff": {
            "option_a_today_registry": _neff(len(reg)),
            "option_b_all_ledger_rows": _neff(n_all),
            "option_b_floor": _neff(n_floor),
        },
        "rho_artifact_written_to": str(rho_out),
    }
    out.write_text(json.dumps(result, indent=2, default=float))
    return result


def main(argv: Optional[List[str]] = None) -> int:
    today = _dt.date.today().isoformat()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--s3-mirror", type=Path, required=True)
    ap.add_argument("--trade-logs", type=Path, default=ROOT / "data/trade_logs")
    ap.add_argument("--registry", type=Path, default=ROOT / "data/observability/run_registry.sqlite")
    ap.add_argument("--out", type=Path, default=ROOT / f"data/observability/rr3b_population_{today}.json")
    ap.add_argument("--rho-out", type=Path, default=ROOT / f"data/observability/rr3b_rho_{today}.json")
    a = ap.parse_args(argv)
    for p in (a.out, a.rho_out):
        if p.name.startswith("n_effective_"):
            raise SystemExit(f"refusing to write {p.name}: an n_effective_* file becomes the live gate's input")
    r = run(a.s3_mirror, a.trade_logs, a.registry, a.out, a.rho_out)
    print(json.dumps({k: r[k] for k in ("executed_universe", "current_registry", "option_b_n_raw", "n_eff")},
                     indent=2, default=float)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
