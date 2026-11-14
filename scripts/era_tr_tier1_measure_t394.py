"""T-394 — export the pinned Tier-1 corrections table, and measure the wired writer path against T-390's render.

Pre-declared: `docs/Sources/proposal_era_tr_tier1_wiring_t394_2026-11-14.md` §1 (committed alone first).

  export-table  write `config/stooq_corrections_tier1.json` (the 11 Tier-1 rows) and
                `config/stooq_corrections_unverified.json` (the Tier-2 label per file + three known omissions)
                from T-390's v5-based corrections table; print the two sha256s for `stooq_tier1.py`'s pins
  run           rebuild all 575 files IN MEMORY through `era_tr.build_file(changes=…)` with the pinned table —
                the same calls the writer makes — and compare every text with T-390's own v5 + Tier 1 render;
                write only the files that differ from v5, then run T-384's acceptance in memory
  manifest      md5 of every file under --out

Read-only inputs: the canonical cache + `_merge_meta.json`, raw Stooq, the pinned yfinance cache, v4 (records,
MANIFEST), the v5 delta, T-390's v5-based outputs (`stooq_repair_t390_v5/`), T-265, the EDGAR 8-K panel.
No network. Writes only `config/` (export-table) and --out (default `Dev/_substrate_candidates/
era_tr_tier1_t394/`); HALTS below 10 GiB free.
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

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engines.data_manager import era_tr as et  # noqa: E402
from engines.data_manager import stooq_tier1 as st1  # noqa: E402
from scripts import drip_fix_candidate_t384 as t384  # noqa: E402
from scripts.cutover_step1_pass import verify_yf_manifest  # noqa: E402

CAND = Path("/Users/jacksonmurphy/Dev/_substrate_candidates")
V4_DIR = CAND / "drip_fix_a_prime_v4_2026_11_11"
T390_DIR = CAND / "stooq_repair_t390_v5"
YF_DIR = CAND / "drip_fix_a_prime_2026_11_11" / "yf"
YF_MANIFEST = REPO / "config" / "era_tr_reference_yf_manifest.sha256"
V5_DELTA_CFG = REPO / "config" / "era_tr_v5_delta_t393.json"
EDGAR_8K = REPO / "data" / "edgar" / "8k" / "panel_8k_items.parquet"
DEFAULT_OUT = CAND / "era_tr_tier1_t394"
MIN_FREE_GIB = 10.0
EDGAR_BDAYS = 5
#: The reviewer's known omissions (proposal §1.6): labels on their files, never rows.
KNOWN_UNAPPLIED = {
    "GE": [{"date": "2019-02-26", "what": "Wabtec: Stooq 3.93 % below yfinance and 3.98 % below T-265 on the day; "
            "T-390's market gate refused the row (Stooq's own 3-day move against the Stooq market +6.9 %); "
            "GE 2019 fails T-384 (i) at -3.95 pp"}],
    "HON": [{"date": "2018-10-01", "what": "Garrett: Stooq 1.11 % below both references; T-390's market gate refused "
             "the row (+0.4 %); HON 2018 fails T-384 (i) at -1.14 pp after the Resideo row"}],
    "APD": [{"date": "2016-09-29", "what": "a separate dividend-sized Stooq offset (+0.57 %) two bars before the "
             "Versum step; APD 2016 fails T-384 (i) at +0.59 pp after the Versum row; below T-390's 1 % floor"}],
}


def check_disk(path: Path) -> None:
    free = shutil.disk_usage(path).free / 1024 ** 3
    if free < MIN_FREE_GIB:
        raise SystemExit(f"HALT: free disk {free:.2f} GiB < {MIN_FREE_GIB} GiB")


def out_dir(p: Path) -> Path:
    out = t384.assert_outside_canon(Path(p))
    for ro in (V4_DIR, YF_DIR.parent, T390_DIR, CAND / "era_tr_v5_delta_t393"):
        r = Path(ro).resolve()
        if out == r or r in out.parents:
            raise SystemExit(f"REFUSED: {out} is inside the read-only input {r}")
    out.mkdir(parents=True, exist_ok=True)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# export-table
# ═══════════════════════════════════════════════════════════════════════════════

def _edgar_refs(filings: pd.DataFrame, ticker: str, date: str) -> List[dict]:
    """Every 8-K the ticker filed within ±5 business days of the date (accession, filing date, items)."""
    f = filings[filings["ticker"] == ticker]
    if f.empty:
        return []
    fd = pd.DatetimeIndex(f["filing_date"]).values.astype("datetime64[D]")
    dd = np.datetime64(pd.Timestamp(date).date(), "D")
    gap = np.abs(np.busday_count(np.minimum(fd, dd), np.maximum(fd, dd)))
    sel = f[gap <= EDGAR_BDAYS].sort_values("filing_date")
    return [{"accession": str(r.accession), "filing_date": str(pd.Timestamp(r.filing_date).date()), "items": str(r.items)}
            for r in sel.itertuples(index=False)]


def cmd_export_table(args: argparse.Namespace) -> int:
    src = Path(args.table)
    table = pd.read_parquet(src)
    table["date"] = pd.to_datetime(table["date"])
    table["end_date"] = pd.to_datetime(table["end_date"])
    applied = table[table["status"] == "applied"]
    t1 = applied[applied["tier"] == "1"].sort_values(["ticker", "date"])
    t2 = applied[applied["tier"] == "2"].sort_values(["ticker", "date"])
    if len(t1) != st1.N_TIER1_ROWS or (applied["tier"] == "contradicted").any():
        raise SystemExit(f"REFUSED: {len(t1)} Tier-1 rows (want {st1.N_TIER1_ROWS}) or a contradicted row in {src}")
    filings = pd.read_parquet(EDGAR_8K, columns=["ticker", "accession", "filing_date", "items"])
    filings["filing_date"] = pd.to_datetime(filings["filing_date"])
    source = {"table": str(src), "table_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
              "built_by": "scripts/stooq_repair_t390.py build on research/stooq-repair-t390 @ c1610fb (the v5 base)",
              "proposal": "docs/Sources/proposal_stooq_repair_t390_2026-11-13.md §10-§11"}
    rows = []
    for r in t1.itertuples(index=False):
        d = str(r.date.date())
        rows.append({"ticker": r.ticker, "kind": r.kind, "date": d,
                     "end_date": None if pd.isna(r.end_date) else str(r.end_date.date()),
                     "log_amount": float(r.log_amount), "t265_log_amount": float(r.t265_value),
                     "amount_source": str(r.amount_source), "cluster_n": None if pd.isna(r.cluster_n) else int(r.cluster_n),
                     "edgar_8k": _edgar_refs(filings, r.ticker, d) if r.kind == st1.KIND_STEP else []})
    doc1 = {"_what": "T-394: the 11 Tier-1 Stooq corrections the cutover writer APPLIES (T-390's rows that T-265 covers "
                     "and agrees with). A step of log_amount s at `date` multiplies every earlier bar by exp(s); a block "
                     "of offset log_amount over [date, end_date) multiplies those bars by exp(-log_amount). Pinned by "
                     "sha256 in engines/data_manager/stooq_tier1.py.",
            "source": source, "rows": rows}
    tier2: Dict[str, dict] = {}
    for t, g in t2.groupby("ticker"):
        st = g[g["kind"] == st1.KIND_STEP]
        bl = g[g["kind"] == st1.KIND_BLOCK]
        tier2[t] = {"n_steps": int(len(st)), "n_blocks": int(len(bl)),
                    "steps": [str(d.date()) for d in st["date"]],
                    "blocks": [[str(a.date()), str(b.date())] for a, b in zip(bl["date"], bl["end_date"])]}
    doc2 = {"_what": "T-394: the Tier-2 LABEL. Corrections T-390 found that T-265 cannot check (yfinance-derived, "
                     "UNVERIFIED). NEVER applied; copied per file into the write record as unverified_stooq_corrections. "
                     "Pinned by sha256 in engines/data_manager/stooq_tier1.py.",
            "source": source, "n_rows": int(len(t2)), "n_files": int(len(tier2)),
            "known_unapplied": KNOWN_UNAPPLIED, "tier2": tier2}
    for path, doc in ((st1.TIER1_PATH, doc1), (st1.UNVERIFIED_PATH, doc2)):
        path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        print(f"{path.name}: sha256 {hashlib.sha256(path.read_bytes()).hexdigest()}")
    print(f"tier 1: {len(rows)} rows on {t1['ticker'].nunique()} files; tier 2: {len(t2)} rows on {len(tier2)} files")
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
# run: the writer's own calls, in memory, against T-390's render
# ═══════════════════════════════════════════════════════════════════════════════

class Tier1InMemory:
    def __init__(self, table: st1.Tier1Table) -> None:
        self.table = table
        self.meta = t384.load_meta()
        self.raw_idx = t384.raw_stooq_index()
        self.recs: Dict[str, dict] = {}
        with open(V4_DIR / "build_records.jsonl") as fh:
            for line in fh:
                r = json.loads(line)
                self.recs[r["ticker"]] = r
        self.written = sorted(t for t, r in self.recs.items() if r["status"] == "written")
        cfg = json.loads(V5_DELTA_CFG.read_text())["changed"]
        self.v5_md5: Dict[str, str] = {}
        for line in (V4_DIR / "MANIFEST.md5").read_text().splitlines():
            h, rel = line.split("  ", 1)
            if rel.startswith("processed/") and rel.endswith("_1d.csv"):
                self.v5_md5[rel[len("processed/"): -len("_1d.csv")]] = h
        self.v5_md5.update({t: v["v5_md5"] for t, v in cfg.items()})
        self.text: Dict[str, str] = {}          # only the files that differ from v5
        self.md5: Dict[str, str] = {}
        self.labels: Dict[str, pd.DataFrame] = {}
        self.changes: Dict[str, pd.Series] = {}
        self.records: Dict[str, dict] = {}
        self.rails_failed: List[str] = []

    def build_all(self) -> None:
        st1.check_universe(self.table, self.written)
        for n, t in enumerate(self.written):
            seam = pd.Timestamp(self.meta[t]["seam_date"])
            raw = et.read_raw_stooq(self.raw_idx[t])
            px, dv = et.read_yf(t, YF_DIR)
            ref = et.analyse_reference(t, raw, px, dv, seam)
            header, lines = t384.read_cache_text(t)
            frame = t384.read_cache_frame(t)
            rows = self.table.rows_for(t)
            changes = None
            if rows:
                lab = ref.labels
                guard = (pd.DatetimeIndex(lab.loc[lab["refused"].to_numpy(dtype=bool), "day"]) if len(lab) else None)
                changes = st1.changes_for_file(t, rows, pd.DatetimeIndex(frame["Date"]), seam, guard)
                self.changes[t] = changes
            res = et.build_file(t, self.meta[t], header, lines, frame, raw, ref, changes=changes)
            new_close = pd.Series(res.frame["Close"].to_numpy(dtype=float), index=pd.DatetimeIndex(res.frame["Date"]))
            cache_close = pd.Series(frame["Close"].to_numpy(dtype=float), index=pd.DatetimeIndex(frame["Date"]))
            steps = et.step_audit(new_close, raw, ref.labels, seam, changes=changes)
            splice = et.splice_audit(new_close, cache_close, raw, ref.labels, seam, res.record["splice"], changes=changes)
            if not (steps["pass"] and splice["pass"]):
                self.rails_failed.append(t)
            self.md5[t] = hashlib.md5(res.text.encode()).hexdigest()
            if len(ref.labels):
                self.labels[t] = ref.labels
            if self.md5[t] != self.v5_md5[t]:
                self.text[t] = res.text
                self.records[t] = {"ticker": t, "rows": rows, "step_audit": steps, "splice_audit": splice,
                                   "stooq_correction_changes": res.record["stooq_correction_changes"]}
            if (n + 1) % 100 == 0:
                print(f"[build] {n + 1}/{len(self.written)} differ from v5: {len(self.text)}", flush=True)

    def candidate(self, t: str) -> Tuple[pd.Series, List[str]]:
        if t in self.text:
            text = self.text[t]
        else:
            delta = json.loads(V5_DELTA_CFG.read_text())["changed"]
            base = (CAND / "era_tr_v5_delta_t393") if t in delta else V4_DIR
            # ticker-exclusions: bypassed — data-ops: an unchanged file IS v5's file (md5-proven in build_all); read from the candidate outside the repo
            text = (base / "processed" / f"{t}_1d.csv").read_text()
        df = pd.read_csv(io.StringIO(text), usecols=["Date", "Close"], float_precision="round_trip")
        return (pd.Series(df["Close"].to_numpy(dtype=float), index=pd.to_datetime(df["Date"]), name="cand"),
                text.split("\n")[1:-1])

    def labels_for(self, t: str) -> Optional[pd.DataFrame]:
        return self.labels.get(t)

    def changes_for(self, t: str) -> Optional[pd.Series]:
        return self.changes.get(t)


def _csv_equal(a_dir: Path, b_dir: Path) -> Dict[str, bool]:
    names = ["i_t265", "ii_yf", "iii_nonpayers", "iv_bytes", "era_deltas", "b_before_after", "iii_c_no_reference", "step_audit"]
    return {n: bool(pd.read_csv(a_dir / f"{n}.csv").equals(pd.read_csv(b_dir / f"{n}.csv"))) for n in names}


def cmd_run(args: argparse.Namespace) -> int:
    out = out_dir(Path(args.out))
    check_disk(out)
    verify_yf_manifest(YF_DIR, YF_MANIFEST)
    table = st1.load_tier1()
    mem = Tier1InMemory(table)
    mem.build_all()
    t390 = json.loads((T390_DIR / "tier1_render" / "render_md5.json").read_text())
    want = t390["md5"]
    changed = sorted(mem.text)
    ident_changed = [t for t in t390["changed"] if mem.md5.get(t) == want[t]]
    others = [t for t in mem.written if t not in t390["changed"]]
    ident_v5 = [t for t in others if mem.md5[t] == mem.v5_md5[t] == want[t]]
    for t in changed:
        t384.write_pair(out / "processed", t, mem.text[t])
    with open(out / "records_changed.jsonl", "w") as fh:
        for t in changed:
            fh.write(json.dumps(mem.records[t], default=str) + "\n")
    rc = t384.run_acceptance(V4_DIR, YF_DIR, out / "acceptance", candidate=mem.candidate,
                             extra_steps=mem.changes_for, labels=mem.labels_for)
    s = json.loads((out / "acceptance" / "summary.json").read_text())
    v5 = json.loads((T390_DIR / "acceptance_v5_alone" / "summary.json").read_text())
    rep = {
        "table_sha256": table.sha256, "unverified_sha256": table.unverified_sha256, "n_rows": table.n_rows,
        "files": len(mem.written), "files_that_differ_from_v5": changed,
        "byte_identity": {"t390_tier1_files": len(t390["changed"]), "equal_to_t390_render": len(ident_changed),
                          "other_files": len(others), "equal_to_v5_and_t390_render": len(ident_v5),
                          "not_identical": sorted(set(mem.written) - set(ident_changed) - set(ident_v5))},
        "write_time_rails_failed": mem.rails_failed,
        "acceptance": {"verdict": s["verdict"], "verdict_v5": v5["verdict"],
                       "i_fail": s["i"]["fail"], "i_fail_v5": v5["i"]["fail"],
                       "i_pass_strict": s["i"]["pass_strict"], "i_pass_strict_v5": v5["i"]["pass_strict"],
                       "ii_years_pass": int(sum(v["pass"] for v in s["ii"]["by_year"].values())),
                       "ii_years_pass_v5": int(sum(v["pass"] for v in v5["ii"]["by_year"].values())),
                       "iii": s["iii"], "iii_v5": v5["iii"], "iii_c": s["iii_c"], "iv": s["iv"],
                       "step_audit": s["step_audit"], "step_audit_v5": v5["step_audit"]},
        "acceptance_csvs_equal_t390_tier1_run": _csv_equal(out / "acceptance", T390_DIR / "acceptance_tier1"),
        "acceptance_csvs_equal_v5_alone": _csv_equal(out / "acceptance", T390_DIR / "acceptance_v5_alone"),
    }
    (out / "measure.json").write_text(json.dumps(rep, indent=2, default=str))
    print(json.dumps(rep, indent=2, default=str))
    ok = (not rep["byte_identity"]["not_identical"] and not mem.rails_failed
          and all(rep["acceptance_csvs_equal_t390_tier1_run"].values()))
    return rc if not ok else 0 if rc in (0,) else rc


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
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export-table", help="write the two pinned config files from T-390's v5-based table")
    e.add_argument("--table", default=str(T390_DIR / "corrections.parquet"))
    e.set_defaults(func=cmd_export_table)
    r = sub.add_parser("run", help="rebuild in memory with the pinned table; compare with T-390's render; acceptance")
    r.add_argument("--out", default=str(DEFAULT_OUT))
    r.set_defaults(func=cmd_run)
    m = sub.add_parser("manifest", help="md5 of every file under --out")
    m.add_argument("--out", default=str(DEFAULT_OUT))
    m.set_defaults(func=cmd_manifest)
    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
