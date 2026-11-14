"""T-393 — measure the era_tr DISTRIBUTION GUARD against (a′) v4 without writing a full candidate (disk).

Rule and acceptance PRE-DECLARED in `docs/Sources/proposal_era_tr_distribution_guard_t393_2026-11-13.md` §1
(committed alone before the code). v5 = v4's inputs through the guarded `engines/data_manager/era_tr.py`.

  run       rebuild all 575 files IN MEMORY with the guarded era_tr; compare each text to v4's MANIFEST md5;
            write ONLY the changed files (+ their records, every label change, a manifest) to --out; then run
            T-384's acceptance in memory on v5 → <out>/acceptance/ (+ summary_t393.json beside v4's numbers)
  manifest  md5 of every file under --out

Read-only inputs: the canonical cache + `_merge_meta.json`, raw Stooq, the pinned yfinance cache (verified
against `config/era_tr_reference_yf_manifest.sha256`), v4 (labels, records, MANIFEST), T-265. No network.
Writes only under --out (default `Dev/_substrate_candidates/era_tr_v5_delta_t393/`); HALTS below 9.5 GiB free.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engines.data_manager import era_tr as et  # noqa: E402
from scripts import drip_fix_candidate_t384 as t384  # noqa: E402
from scripts.cutover_step1_pass import verify_yf_manifest  # noqa: E402

V4_DIR = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_v4_2026_11_11")
YF_DIR = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_2026_11_11/yf")
YF_MANIFEST = REPO / "config" / "era_tr_reference_yf_manifest.sha256"
DEFAULT_OUT = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/era_tr_v5_delta_t393")
MIN_FREE_GIB = 9.5
OUT_BUDGET_BYTES = 50 * 1024 ** 2
LABEL_KEYS = ["ticker", "ex_date", "day", "D", "P_prev", "m", "label_source", "close_move", "close_move_best",
              "close_sigma", "z_drop", "refusal_reason", "spinoff_repaired", "log_f", "log_f_dividend",
              "unresolved_reason"]


def check_disk(path: Path) -> None:
    free = shutil.disk_usage(path).free / 1024 ** 3
    if free < MIN_FREE_GIB:
        raise SystemExit(f"HALT: free disk {free:.2f} GiB < {MIN_FREE_GIB} GiB")


def out_dir(p: Path) -> Path:
    out = t384.assert_outside_canon(Path(p))
    for ro in (V4_DIR, YF_DIR.parent):
        r = Path(ro).resolve()
        if out == r or r in out.parents:
            raise SystemExit(f"REFUSED: {out} is inside the read-only input {r}")
    out.mkdir(parents=True, exist_ok=True)
    return out


def v4_state() -> Tuple[Dict[str, dict], Dict[str, str]]:
    recs: Dict[str, dict] = {}
    with open(V4_DIR / "build_records.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            recs[r["ticker"]] = r
    md5: Dict[str, str] = {}
    for line in (V4_DIR / "MANIFEST.md5").read_text().splitlines():
        h, rel = line.split("  ", 1)
        if rel.startswith("processed/") and rel.endswith("_1d.csv"):
            md5[rel[len("processed/"): -len("_1d.csv")]] = h
    return recs, md5


def v4_missed(t: str) -> pd.DataFrame:
    p = V4_DIR / "probe" / "labels" / f"{t}.parquet"
    if not p.exists():
        return pd.DataFrame(columns=["day", "missed"])
    return pd.read_parquet(p, columns=["day", "missed"])


class V5InMemory:
    """Every file rebuilt through the guarded era_tr; only the texts that differ from v4 are kept."""

    def __init__(self) -> None:
        self.meta = t384.load_meta()
        self.raw_idx = t384.raw_stooq_index()
        self.recs, self.v4_md5 = v4_state()
        self.written = sorted(t for t, r in self.recs.items() if r["status"] == "written")
        self.labels: Dict[str, pd.DataFrame] = {}
        self.changed_text: Dict[str, str] = {}
        self.changed_record: Dict[str, dict] = {}
        self.label_changes: List[dict] = []
        self.unresolved: List[dict] = []

    def build_all(self) -> None:
        for n, t in enumerate(self.written):
            raw = et.read_raw_stooq(self.raw_idx[t])
            px, dv = et.read_yf(t, YF_DIR)
            ref = et.analyse_reference(t, raw, px, dv, pd.Timestamp(self.meta[t]["seam_date"]))
            if ref.status != self.recs[t]["reference"]:
                raise SystemExit(f"{t}: reference status {ref.status} != v4's {self.recs[t]['reference']}")
            header, lines = t384.read_cache_text(t)
            res = et.build_file(t, self.meta[t], header, lines, t384.read_cache_frame(t), raw, ref)
            lab = ref.labels
            self.labels[t] = lab
            if hashlib.md5(res.text.encode()).hexdigest() != self.v4_md5[t]:
                self.changed_text[t] = res.text
                self.changed_record[t] = {"status": "written", **res.record}
            if len(lab):
                old = v4_missed(t)
                was = pd.Series(old["missed"].to_numpy(dtype=bool), index=pd.DatetimeIndex(old["day"]))
                now = pd.Series(lab["missed"].to_numpy(dtype=bool), index=pd.DatetimeIndex(lab["day"]))
                if not was.index.equals(now.index):
                    raise SystemExit(f"{t}: the labelled ex-dates differ from v4's (not only their labels)")
                moved = (was.to_numpy() != now.to_numpy()) | lab["spinoff_repaired"].to_numpy(dtype=bool)
                diff = lab[moved].assign(ticker=t)
                self.label_changes += diff.assign(v4_missed=was.to_numpy()[moved])[
                    LABEL_KEYS + ["v4_missed", "missed"]].to_dict("records")
                self.unresolved += lab[lab["unresolved"].to_numpy(dtype=bool)].assign(ticker=t)[LABEL_KEYS].to_dict("records")
            if (n + 1) % 100 == 0:
                print(f"[build] {n + 1}/{len(self.written)} changed={len(self.changed_text)}", flush=True)

    # providers for t384.run_acceptance
    def candidate(self, t: str) -> Tuple[pd.Series, List[str]]:
        if t in self.changed_text:
            text = self.changed_text[t]
        else:
            # ticker-exclusions: bypassed — data-ops: an unchanged v5 file IS v4's file (md5-proven); read from the candidate outside the repo
            text = (V4_DIR / "processed" / f"{t}_1d.csv").read_text()
        df = pd.read_csv(io.StringIO(text), usecols=["Date", "Close"], float_precision="round_trip")
        return (pd.Series(df["Close"].to_numpy(dtype=float), index=pd.to_datetime(df["Date"]), name="cand"),
                text.split("\n")[1:-1])

    def labels_for(self, t: str) -> Optional[pd.DataFrame]:
        lab = self.labels.get(t)
        return lab if lab is not None and len(lab) else None


def cmd_run(args: argparse.Namespace) -> int:
    out = out_dir(Path(args.out))
    check_disk(out)
    yf_sha = verify_yf_manifest(YF_DIR, YF_MANIFEST)
    v5 = V5InMemory()
    v5.build_all()
    check_disk(out)
    for t, text in sorted(v5.changed_text.items()):
        t384.write_pair(out / "processed", t, text)
    with open(out / "build_records_changed.jsonl", "w") as fh:
        for t in sorted(v5.changed_record):
            fh.write(json.dumps(v5.changed_record[t], default=str) + "\n")
    pd.DataFrame(v5.label_changes).to_csv(out / "label_changes.csv", index=False)
    pd.DataFrame(v5.unresolved).to_csv(out / "unresolved_distributions.csv", index=False)
    delta = {"yf_manifest_sha256": yf_sha, "v4": str(V4_DIR), "files": len(v5.written),
             "unchanged_md5_equal_v4": len(v5.written) - len(v5.changed_text),
             "changed": {t: {"v4_md5": v5.v4_md5[t], "v5_md5": hashlib.md5(v5.changed_text[t].encode()).hexdigest(),
                             "refused": [f"{r['ex_date']}:{r['reason']}" for r in v5.changed_record[t]["refused_distributions"]],
                             "repaired": [f"{r['ex_date']}:{r['log_step']:.6f}" for r in v5.changed_record[t]["stooq_spinoff_repaired"]]}
                         for t in sorted(v5.changed_text)},
             "n_label_changes": len(v5.label_changes), "n_unresolved": len(v5.unresolved)}
    (out / "delta.json").write_text(json.dumps(delta, indent=2))
    print(json.dumps({k: v for k, v in delta.items() if k != "changed"}, indent=2))
    print("changed files:", sorted(v5.changed_text))
    rc = t384.run_acceptance(V4_DIR, YF_DIR, out / "acceptance", candidate=v5.candidate, labels=v5.labels_for)
    (out / "acceptance" / "summary_t393.json").write_text(json.dumps(summary_vs_v4(out / "acceptance"), indent=2, default=str))
    return rc


def summary_vs_v4(adir: Path) -> dict:
    a = json.loads((adir / "summary.json").read_text())
    b = json.loads((V4_DIR / "acceptance" / "summary.json").read_text())
    key = ["ticker", "year", "seam_stub"]
    di = pd.read_csv(adir / "i_t265.csv").merge(pd.read_csv(V4_DIR / "acceptance" / "i_t265.csv")[key + ["x_pp", "pass"]],
                                                on=key, suffixes=("", "_v4"))
    dii = pd.read_csv(adir / "ii_yf.csv").merge(pd.read_csv(V4_DIR / "acceptance" / "ii_yf.csv")[["ticker", "year", "x_pp"]],
                                                on=["ticker", "year"], suffixes=("", "_v4"))
    mi = di[(di["x_pp"] - di["x_pp_v4"]).abs() > 1e-9]
    mii = dii[(dii["x_pp"] - dii["x_pp_v4"]).abs() > 1e-9]
    return {"verdict": a["verdict"], "verdict_v4": b["verdict"],
            "i": {"fail": a["i"]["fail"], "fail_v4": b["i"]["fail"], "pass_strict": a["i"]["pass_strict"],
                  "pass_strict_v4": b["i"]["pass_strict"],
                  "moved": mi[key + ["x_pp_v4", "x_pp", "pass_v4", "pass"]].to_dict("records")},
            "ii": {int(y): {"median": v["median_abs_pp"], "p95": v["p95_abs_pp"], "pass": v["pass"],
                            "p95_v4": b["ii"]["by_year"][str(y)]["p95_abs_pp"], "pass_v4": b["ii"]["by_year"][str(y)]["pass"]}
                   for y, v in ((int(k), v) for k, v in a["ii"]["by_year"].items())},
            "ii_moved": mii[["ticker", "year", "x_pp_v4", "x_pp"]].to_dict("records"),
            "iii": a["iii"], "iii_v4": b["iii"], "iii_c": a.get("iii_c"), "iv": a["iv"],
            "step_audit": a.get("step_audit"), "step_audit_v4": b.get("step_audit")}


def cmd_manifest(args: argparse.Namespace) -> int:
    out = out_dir(Path(args.out))
    lines, total = [], 0
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.md5":
            lines.append(f"{hashlib.md5(p.read_bytes()).hexdigest()}  {p.relative_to(out)}")
            total += p.stat().st_size
    body = "\n".join(lines) + "\n"
    (out / "MANIFEST.md5").write_text(body)
    print(f"[manifest] {len(lines)} files, {total / 1024 ** 2:.1f} MB; md5 of MANIFEST.md5 {hashlib.md5(body.encode()).hexdigest()}")
    return 5 if total > OUT_BUDGET_BYTES else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="rebuild in memory, write only the changed files, run T-384's acceptance on v5")
    r.add_argument("--out", default=str(DEFAULT_OUT))
    r.set_defaults(func=cmd_run)
    m = sub.add_parser("manifest", help="md5 of every file under --out")
    m.add_argument("--out", default=str(DEFAULT_OUT))
    m.set_defaults(func=cmd_manifest)
    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
