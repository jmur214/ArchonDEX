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

from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Callable, Dict, Iterator, List, Optional, Tuple

import pandas as pd

# Where each archiver writes, RELATIVE to a state root — the same two directories
# cloud_state.ALTDATA_DIRS pulls and pushes, and the freshness tables below read.
ALT_REL = "data/macro_data/alt"
POSITIONING_REL = "data/positioning"

# The 24/7 market-snapshot sources that MUST land today's rows on any run day.
# (source_label, parquet relative path, the date column stamped with snap_date)
_SNAPSHOT_FRESHNESS: List[Tuple[str, str, str]] = [
    ("kalshi", "data/macro_data/alt/kalshi_snapshots.parquet", "snap_date"),
    ("kxfed", "data/macro_data/alt/kalshi_kxfed_snapshots.parquet", "snap_date"),
    ("polymarket", "data/macro_data/alt/polymarket_snapshots.parquet", "snap_date"),
    # Form4/USASpending are NOT gated here: both legitimately gap (weekends/holidays,
    # award-posting lag), so a zero day for them is not evidence of breakage — their
    # counts are reported per-run.
    # The T-334 CEF panel was RETIRED from this list 2026-11-19: its source has failed on
    # every pull since 2026-10-19 and its only consumer (T-379) closed the CEF thread, so
    # it made the local verifier exit 1 and page every day — an alarm that cries wolf.
    # See `_RETIRED_CEF` below; un-retire only with a consumer AND a working source.
]

_RETIRED_CEF = ("RETIRED 2026-11-19: the CEF source has failed on every pull since 2026-10-19 "
                "(JSONDecodeError — the endpoint no longer serves JSON); its only consumer, "
                "the T-379 probe, closed the CEF thread on free data; the banked rows to "
                "2026-10-19 are retained in cef_daily.parquet. Un-exempt only with a "
                "consumer AND a working source.")


# --- T-335: the DURABLE close of the silent-stop class -----------------------
# GDELT died silently because it sat OUTSIDE the gated set. The fix is not "add GDELT"
# (it is retired) but "no archiver outside the gate". A naive today's-rows gate would
# false-alarm on weekly/monthly feeds — and alarm fatigue is precisely how the July
# outage went unread — so each feed declares its OWN staleness budget from its real
# publication cadence. A feed whose dates cannot be PARSED is also a failure: you
# cannot monitor what you cannot age.
# (name, relpath, datecol, max_age_days, fmt, exempt_reason)
# exempt_reason != None => LOCAL-ONLY Phase-A feed: reported as EXEMPT with the
# reason, never as staleness. The gate's job is to DECLARE what the cloud actually
# collects; silently failing a feed the cloud was never going to collect is the
# false-alarm class that produces alarm fatigue (director ruling 2026-08-15).
_FEED_HEALTH: List[Tuple[str, str, str, int, str, Optional[str]]] = [
    # daily market snapshots (weekend tolerance)
    ("kalshi", "data/macro_data/alt/kalshi_snapshots.parquet", "snap_date", 4, "iso", None),
    ("kxfed", "data/macro_data/alt/kalshi_kxfed_snapshots.parquet", "snap_date", 4, "iso", None),
    ("polymarket", "data/macro_data/alt/polymarket_snapshots.parquet", "snap_date", 4, "iso", None),
    ("cef", "data/macro_data/alt/cef_daily.parquet", "snap_date", 4, "iso", _RETIRED_CEF),
    # daily-ish constructed series / resolution feeds
    ("epu_daily", "data/macro_data/alt/epu_daily_us.parquet", "archive_vintage", 7, "iso", None),
    ("gpr_daily", "data/macro_data/alt/gpr_daily_recent.parquet", "archive_vintage", 7, "iso",
     "local-only Phase-A; legacy .xls needs xlrd (absent from the lean image); no cloud consumer"),
    ("fred_rate_path", "data/macro_data/alt/fred_rate_path.parquet", "observation_date", 7, "iso", None),
    # T-334 feeds (weekday / posting-lag cadence)
    ("form4", "data/macro_data/alt/edgar_form4_index.parquet", "date_filed", 5, "iso", None),
    ("usaspending", "data/macro_data/alt/usaspending_awards.parquet", "snap_date", 7, "iso", None),
    ("credit_oas", "data/macro_data/alt/credit_spread_oas.parquet",
     "observation_date", 7, "iso",                  # T-336 C5 (deep history + live tail)
     "local-only Phase-A: the cloud pulse never runs the credit-OAS pull (the laptop job "
     "collects it daily), so in-container the file is absent and read 'no-date' on every "
     "run since T-336; no cloud consumer (2026-11-19). Un-exempt if the pulse adds the pull."),
    # positioning: real cadences are weekly → twice-monthly → monthly (+ publication lag)
    ("regsho", "data/positioning/finra_regsho_short_volume.parquet", "date", 7, "iso", None),
    ("naaim", "data/positioning/naaim_exposure.parquet", "date", 14, "excel",
     "COLLECTOR BROKEN 2026-07-29 by a NAAIM site redesign (WordPress/Bricks): the series "
     "now renders client-side — 0 table elements, 0 date+value pairs, no static .xls/.csv "
     "export (both legacy paths 404). Repair means scraping an undocumented JS endpoint. "
     "ZERO code consumers, so the consumer-less rule applies as it did for GDELT/gpr; "
     "1,047 banked observations retained. Un-exempt if a consumer appears."),
    ("finra_short_interest", "data/positioning/finra_short_interest.parquet",
     "accountingYearMonthNumber", 40, "iso", None),   # observed max gap 31d (T-340b: budget was 1d too tight)
    ("sec_ftd", "data/positioning/sec_ftd.parquet", "settlement_date", 45, "iso", None),
    ("finra_margin", "data/positioning/finra_margin_debt.parquet", "month/year", 75, "monthyear",
     "local-only Phase-A; month/year strings unparseable in-container; no cloud consumer"),
]


def _newest(path: Path, col: str, fmt: str):
    """Newest timestamp in `col`, or None if the file/column is unreadable OR the
    dates cannot be parsed (an unparseable date column is itself a gate failure)."""
    try:
        s = pd.read_parquet(path, columns=[col])[col]
    except Exception:
        return None
    try:
        if fmt == "excel":       # Excel serial days (NAAIM ships these raw)
            v = pd.to_numeric(s, errors="coerce").dropna()
            return (pd.Timestamp("1899-12-30") + pd.to_timedelta(v.max(), unit="D")
                    ) if len(v) else None
        if fmt == "gdelt":       # 20260729T000000Z
            return pd.to_datetime(s.astype(str).str.slice(0, 8), format="%Y%m%d",
                                  errors="coerce").max()
        if fmt == "monthyear":   # "Jan-26" style
            return pd.to_datetime(s.astype(str), format="%b-%y", errors="coerce").max()
        d = pd.to_datetime(s.astype(str), errors="coerce", utc=False)
        d = d.dt.tz_localize(None) if getattr(d.dtype, "tz", None) else d
        return d.max()
    except Exception:
        return None


def assess_feed_health(root: Path) -> Tuple[Dict[str, dict], List[str]]:
    """Age EVERY feed against its own budget. Returns (per-feed detail, offenders)."""
    now = pd.Timestamp.now().normalize()
    detail, stale = {}, []
    for name, rel, col, budget, fmt, exempt in _FEED_HEALTH:
        if exempt:
            detail[name] = {"age_days": None, "budget": budget, "ok": True,
                            "exempt": exempt}
            continue
        newest = _newest(root / rel, col, fmt)
        if newest is None or pd.isna(newest):
            detail[name] = {"age_days": None, "budget": budget, "ok": False,
                            "reason": "missing/unparseable dates — unmonitorable"}
            stale.append(f"{name}(no-date)")
            continue
        age = int((now - pd.Timestamp(newest).normalize()).days)
        ok = age <= budget
        detail[name] = {"age_days": age, "budget": budget, "ok": ok,
                        "newest": str(pd.Timestamp(newest).date())}
        if not ok:
            stale.append(f"{name}({age}d>{budget}d)")
    return detail, stale


@dataclass
class AltdataArchiveResult:
    ran: bool
    degraded: bool
    reason: str
    reports: List[str] = field(default_factory=list)     # per-source human lines
    fresh_rows: Dict[str, int] = field(default_factory=dict)  # snapshot source -> today's rows
    feed_health: Dict[str, dict] = field(default_factory=dict)  # T-335: per-feed age vs budget
    stale_feeds: List[str] = field(default_factory=list)        # T-335: budget offenders
    snapshot_degraded: bool = False   # the T-290 same-day check ALONE
    stale_degraded: bool = False      # the T-335 cadence-budget check ALONE


def _fresh_rows(path: Path, datecol: str, today: str) -> int:
    """Rows in ``path`` stamped with ``today`` in ``datecol``. Missing file /
    unreadable parquet ⇒ 0 (which — for a snapshot source — reads as broken)."""
    try:
        df = pd.read_parquet(path, columns=[datecol])
        return int((df[datecol].astype(str) == today).sum())
    except Exception:
        return 0


@contextmanager
def _out_dir_under_root(module: ModuleType, out_dir: Path) -> Iterator[None]:
    """Point an archiver module's ``OUT_DIR`` at the run's root while its jobs run.

    Both archivers self-root ``OUT_DIR`` to THEIR checkout at import, and every write
    site in them resolves ``OUT_DIR / <name>`` at CALL time — the same global their own
    ``--out-dir`` flag reassigns. Without this the daily run wrote the hoard into the
    checkout while the freshness check below (and the S3 push) read the run's root: a
    run rooted anywhere else wrote into a checkout someone else was using (2026-11-19).
    Where the root IS the checkout (the cloud container) the path is unchanged.
    Restored afterwards so a caller of the archivers' own functions is unaffected."""
    previous = module.OUT_DIR
    module.OUT_DIR = out_dir
    try:
        yield
    finally:
        module.OUT_DIR = previous


def run_altdata_archive(root: str, *, days_back: int = 10) -> AltdataArchiveResult:
    """Run both T-136 archivers (each pull fail-open) and assess snapshot
    freshness. Never raises into the caller — the trading path stays clean.

    Both archivers write under ``root`` (see ``_out_dir_under_root``)."""
    root_p = Path(root)
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    reports: List[str] = []

    # Import lazily so a broken archiver import can't take down the driver's
    # module load.
    def _run_group(tag: str, jobs: List[Tuple[str, Callable[[], str]]]) -> None:
        for name, fn in jobs:
            try:
                reports.append(f"[{tag}] {name}: {fn()}")
            except Exception as exc:            # fail-open per source
                reports.append(f"[{tag}] {name}: FAILED ({type(exc).__name__}: {exc})")

    try:
        import scripts.archive_altdata_t136 as ad
        with _out_dir_under_root(ad, root_p / ALT_REL):
            _run_group("D", [
                ("gpr", ad.pull_gpr), ("epu", ad.pull_epu),
                ("polymarket", ad.snapshot_polymarket),
                ("kalshi", ad.snapshot_kalshi),
                ("kxfed", ad.snapshot_kxfed),               # T-290 d2 rate-path
                ("fred_rate_path", ad.pull_fred_rate_path),  # T-290 d2 resolution
                # T-334 CEF panel RETIRED 2026-11-19 (see _RETIRED_CEF): no longer pulled.
                ("form4", ad.pull_form4_index),               # T-334 EDGAR Form 4 index
                ("usaspending", ad.pull_usaspending),         # T-334 federal awards
            ])
    except Exception as exc:
        reports.append(f"[D] archive_altdata import FAILED ({type(exc).__name__}: {exc})")

    try:
        import scripts.archive_positioning_t136 as ap
        with _out_dir_under_root(ap, root_p / POSITIONING_REL):
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
    # T-335: EVERY feed is now aged against its own cadence budget — degraded if the
    # same-day snapshot check fails OR any feed exceeds its budget / is unmonitorable.
    feed_health, stale_feeds = assess_feed_health(root_p)
    snapshot_degraded = landed == 0
    stale_degraded = bool(stale_feeds)
    degraded = snapshot_degraded or stale_degraded
    # T-340: the reason must describe the alarm that ACTUALLY fired. The first
    # version branched on `degraded` (the OR of both alarms) but hardcoded the
    # snapshot wording, so a cadence-only failure printed "ZERO market-snapshot rows
    # landed ... {'kalshi': 287, 'polymarket': 568}" — a message contradicted by its
    # own numbers in the same string (the sibling-number tell). Each alarm now speaks
    # only for itself.
    parts = []
    if snapshot_degraded:
        parts.append(f"ZERO market-snapshot rows landed for {today} across "
                     f"{list(fresh_rows)} — silent API breakage (dedup hides it "
                     f"on disk); {fresh_rows}")
    else:
        parts.append(f"{landed}/{len(fresh_rows)} snapshot sources fresh for "
                     f"{today}: {fresh_rows}")
    if stale_degraded:
        parts.append(f"STALE/UNMONITORABLE BEYOND BUDGET: {stale_feeds}")
    reason = " | ".join(parts)
    return AltdataArchiveResult(ran=True, degraded=degraded, reason=reason,
                                reports=reports, fresh_rows=fresh_rows,
                                feed_health=feed_health, stale_feeds=stale_feeds,
                                snapshot_degraded=snapshot_degraded,
                                stale_degraded=stale_degraded)
