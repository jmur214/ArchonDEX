"""Paper-run diagnostics — pure-pandas/stdlib loaders for the Paper tab (T-182).

READ-ONLY. This module reads the going-live paper run's persisted outputs and
the integrity/measurement artifacts that gate it. It NEVER trades, submits, or
mutates state — it surfaces what already happened.

The session theme is *"silent gaps must be VISIBLE."* Most paper-run data is
NOT persisted yet (the live loop currently writes to an ephemeral
``tempfile.mkdtemp()`` — see ``scripts/run_paper_day_t163.py``). Every loader
here returns a clearly-typed "pending / no data yet" state when its source is
absent, so a panel can render a visible gap instead of crashing or blanking.

Whitelisted engine imports (data-processing only, no real-money path):
  * ``core.census.assert_census_file``        — the shared integrity gate
  * ``core.combined_candidate_scorecard``      — the base-vs-robo deploy bar

Everything else is pandas + stdlib.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from core.census import assert_census_file, CensusVerdict

# --------------------------------------------------------------------- #
# Paths (all relative to the repo CWD — matches capital_allocation_loader)
# --------------------------------------------------------------------- #
DATA_DIR = Path("data")
TRADE_LOGS_DIR = DATA_DIR / "trade_logs"
# Persistent paper-run state. T-191 repoint: the T-185 persistence layer
# writes the JSONL belief/journal/recon to data/paper_state/ and the
# dead-man's-switch heartbeat to data/state/paper_heartbeat.json (NOT the
# guessed data/paper/latest/). Absent → loaders degrade to "no paper run yet".
PAPER_DIR = DATA_DIR / "paper_state"
HEARTBEAT_PATH = DATA_DIR / "state" / "paper_heartbeat.json"
SCORECARD_DOC = Path("docs") / "State" / "paper_run_scorecard.md"


# --------------------------------------------------------------------- #
# 1) Census — the integrity signal
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class CensusResult:
    """Outcome of the newest census-bearing run, or a "none found" state."""
    found: bool
    path: Optional[str]
    census: dict = field(default_factory=dict)
    canonical: bool = False
    census_present: bool = False
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mtime: float = 0.0


def _newest_census_summary() -> Optional[Path]:
    """Find the newest performance_summary.json that has a NON-EMPTY census
    block. Returns None if none exists (most summaries predate the census
    layer)."""
    if not TRADE_LOGS_DIR.exists():
        return None
    candidates: list[tuple[float, Path]] = []
    for child in TRADE_LOGS_DIR.iterdir():
        if not child.is_dir():
            continue
        summ = child / "performance_summary.json"
        if not summ.exists() or summ.stat().st_size == 0:
            continue
        try:
            raw = json.loads(summ.read_text())
        except Exception:
            continue
        census = raw.get("census")
        if isinstance(census, dict) and census:
            candidates.append((summ.stat().st_mtime, summ))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]


@lru_cache(maxsize=1)
def _load_census_cached(_token: float) -> CensusResult:
    """Cache keyed on the newest-summary mtime token so the pulse interval
    doesn't re-walk + re-parse every 2s; recomputes only when a newer
    census-bearing run lands."""
    path = _newest_census_summary()
    if path is None:
        return CensusResult(found=False, path=None)
    try:
        raw = json.loads(path.read_text())
    except Exception as exc:
        return CensusResult(found=False, path=str(path),
                            failures=[f"cannot read summary: {exc!r}"])
    verdict: CensusVerdict = assert_census_file(str(path))
    return CensusResult(
        found=True,
        path=str(path),
        census=raw.get("census", {}) or {},
        canonical=bool(verdict.canonical),
        census_present=bool(verdict.census_present),
        failures=list(verdict.failures),
        warnings=list(verdict.warnings),
        mtime=path.stat().st_mtime,
    )


def load_census() -> CensusResult:
    """Public entry: newest census-bearing run + its canonical verdict.

    Never raises. Returns ``found=False`` when no census-bearing run exists.
    """
    path = _newest_census_summary()
    token = path.stat().st_mtime if path is not None else 0.0
    return _load_census_cached(token)


# --------------------------------------------------------------------- #
# 2) Paper ledger / orders / reconcile status
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class PaperRunStatus:
    persisted: bool
    paper_dir: str
    last_modified: Optional[str] = None
    cash: Optional[float] = None
    realized_pnl: Optional[float] = None
    n_positions: int = 0
    positions: dict = field(default_factory=dict)
    n_open_orders: int = 0
    last_reconcile_clean: Optional[bool] = None
    n_reconcile_cycles: int = 0
    reconcile_clean_cycles: int = 0
    seq: Optional[int] = None
    note: str = ""


def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file → list of dicts. Skips malformed lines (a malformed
    last line is the documented crash-recovery scenario). [] if missing."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    out: list[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def load_paper_run(paper_dir: Path = PAPER_DIR) -> PaperRunStatus:
    """Load the persisted paper run's ledger/orders/recon status.

    Degrades to ``persisted=False`` when no paper-run dir exists (the common
    case — the live loop currently writes to an ephemeral tempdir). Equity is
    intentionally NOT synthesised: we have no live prices, so we report cash +
    position count + realized_pnl + reconcile state and let the view label the
    gap honestly.
    """
    ledger_path = paper_dir / "ledger.jsonl"
    orders_path = paper_dir / "orders.jsonl"
    recon_path = paper_dir / "recon.jsonl"

    # T-191: the heartbeat (data/state/paper_heartbeat.json) is the per-run
    # dead-man's-switch summary the T-185 loop writes EVEN on dry-run / flat
    # days (when no ledger fill is appended). Read it first so the tab shows
    # "the loop ran today, canonical" even before any fill lands.
    hb = {}
    try:
        if HEARTBEAT_PATH.exists():
            hb = json.loads(HEARTBEAT_PATH.read_text()).get("last_run", {}) or {}
    except Exception:
        hb = {}

    if not paper_dir.exists() or not ledger_path.exists():
        if hb:
            return PaperRunStatus(
                persisted=True,
                paper_dir=str(paper_dir),
                last_modified=hb.get("run_ts"),
                n_reconcile_cycles=int(hb.get("reconcile_total_cycles", 0) or 0),
                reconcile_clean_cycles=int(hb.get("reconcile_clean_cycles", 0) or 0),
                last_reconcile_clean=(int(hb.get("reconcile_clean_cycles", 0) or 0)
                                      == int(hb.get("reconcile_total_cycles", 0) or 0)
                                      and int(hb.get("reconcile_total_cycles", 0) or 0) > 0) or None,
                note=f"Heartbeat {hb.get('run_date','?')}: canonical={hb.get('canonical')}, "
                     f"submitted={hb.get('submitted')}, fills={hb.get('fills')}, "
                     f"account_flat={hb.get('account_flat')} — no ledger fills yet (flat/dry day).",
            )
        return PaperRunStatus(
            persisted=False,
            paper_dir=str(paper_dir),
            note="No paper run persisted yet — neither data/paper_state/ledger.jsonl "
                 "nor data/state/paper_heartbeat.json found.",
        )

    ledger = _read_jsonl(ledger_path)
    orders = _read_jsonl(orders_path)
    recon = _read_jsonl(recon_path)

    last_ledger = ledger[-1] if ledger else {}
    positions = last_ledger.get("positions", {}) or {}
    # count only non-flat positions
    open_positions = {t: p for t, p in positions.items()
                      if isinstance(p, dict) and int(p.get("qty", 0) or 0) != 0}

    # open orders = journal entries not in a terminal state
    terminal = {"filled", "canceled", "cancelled", "rejected", "expired", "done"}
    open_orders = [o for o in orders
                   if str(o.get("state", o.get("status", ""))).lower() not in terminal]

    clean_cycles = sum(1 for r in recon if bool(r.get("clean")))
    last_clean = bool(recon[-1].get("clean")) if recon else None

    try:
        mtime = ledger_path.stat().st_mtime
        last_mod = pd.Timestamp(mtime, unit="s").strftime("%Y-%m-%d %H:%M")
    except Exception:
        last_mod = None

    return PaperRunStatus(
        persisted=True,
        paper_dir=str(paper_dir),
        last_modified=last_mod,
        cash=float(last_ledger["cash"]) if "cash" in last_ledger else None,
        realized_pnl=float(last_ledger.get("realized_pnl", 0.0)) if last_ledger else None,
        n_positions=len(open_positions),
        positions=open_positions,
        n_open_orders=len(open_orders),
        last_reconcile_clean=last_clean,
        n_reconcile_cycles=len(recon),
        reconcile_clean_cycles=clean_cycles,
        seq=int(last_ledger["seq"]) if "seq" in last_ledger else None,
    )


# --------------------------------------------------------------------- #
# 3) §5 scorecard — parsed from the markdown doc
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class ScorecardCriteria:
    found: bool
    doc_path: str
    rows: list[dict] = field(default_factory=list)  # {metric, target, status, verdict}
    as_of: str = ""


_PASS = "PASS"
_PENDING = "PENDING"
_FAIL = "FAIL"


def _classify_scorecard_row(metric: str, target: str, status: str) -> str:
    """Heuristic verdict from a parsed (metric, target, status) row.

    Deliberately SIMPLE and clearly labelled in the UI as "parsed from the
    scorecard doc" — this is a doc-mirror, not a recomputation.
      * empty / 'pending' / '—' status   → PENDING
      * a "must be 0 / 0 violations" target met by a 0 status → PASS
      * a numeric target with the status numerically satisfying it → PASS
      * otherwise → PENDING (we don't assert FAIL from a doc parse)
    """
    s = (status or "").strip().lower()
    t = (target or "").strip().lower()

    if not s or "pending" in s or s in {"—", "-", "n/a", "tbd", "shadow"}:
        return _PENDING

    # pull the first number out of status and target (strip bold/markup)
    def _first_num(text: str) -> Optional[float]:
        m = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
        return float(m.group()) if m else None

    s_num = _first_num(s)
    t_num = _first_num(t)

    # "0" / "zero violations / drifts" style targets
    if t_num is not None and t_num == 0:
        if s_num is not None and s_num == 0:
            return _PASS
        if s_num is not None and s_num > 0:
            return _PENDING  # a doc-parsed nonzero on a "must be 0" → flag amber, not red
        return _PENDING

    # "≥ N" target (duration, fills, clean-rate)
    if (">=" in t or "≥" in t) and s_num is not None and t_num is not None:
        return _PASS if s_num >= t_num else _PENDING
    # "≤ N" target (slippage, false-alarms, missed-cycle)
    if ("<=" in t or "≤" in t) and s_num is not None and t_num is not None:
        return _PASS if s_num <= t_num else _PENDING

    # percentage clean-rate special-case ("100%" status vs "≥99%" target)
    if s_num is not None and t_num is not None and "%" in s:
        return _PASS if s_num >= t_num else _PENDING

    return _PENDING


def load_scorecard_criteria(doc_path: Path = SCORECARD_DOC) -> ScorecardCriteria:
    """Parse the §5 metric table out of the paper-run scorecard markdown.

    Looks for the pipe table whose header contains 'metric' and 'target' and
    parses each data row into {metric, target, status, verdict}. Degrades to
    ``found=False`` when the doc or table is absent.
    """
    if not doc_path.exists():
        return ScorecardCriteria(found=False, doc_path=str(doc_path))

    text = doc_path.read_text()
    lines = text.splitlines()

    # find the header row of the metric|target|status table
    header_idx = None
    as_of = ""
    for i, line in enumerate(lines):
        low = line.lower()
        if line.lstrip().startswith("|") and "metric" in low and "target" in low:
            header_idx = i
            # try to grab an "as of" stamp from the status header cell
            m = re.search(r"\((day\s*\d+[^)]*)\)", line, re.IGNORECASE)
            if m:
                as_of = m.group(1).strip()
            break

    if header_idx is None:
        return ScorecardCriteria(found=False, doc_path=str(doc_path))

    rows: list[dict] = []
    # data rows start two lines down (skip the |---|---| separator)
    for line in lines[header_idx + 2:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break  # table ended
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 3:
            continue
        metric, target, status = cells[0], cells[1], cells[2]
        # strip markdown bold from status
        status_clean = status.replace("**", "").strip()
        rows.append({
            "metric": metric.replace("**", "").strip(),
            "target": target.strip(),
            "status": status_clean,
            "verdict": _classify_scorecard_row(metric, target, status_clean),
        })

    return ScorecardCriteria(found=bool(rows), doc_path=str(doc_path),
                             rows=rows, as_of=as_of)


# --------------------------------------------------------------------- #
# 4) Equity vs robo — combined-candidate scorecard
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class EquityVsRobo:
    found: bool
    base_source: str            # human-readable provenance of the base series
    is_backtest_base: bool      # True → "(backtest base — paper pending)" label
    blocks: dict = field(default_factory=dict)  # {robo_name: [row_dict, ...]}
    note: str = ""


def _paper_equity_series(paper_dir: Path) -> Optional[pd.Series]:
    """Prefer the persisted paper equity curve (data/paper/latest/equity.csv,
    columns date,equity). None if absent."""
    p = paper_dir / "equity.csv"
    if not p.exists() or p.stat().st_size == 0:
        return None
    try:
        df = pd.read_csv(p)
    except Exception:
        return None
    cols = {c.lower(): c for c in df.columns}
    date_c = cols.get("date") or cols.get("timestamp")
    eq_c = cols.get("equity") or cols.get("value")
    if not date_c or not eq_c:
        return None
    idx = pd.to_datetime(df[date_c], errors="coerce")
    s = pd.Series(pd.to_numeric(df[eq_c], errors="coerce").values, index=idx).dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s if len(s) > 5 else None


def _newest_backtest_equity() -> Optional[tuple[pd.Series, str]]:
    """Fallback base: newest trade_logs/<uuid>/portfolio_snapshots.csv, grouped
    by timestamp-date → last equity. Returns (series, run_uuid) or None.

    portfolio_snapshots.csv is not present in every run (it postdates some
    backtests) — degrade to None if no run has one.
    """
    if not TRADE_LOGS_DIR.exists():
        return None
    candidates: list[tuple[float, Path]] = []
    for child in TRADE_LOGS_DIR.iterdir():
        snap = child / "portfolio_snapshots.csv"
        if snap.exists() and snap.stat().st_size > 0:
            candidates.append((snap.stat().st_mtime, snap))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0], reverse=True)
    snap = candidates[0][1]
    try:
        df = pd.read_csv(snap)
    except Exception:
        return None
    cols = {c.lower(): c for c in df.columns}
    ts_c = cols.get("timestamp") or cols.get("date")
    eq_c = cols.get("equity") or cols.get("value") or cols.get("portfolio_value")
    if not ts_c or not eq_c:
        return None
    df["_d"] = pd.to_datetime(df[ts_c], errors="coerce").dt.date
    df = df.dropna(subset=["_d"])
    grouped = df.groupby("_d")[eq_c].last()
    s = pd.Series(grouped.values, index=pd.to_datetime(grouped.index)).dropna()
    if len(s) <= 5:
        return None
    return s, snap.parent.name


@lru_cache(maxsize=4)
def _build_blocks_cached(_token: str, source_path: str, n_boot: int) -> dict:
    """Cache the (slow) bootstrap scorecard keyed on source-file mtime token, so
    the 2s pulse interval doesn't recompute the block-bootstrap every tick."""
    from core.combined_candidate_scorecard import build_scorecard, rows_to_dicts
    s = _read_series_for_scorecard(source_path)
    if s is None or len(s) < 30:
        return {}
    blocks = build_scorecard(s, n_boot=n_boot)
    return rows_to_dicts(blocks)


def _read_series_for_scorecard(source_path: str) -> Optional[pd.Series]:
    """Re-read a base series from its source path (used inside the lru cache,
    which can only take hashable args)."""
    p = Path(source_path)
    if not p.exists():
        return None
    if p.name == "equity.csv":
        return _paper_equity_series(p.parent)
    # portfolio_snapshots.csv
    try:
        df = pd.read_csv(p)
    except Exception:
        return None
    cols = {c.lower(): c for c in df.columns}
    ts_c = cols.get("timestamp") or cols.get("date")
    eq_c = cols.get("equity") or cols.get("value") or cols.get("portfolio_value")
    if not ts_c or not eq_c:
        return None
    df["_d"] = pd.to_datetime(df[ts_c], errors="coerce").dt.date
    df = df.dropna(subset=["_d"])
    grouped = df.groupby("_d")[eq_c].last()
    s = pd.Series(grouped.values, index=pd.to_datetime(grouped.index)).dropna()
    return s if len(s) > 5 else None


def load_equity_vs_robo(paper_dir: Path = PAPER_DIR, n_boot: int = 300) -> EquityVsRobo:
    """Build the base / base+20%DBMF / robo scorecard for each pre-registered
    proxy.

    Base series priority:
      1. data/paper/latest/equity.csv (real paper returns) → live label
      2. newest backtest portfolio_snapshots.csv           → "(backtest base —
         paper pending)" label
      3. neither → ``found=False`` pending state

    Slow (block-bootstrap); cached by source mtime + a small n_boot so the
    pulse doesn't recompute every tick.
    """
    paper_s = _paper_equity_series(paper_dir)
    if paper_s is not None:
        source_path = str(paper_dir / "equity.csv")
        token = f"{source_path}:{(paper_dir / 'equity.csv').stat().st_mtime}"
        try:
            blocks = _build_blocks_cached(token, source_path, n_boot)
        except Exception as exc:
            return EquityVsRobo(found=False, base_source="paper equity.csv",
                                is_backtest_base=False,
                                note=f"scorecard error: {exc!r}")
        return EquityVsRobo(
            found=bool(blocks),
            base_source=f"data/paper/latest/equity.csv ({len(paper_s)} days)",
            is_backtest_base=False,
            blocks=blocks,
            note="" if blocks else "paper equity too short for a scorecard window.",
        )

    fallback = _newest_backtest_equity()
    if fallback is None:
        return EquityVsRobo(
            found=False, base_source="(none)", is_backtest_base=True,
            note="No paper equity persisted and no backtest "
                 "portfolio_snapshots.csv found — base series unavailable.",
        )
    series, run_uuid = fallback
    source_path = str(TRADE_LOGS_DIR / run_uuid / "portfolio_snapshots.csv")
    token = f"{source_path}:{Path(source_path).stat().st_mtime}"
    try:
        blocks = _build_blocks_cached(token, source_path, n_boot)
    except Exception as exc:
        return EquityVsRobo(found=False, base_source=f"backtest {run_uuid[:8]}",
                            is_backtest_base=True, note=f"scorecard error: {exc!r}")
    return EquityVsRobo(
        found=bool(blocks),
        base_source=f"backtest {run_uuid[:8]}… portfolio_snapshots.csv ({len(series)} days)",
        is_backtest_base=True,
        blocks=blocks,
        note="" if blocks else "base series too short for a scorecard window.",
    )
