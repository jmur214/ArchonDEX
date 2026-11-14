"""T-394 — the PINNED Tier-1 Stooq corrections the cutover writer applies, and the Tier-2 LABEL it carries.

Pre-declared in `docs/Sources/proposal_era_tr_tier1_wiring_t394_2026-11-14.md` §1 (committed alone first).

TIER 1 (`config/stooq_corrections_tier1.json`): exactly the 11 rows of T-390's corrections table (rebuilt on v5,
`docs/Sources/proposal_stooq_repair_t390_2026-11-13.md` §11) that T-265 covers and agrees with — 7 spin-off
steps Stooq left unapplied and 4 one-bar blocks. They are APPLIED by `tr_writer.era_tr_rewrite` through
`era_tr.build_file(changes=…)`.

TIER 2 (`config/stooq_corrections_unverified.json`): 1,579 rows on 374 files, yfinance-derived and UNVERIFIED,
plus three known omissions. They are NEVER applied. A file's entry is copied into its write record as
`unverified_stooq_corrections`, and the convention census reads it back.

Both files are pinned by sha256 CONSTANTS in this module: a file that does not hash to its constant is refused
before any price file is read. Nothing here derives a row; a row is data, checked against the file it names.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
TIER1_PATH = REPO / "config" / "stooq_corrections_tier1.json"
UNVERIFIED_PATH = REPO / "config" / "stooq_corrections_unverified.json"
#: The pins. Changing a table means changing its constant in the same commit, under review.
TIER1_SHA256 = "fa53978cc9bfba593e93f88df6996a4c4fdcf4bd53f56717a061aeeaf2905d30"
UNVERIFIED_SHA256 = "60902ac0514986fac900ffa339c11ca800952ae36a14d13a652d87ab47e58d47"
N_TIER1_ROWS = 11
KIND_STEP, KIND_BLOCK = "spinoff_step", "block"
GUARD_BARS = 3                 # a row this close to an ex-date the writer's guard touched is refused


class StooqTier1Refusal(RuntimeError):
    """The pinned corrections cannot be applied as given (fail closed; nothing is written)."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class Tier1Table:
    """The pinned table as loaded: rows per file, and the Tier-2 label per file."""
    sha256: str
    rows: Dict[str, List[dict]]
    unverified_sha256: str
    unverified: Dict[str, dict] = field(default_factory=dict)
    known_unapplied: Dict[str, List[dict]] = field(default_factory=dict)

    @property
    def n_rows(self) -> int:
        return sum(len(v) for v in self.rows.values())

    def rows_for(self, ticker: str) -> List[dict]:
        return list(self.rows.get(ticker, []))

    def unverified_for(self, ticker: str) -> dict:
        """The file's Tier-2 label: counts and spans of the corrections NOT applied, and its known omissions.
        Always a dict — zero counts say "the label file names nothing for this file"."""
        u = self.unverified.get(ticker, {})
        return {"n_steps": int(u.get("n_steps", 0)), "n_blocks": int(u.get("n_blocks", 0)),
                "steps": list(u.get("steps", [])), "blocks": [list(b) for b in u.get("blocks", [])],
                "known_unapplied": list(self.known_unapplied.get(ticker, [])),
                "label_sha256": self.unverified_sha256,
                "meaning": "yfinance-derived corrections T-390 found and T-265 cannot check: NOT applied"}


def load_tier1(path: Path = TIER1_PATH, expected_sha256: str = TIER1_SHA256,
               unverified_path: Path = UNVERIFIED_PATH, unverified_sha256: str = UNVERIFIED_SHA256) -> Tier1Table:
    """Both pinned files, or REFUSE: a missing file, a sha256 that is not the pin, a row count that is not 11,
    an unknown kind, or two rows for one file and date."""
    for p, want, name in ((path, expected_sha256, "Tier-1 table"), (unverified_path, unverified_sha256, "Tier-2 label file")):
        if not Path(p).exists():
            raise StooqTier1Refusal(f"the {name} {p} is absent")
        got = _sha256(p)
        if got != want:
            raise StooqTier1Refusal(f"the {name} {p} has sha256 {got}, not the pinned {want} — refused")
    doc = json.loads(Path(path).read_text())
    rows: Dict[str, List[dict]] = {}
    seen = set()
    for r in doc["rows"]:
        if r["kind"] not in (KIND_STEP, KIND_BLOCK):
            raise StooqTier1Refusal(f"{r['ticker']} {r['date']}: unknown kind {r['kind']!r}")
        if r["kind"] == KIND_BLOCK and not r.get("end_date"):
            raise StooqTier1Refusal(f"{r['ticker']} {r['date']}: a block row with no end date")
        key = (r["ticker"], r["date"])
        if key in seen:
            raise StooqTier1Refusal(f"{r['ticker']} {r['date']}: two rows for one file and date")
        seen.add(key)
        rows.setdefault(r["ticker"], []).append(dict(r))
    if len(seen) != N_TIER1_ROWS:
        raise StooqTier1Refusal(f"the Tier-1 table holds {len(seen)} rows, not {N_TIER1_ROWS}")
    lab = json.loads(Path(unverified_path).read_text())
    return Tier1Table(sha256=_sha256(path), rows=rows, unverified_sha256=_sha256(unverified_path),
                      unverified=lab.get("tier2", {}), known_unapplied=lab.get("known_unapplied", {}))


def check_universe(table: Tier1Table, merged_files: Iterable[str]) -> None:
    """Every row must name a merged file with pre-seam bars — checked for the WHOLE table before any write."""
    missing = sorted(set(table.rows) - set(merged_files))
    if missing:
        raise StooqTier1Refusal(f"Tier-1 rows name files that are not merged files with pre-seam bars: {missing}")


def changes_for_file(ticker: str, rows: List[dict], dates: pd.DatetimeIndex, seam: pd.Timestamp,
                     guard_days: Optional[pd.DatetimeIndex] = None) -> pd.Series:
    """One file's rows as (date → change of the daily log return on that bar), or REFUSE.

    A step of log amount s at e raises the return into e by −s (every earlier bar × exp(s)); a block of offset
    δ over [a, b) changes the return into a by −δ and into b by +δ. `dates` are the file's bars (pre-seam and
    post-seam); `guard_days` are the ex-dates the writer's distribution guard refused or repaired in this file.
    Refused: a date that is not a bar; a row on or after the seam, or a block ending after it; a row within
    GUARD_BARS bars of a guard day."""
    dates = pd.DatetimeIndex(dates)
    seam = pd.Timestamp(seam)
    guard_pos = (dates.get_indexer(pd.DatetimeIndex(guard_days)) if guard_days is not None and len(guard_days)
                 else np.zeros(0, dtype=int))
    out: Dict[pd.Timestamp, float] = {}
    for r in rows:
        d = pd.Timestamp(r["date"])
        amount = float(r["log_amount"])
        if not np.isfinite(amount) or amount == 0.0:
            raise StooqTier1Refusal(f"{ticker} {r['date']}: the row's amount {r['log_amount']!r} is not a correction")
        pos = dates.get_indexer([d])[0]
        if pos < 0:
            raise StooqTier1Refusal(f"{ticker} {r['date']}: not a bar of the file")
        if d >= seam:
            raise StooqTier1Refusal(f"{ticker} {r['date']}: on or after the seam {seam.date()} — it would land "
                                    f"outside the pre-seam span")
        if len(guard_pos) and (np.abs(guard_pos[guard_pos >= 0] - pos) <= GUARD_BARS).any():
            raise StooqTier1Refusal(f"{ticker} {r['date']}: within {GUARD_BARS} bars of an ex-date the writer's "
                                    f"distribution guard refused or repaired — the two must never act on one event")
        if r["kind"] == KIND_STEP:
            out[d] = out.get(d, 0.0) - amount
            continue
        b = pd.Timestamp(r["end_date"])
        if dates.get_indexer([b])[0] < 0:
            raise StooqTier1Refusal(f"{ticker} {r['date']}: the block's end {r['end_date']} is not a bar of the file")
        if b > seam or b <= d:
            raise StooqTier1Refusal(f"{ticker} {r['date']}: the block's end {r['end_date']} is after the seam "
                                    f"{seam.date()} or not after its start")
        out[d] = out.get(d, 0.0) - amount
        out[b] = out.get(b, 0.0) + amount
    return pd.Series(out, dtype=float).sort_index()
