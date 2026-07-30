"""Fail-open alt-data + positioning archiving for the daily cloud pulse
(T-2026-07-07-290 deliverable 1).

The two T-136 archivers (``scripts/archive_altdata_t136`` — GPR/EPU/GDELT/
Polymarket/Kalshi/KXFED/FRED — and ``scripts/archive_positioning_t136`` —
FINRA/SEC/NAAIM) run daily on the local Mac via launchd. This module folds
the SAME pulls into the cloud paper pulse (``scripts/run_paper_cloud_day``)
as a POST-reconcile step so the alt-data hoard also accrues in the cloud, is
persisted durably to S3 (the ``altdata/`` prefix), and surfaces its health in
the heartbeat the dashboard reads.

TWO hard invariants:

  1. **Fail-open for trading.** Every pull is individually try/excepted and
     the whole run is called AFTER reconcile/tracking. A network failure,
     a changed endpoint, an import error — none of it may raise into the
     trading path or change the run's canonical verdict. Alt-data is not
     load-bearing for orders.

  2. **A zero-snapshot day flags LOUDLY.** The parquet archivers DEDUP, so a
     silently-broken API (GDELT already 503s intermittently; a Kalshi auth
     flip) leaves the parquet the SAME size on disk — indistinguishable from
     a healthy no-change day. We defeat that by counting rows STAMPED with
     TODAY's ``snap_date`` in the 24/7 market-snapshot sources. Zero fresh
     rows across ALL of them = ``degraded=True`` → the heartbeat's separate
     alt-data alert channel fires. (Positioning sources lag / gap on
     weekends — accepted — so they do not gate degradation.)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import pandas as pd

# The 24/7 market-snapshot sources that MUST land today's rows on any run day.
# (source_label, parquet relative path, the date column stamped with snap_date)
_SNAPSHOT_FRESHNESS: List[Tuple[str, str, str]] = [
    ("kalshi", "data/macro_data/alt/kalshi_snapshots.parquet", "snap_date"),
    ("kxfed", "data/macro_data/alt/kalshi_kxfed_snapshots.parquet", "snap_date"),
    ("polymarket", "data/macro_data/alt/polymarket_snapshots.parquet", "snap_date"),
    # T-334: the CEF panel is a DAILY snapshot with the same silent-breakage risk
    # (parquet dedup hides a dead endpoint). Form4/USASpending are NOT gated here:
    # both legitimately gap (weekends/holidays, award-posting lag), so a zero day
    # for them is not evidence of breakage — their counts are reported per-run.
    ("cef", "data/macro_data/alt/cef_daily.parquet", "snap_date"),
]


@dataclass
class AltdataArchiveResult:
    ran: bool
    degraded: bool
    reason: str
    reports: List[str] = field(default_factory=list)     # per-source human lines
    fresh_rows: Dict[str, int] = field(default_factory=dict)  # snapshot source -> today's rows


def _fresh_rows(path: Path, datecol: str, today: str) -> int:
    """Rows in ``path`` stamped with ``today`` in ``datecol``. Missing file /
    unreadable parquet ⇒ 0 (which — for a snapshot source — reads as broken)."""
    try:
        df = pd.read_parquet(path, columns=[datecol])
        return int((df[datecol].astype(str) == today).sum())
    except Exception:
        return 0


def run_altdata_archive(root: str, *, days_back: int = 10) -> AltdataArchiveResult:
    """Run both T-136 archivers (each pull fail-open) and assess snapshot
    freshness. Never raises into the caller — the trading path stays clean."""
    root_p = Path(root)
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    reports: List[str] = []

    # Import lazily so a broken archiver import can't take down the driver's
    # module load; both self-root their OUT_DIR to the repo root.
    def _run_group(tag: str, jobs: List[Tuple[str, Callable[[], str]]]) -> None:
        for name, fn in jobs:
            try:
                reports.append(f"[{tag}] {name}: {fn()}")
            except Exception as exc:            # fail-open per source
                reports.append(f"[{tag}] {name}: FAILED ({type(exc).__name__}: {exc})")

    try:
        import scripts.archive_altdata_t136 as ad
        _run_group("D", [
            ("gpr", ad.pull_gpr), ("epu", ad.pull_epu),
            ("gdelt", ad.pull_gdelt_timelines),
            ("polymarket", ad.snapshot_polymarket),
            ("kalshi", ad.snapshot_kalshi),
            ("kxfed", ad.snapshot_kxfed),               # T-290 d2 rate-path
            ("fred_rate_path", ad.pull_fred_rate_path),  # T-290 d2 resolution
            ("cef", ad.snapshot_cef),                     # T-334 CEF discount panel
            ("form4", ad.pull_form4_index),               # T-334 EDGAR Form 4 index
            ("usaspending", ad.pull_usaspending),         # T-334 federal awards
        ])
    except Exception as exc:
        reports.append(f"[D] archive_altdata import FAILED ({type(exc).__name__}: {exc})")

    try:
        import scripts.archive_positioning_t136 as ap
        _run_group("C", [
            ("regsho", lambda: ap.pull_regsho_short_volume(days_back)),
            ("ftd", ap.pull_sec_ftd),
            ("naaim", ap.pull_naaim),
            ("margin", ap.pull_finra_margin),
            ("short_interest", ap.pull_finra_short_interest),
        ])
    except Exception as exc:
        reports.append(f"[C] archive_positioning import FAILED ({type(exc).__name__}: {exc})")

    # --- freshness: dedup hides silent breakage, so count TODAY-stamped rows in
    # the 24/7 snapshot sources. Zero across all of them = degraded (LOUD). ---
    fresh_rows: Dict[str, int] = {
        src: _fresh_rows(root_p / rel, col, today)
        for src, rel, col in _SNAPSHOT_FRESHNESS
    }
    landed = sum(1 for v in fresh_rows.values() if v > 0)
    degraded = landed == 0
    if degraded:
        reason = (f"ZERO market-snapshot rows landed for {today} across "
                  f"{list(fresh_rows)} — silent API breakage (dedup hides it "
                  f"on disk); {fresh_rows}")
    else:
        reason = f"{landed}/{len(fresh_rows)} snapshot sources fresh for {today}: {fresh_rows}"
    return AltdataArchiveResult(ran=True, degraded=degraded, reason=reason,
                                reports=reports, fresh_rows=fresh_rows)
