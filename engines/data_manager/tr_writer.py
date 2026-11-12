"""The TOTAL-RETURN writer for the processed price cache (data/processed/<TICKER>_1d.{csv,parquet}).

RULING (director, 2026-10-15, for the user to override): the cache convention is TOTAL RETURN —
exact post-seam, a constant-yield approximation pre-seam (`apply_dividend_strip`). No writer of
that convention existed in the code: the Alpaca fetch asks `adjustment="split"` and the yfinance
fallback `auto_adjust=False`. Agent R's design read (C-1) requires THIS writer to exist and be
proven on a copy BEFORE any convention guard is switched on, or the first ex-date after switch-on
refuses an append nothing can satisfy and the cache stalls stale.

Why it REPLACES files whole: a dividend back-adjusted series is not append-only — every new ex-date
rescales the provider's entire past. So a refresh is a whole-file re-fetch from ONE provider that
covers the cached span (mixing two providers' back-adjustments at a seam is the T-082b class).
ONE provider for the WHOLE universe — yfinance (`auto_adjust=True`) — never chosen per file
(director ruling 2026-10-15, provisional until the yfinance re-measure of the files below confirms
it). Measured on a copy, this overturns the per-span rule first built here (C-1: Alpaca for spans
starting on/after 2016): the project's Alpaca feed is IEX, whose daily history starts 2020-07-27.
Of the 172 files that rule sent to Alpaca, 69 came back empty, 69 of the 103 that returned could
not cover the cached span, and 99 of the 103 read DIFFERENT_CONVENTION against the cache — an IEX
tail is not the tape the cache was built from. The Alpaca writer provider is archived
(Archive/data_engine/tr_writer_alpaca_provider_2026_10_15.py). On the measured cadence (33 of 39
twinned names step at ex-dates, most quarterly) this branch is the STEADY STATE — ~580 of ~730
files a quarter — and every pass is a substrate re-pin.

What the writer proves, rather than assumes (R's C-3/C-4):
  * the fetch MODE is asserted in a write record, never inferred from a parameter;
  * the basis is MEASURED at write time with a two-mode fetch (adjusted vs dividend-unadjusted):
    "measured_tr" when the ratio steps at ex-dates, "unverified: no ex-date in window" otherwise;
  * the re-fetch must COVER the cached span, or it is refused;
  * the re-fetch must AGREE with the cache up to a rescale over the last OVERLAP_TAIL_BARS cached
    bars (classify_overlap: APPEND or RESCALED), or it is refused. The basis measure cannot catch a
    provider on the other convention — a split-only provider's two modes are identical, so it reads
    "unverified", exactly like a non-payer — so without this a split-only series replaces a
    total-return cache under a clean write record (Agent R's planted mismatch, 2026-10-15);
  * the cache's LAST BAR must equal the provider's true print (unadjusted close × splits after it),
    up to the dividends its own adjustment applied (the LEVEL rail, adopted 2026-10-15). A level
    change outside the identity needs a declaration (`config/level_declarations.json`), and a
    declared reused ticker is never written. Each write pins a per-file record under the cache;
  * the parquet + csv pair is written ATOMICALLY: a failure of either leaves both originals intact;
  * the Yahoo symbol comes from ONE table (`yahoo_symbols`): a share class is a spelling (BRK.B ->
    BRK-B); a rename is an IDENTITY claim held to the same span and overlap rails, and the record
    says "symbol mapped: X -> Y (kind)". No other symbol is ever tried.
The guard primitives (overlap classification at the rounding floor, the seam-return rail) live
here too, so the writer and the guard share one definition of "same convention".

OPTION (a) — the SEAM-preserving write (the user's cutover ruling, 2026-10-22). The pre-seam drip
(T-082b's constant-yield approximation of the Stooq years) STAYS for every file, labelled; only
the POST-seam span is rewritten exact. So for a file the merge record (`_merge_meta.json`) shows
as `both` with pre-seam bars, the writer KEEPS the cached bars before the seam — scaled by the
ratio measured AT the seam bar, so the seam-day return is unchanged and the file sits at the
provider's level — and takes the provider's exact total return from the seam on. The provider
need only cover the post-seam span (that is what admits the class (iii)/(iv) names whose Stooq
history is deeper than the provider's), and the ratio must be the SAME constant at the seam as
over the last-year tail: a mid-span step is a convention change the cache made (AMCR missed two
ex-dates), refused unless a `cache_convention_defects` declaration names it. A file with no
pre-seam span is replaced whole, as before. The write record carries `seam` and `convention`
(what each span IS), which is what the census's universal label reads back.

OPTION (a′) — the ERA-AWARE pre-seam convention (USER RULING 2026-11-12, T-387; amends option (a)
above, whose text is kept as the record of the 2026-10-22 ruling). The kept pre-seam bars are no
longer the drip: `era_tr_rewrite` rewrites a seam file's pre-seam span OFFLINE to `era_tr` — Stooq
as-is where Stooq is total return, every dividend it MISSED restored from the yfinance reference
per measured ex-date (the fraction-missed probe, transient blocks masked), no-reference spans kept
raw Stooq and LABELLED UNVERIFIED, ONE constant at the seam. Post-seam, every Date/OHLCV field stays
byte-identical; ATR on the first 14 post-seam rows and PrevClose on the seam row change by construction
(they are functions of pre-seam bars — measured over the 575: ATR on 14 rows in 181 files, 13 in 390, 3 in
VRT, 1 in VLTO, 0 in PODD and POM; PrevClose in 573); every later post-seam field, and `close_unadj` on EVERY row, stays byte-identical. The (a′) logic itself lives in ONE module, `era_tr.py` (shared with
`scripts/drip_fix_candidate_t384.py`). On a drip file the order is: option (a)'s seam write (or the
cached file as merged), then the (a′) rewrite; `full_refetch` thereafter KEEPS whatever the file's
pinned record says its pre-seam span IS (`kept_pre_seam_convention`) — it never relabels era_tr
bars as drip, nor drip bars as era_tr. Proposal: `docs/Sources/proposal_drip_fix_a_prime_2026-11-11.md`.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from engines.data_manager.yahoo_symbols import yahoo_symbol

UNIVERSE_PROVIDER = "yfinance"  # ONE provider for every file — see the module docstring
SPAN_SLACK_DAYS = 7            # a provider's first bar may trail the cached first bar by a holiday
BASIS_WINDOW_DAYS = 90         # calendar days ≈ 60 trading days for the two-mode basis measure
ROUNDING = 0.005               # adjusted closes round to the cent: 0.005/price per bar (R §3.1)
FP_NOISE = 1e-9
SEAM_RAIL = 0.25               # |first appended return| above this is refused unless a rescale was seen
OVERLAP_MIN_BARS = 10
#: The cached tail a whole-file replacement must agree with: one trading year, so the window holds
#: an ex-date of every payer that pays at least annually. Inside a window with no ex-date a
#: total-return tail and a split-only tail are IDENTICAL, so a short tail passes the other
#: convention. Measured on a copy of the cache (532 covered files): verdicts are identical at 126,
#: 252 and 504 bars and over the whole post-seam region — 419 RESCALED, 110 APPEND, and
#: DIFFERENT_CONVENTION on exactly AGG, EFA, VNQ (the split-only files backfill_t052 wrote) — while
#: a 40-bar tail reads EFA and VNQ as RESCALED.
OVERLAP_TAIL_BARS = 252
COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
#: The SPLIT-ONLY close (the provider's unadjusted mode — the price that traded, split-adjusted) as
#: a second column on every written file, named EXACTLY this (ruled 2026-10-15, the dollar-ADV HIGH:
#: every dollar-ADV, slippage and borrow bucket, and the Engine B share-sizing unit, read it; a file
#: without the column is read as total-return basis). NaN on bars the provider does not hold (the
#: kept pre-seam bars before a class (iii)/(iv) provider's first bar) — never derived.
CLOSE_UNADJ = "close_unadj"

# ── the LEVEL rail (adopted 2026-10-15; docs/Sources/proposal_level_rail_last_bar_identity_2026-10-15.md)
#: |ln residual| tolerance for the last-bar level identity. Measured: legitimate files sit within
#: 0.0053 (APH, stale); scale defects at ln 10 = 2.30 — a factor of ~400 of separation.
LEVEL_TOLERANCE = 0.01
#: A cached file with no pinned write record was written by the pre-T-167 DataManager on
#: 2026-04-18/25 (the pre-merge backup); its total-return adjustment is as of this date, so the
#: identity's dividend factor runs from the file's last bar to here (a stale file's last bar was
#: scaled by the dividends paid between the two — APH 0.9947, explained to 1.0000).
LEGACY_ADJUSTED_AS_OF = pd.Timestamp("2026-04-25")
#: Per-file write records, pinned UNDER the cache (inside the substrate manifest's scope, so the
#: census can read them in the image) — R's condition (c).
WRITE_RECORDS_DIR = "_write_records"
LEVEL_DECLARATIONS_PATH = Path(__file__).resolve().parents[2] / "config" / "level_declarations.json"
CANONICAL_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

# ── OPTION (a): seams and conventions (the user's cutover ruling, 2026-10-22) ──────
#: The T-082b merge record, pinned under the cache: per file, `merge_case` (`both` / `alpaca_only`),
#: `seam_date` and `n_stooq_pre_seam`. It is the ONLY source for "where is this file's seam", so a
#: cache without it has no seams the writer can keep (every write is then whole-file) — and the
#: census's convention label cannot be produced from it at all (fail closed, convention.py).
MERGE_META_NAME = "_merge_meta.json"
#: The declared seams (classes (iii)/(iv)), the whole-file overrides (SPY, regenerated after the
#: merge) and the cache-convention defects (the split-only trio, the mixed AMCR).
CONVENTION_DECLARATIONS_PATH = (Path(__file__).resolve().parents[2] / "config"
                                / "convention_declarations.json")
CONVENTION_SECTIONS = ("seams", "whole_file_overrides", "cache_convention_defects")
DEFECT_KINDS = ("split_only_cache", "mixed_convention_cache")
#: The conventions a span can carry. "drip": T-082b's `apply_dividend_strip` — Stooq bars
#: scaled by a fitted exp(a + b·t), a constant-yield APPROXIMATION of total return (every ex-date
#: step smeared into a drift). "exact_tr": the provider's ex-date total return.
#: "era_tr" (option (a′), USER RULING 2026-11-12, T-387): the pre-seam convention the cutover writes —
#: Stooq where Stooq is total return; the missed dividends restored per measured ex-date; no-reference
#: spans raw Stooq, LABELLED UNVERIFIED (the record's `era_tr` block carries the spans). `drip` stays
#: a valid label: it is what the pre-cutover cache (and a merge record with no write record) IS.
DRIP = "drip"
EXACT_TR = "exact_tr"
ERA_TR = "era_tr"
#: The conventions a KEPT pre-seam (Stooq) span can carry — the same bar dates under either.
PRE_SEAM_CONVENTIONS = (DRIP, ERA_TR)
#: What a declaration may name per side (`seams`) or for a whole file (`whole_file_overrides`).
SEAM_PRE_CONVENTIONS = (DRIP, ERA_TR, EXACT_TR)
SEAM_POST_CONVENTIONS = (DRIP, EXACT_TR)
WHOLE_CONVENTIONS = (DRIP, EXACT_TR)
#: The seam-ratio rail: |ln r_seam − ln r_tail| may not exceed this many rounding floors (the
#: floor at the seam bar plus the tail's median floor). A dividend the cache missed is ~1e-2;
#: the floor at $100 is 5e-5.
SEAM_RATIO_FLOORS = 3

#: symbol -> DataFrame indexed by date with columns "Dividends" and "Stock Splits" (the provider's
#: corporate-actions record, in the same split basis as its unadjusted closes).
Actions = Callable[[str], pd.DataFrame]

#: (ticker, start, end, adjusted) -> OHLCV DataFrame on a tz-naive DatetimeIndex.
#: adjusted=True -> total return (dividends + splits); False -> split-adjusted only.
Provider = Callable[[str, pd.Timestamp, pd.Timestamp, bool], pd.DataFrame]


class WriterRefusal(RuntimeError):
    """The writer will not write: the evidence for a safe replacement is missing."""

    def __init__(self, message: str, detail: Optional[dict] = None):
        super().__init__(message)
        self.detail = detail or {}       # the measured evidence, for the caller's record


@dataclass
class WriteRecord:
    ticker: str
    provider: str
    symbol_mapped: Optional[str]   # "X -> Y (share class|rename)"; None when fetched as named
    mode: str                     # the fetch mode ASSERTED: "adjusted" (total return)
    span_start: str
    span_end: str
    n_rows: int
    basis: str                     # "measured_tr" | "unverified: ..." — measured, not claimed
    basis_detail: dict
    overlap: Optional[dict]        # classify_overlap vs the cached tail; None for a new ticker
    cached_span: Optional[list]
    written_at: str
    level: Optional[dict] = None   # the last-bar identity (None for a new ticker)
    level_declared: Optional[dict] = None   # the declaration a level change was written under
    adjusted_as_of: Optional[str] = None    # the date this file's total-return adjustment is as of
    seam: Optional[dict] = None             # option (a): the kept pre-seam span and the seam ratio
    convention: Optional[dict] = None       # what each span of the written file IS (drip / era_tr / exact_tr)
    convention_declared: Optional[dict] = None   # the cache-convention defect a write was made under
    close_unadj: Optional[dict] = None      # the split-only column: its span and the bars it lacks
    era_tr: Optional[dict] = None           # option (a′): the pre-seam build record (unverified spans, rails)


# ── pure primitives ───────────────────────────────────────────────────────────────

def covers_span(new: Optional[pd.DataFrame], cached: Optional[pd.DataFrame],
                slack_days: int = SPAN_SLACK_DAYS) -> Tuple[bool, str]:
    """A whole-file replacement must cover everything the cached file holds."""
    if new is None or new.empty:
        return False, "the provider returned no bars"
    if cached is None or cached.empty:
        return True, "no cached span to cover (a new ticker)"
    lead = (new.index.min() - cached.index.min()).days
    if lead > slack_days:
        return False, (f"re-fetch starts {new.index.min().date()} but the cached span starts "
                       f"{cached.index.min().date()} ({lead} days later) — it cannot replace the file")
    if new.index.max() < cached.index.max():
        return False, (f"re-fetch ends {new.index.max().date()}, before the cached end "
                       f"{cached.index.max().date()}")
    return True, "covers the cached span"


def _floor(price: pd.Series) -> pd.Series:
    """Per-bar rounding floor in log-ratio units: a cent of rounding at this price level."""
    return ROUNDING / price.abs().clip(lower=1e-6) + FP_NOISE


def measure_basis(adjusted_close: pd.Series, unadjusted_close: pd.Series) -> dict:
    """Two-mode measurement (R's C-4). Total-return back-adjustment makes adjusted/unadjusted RISE
    toward 1 in steps at ex-dates; identical series mean no ex-date fell in the window."""
    j = pd.concat([adjusted_close.rename("adj"), unadjusted_close.rename("raw")],
                  axis=1, join="inner").dropna()
    if len(j) < 20:
        return {"basis": "unverified: too few common bars", "n_common": int(len(j))}
    lr = np.log(j["adj"] / j["raw"])
    d = lr.diff().dropna()
    floor = _floor(j["raw"]).reindex(d.index)
    steps = d[d.abs() > 2 * floor]
    detail = {"n_common": int(len(j)), "n_steps": int(len(steps)),
              "step_dates": [str(x.date()) for x in steps.index[:12]],
              "log_ratio_first": float(lr.iloc[0]), "log_ratio_last": float(lr.iloc[-1])}
    if steps.empty:
        return {"basis": "unverified: no ex-date in window", **detail}
    if (steps < 0).any():
        return {"basis": "anomalous: adjusted/unadjusted ratio FELL at a step", **detail}
    return {"basis": "measured_tr", **detail}


def classify_overlap(cached_close: pd.Series, fetched_close: pd.Series) -> dict:
    """The guard's test on an overlap window (R §3.1): the same convention reads ratio 1 at the
    rounding floor; a rescale (a new ex-date or split after the window) reads a CONSTANT ratio ≠ 1;
    anything that moves within the window — a step or a slope — is a different convention."""
    j = pd.concat([cached_close.rename("c"), fetched_close.rename("f")], axis=1, join="inner").dropna()
    if len(j) < OVERLAP_MIN_BARS:
        return {"verdict": "INSUFFICIENT", "n": int(len(j))}
    lr = np.log(j["f"] / j["c"])
    floor = _floor(j["c"])
    med = float(lr.median())
    resid = lr - med
    t = (j.index - j.index[0]).days.to_numpy(dtype=float)
    slope = float(np.polyfit(t, lr.to_numpy(), 1)[0]) if t[-1] > 0 else 0.0
    slope_move = abs(slope * t[-1])                      # total drift across the window
    detail = {"n": int(len(j)), "median_log_ratio": med, "slope_move": slope_move,
              "max_resid": float(resid.abs().max()), "floor_median": float(floor.median())}
    if (resid.abs() > 3 * floor).any() or slope_move > 3 * float(floor.median()):
        return {"verdict": "DIFFERENT_CONVENTION", **detail}
    if abs(med) <= 2 * float(floor.median()):
        return {"verdict": "APPEND", **detail}
    return {"verdict": "RESCALED", "ratio": float(np.exp(med)), **detail}


def seam_return_ok(last_cached_close: float, first_new_close: float, rescaled: bool) -> Tuple[bool, float]:
    """R's C-3 rail: an UNADJUSTED provider after a split matches the pre-split overlap and would
    append post-split bars at a fraction of the price. Catch the jump at the seam."""
    r = first_new_close / last_cached_close - 1.0
    return (rescaled or abs(r) < SEAM_RAIL), float(r)


def with_derived_columns(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """ATR + PrevClose per project convention (scripts/merge_stooq_alpaca_substrate.py)."""
    df = ohlcv[COLUMNS].sort_index().copy()
    tr = pd.concat([(df["High"] - df["Low"]).abs(),
                    (df["High"] - df["Close"].shift()).abs(),
                    (df["Low"] - df["Close"].shift()).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(window=14, min_periods=14).mean()
    df["PrevClose"] = df["Close"].shift(1)
    df.index.name = "Date"
    return df


def write_pair_atomically(df: pd.DataFrame, parquet_path: Path, csv_path: Path) -> None:
    """Both temp files are written first; only then are both swapped in. A failure while writing
    either leaves BOTH originals untouched (R §3.2: today each write swallows the other's failure,
    and readers use parquet first)."""
    parquet_path, csv_path = Path(parquet_path), Path(csv_path)
    tmp_pq = parquet_path.with_name(parquet_path.name + ".writing")
    tmp_csv = csv_path.with_name(csv_path.name + ".writing")
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(tmp_pq, index=True)
        df.to_csv(tmp_csv, date_format="%Y-%m-%d")
    except Exception:
        for tmp in (tmp_pq, tmp_csv):
            if tmp.exists():
                tmp.unlink()              # temps only — the originals were never opened
        raise
    os.replace(tmp_csv, csv_path)
    os.replace(tmp_pq, parquet_path)


def write_text_pair_atomically(text: str, frame: pd.DataFrame, parquet_path: Path, csv_path: Path) -> None:
    """The TEXT-preserving twin of `write_pair_atomically` (option (a′)): the csv is `text` VERBATIM
    (so the rows the rewrite does not touch stay byte-identical) and the parquet is `frame` (the
    caller parses it FROM that text — `era_tr.frame_from_text`). Both temps first, then both swaps."""
    parquet_path, csv_path = Path(parquet_path), Path(csv_path)
    tmp_pq = parquet_path.with_name(parquet_path.name + ".writing")
    tmp_csv = csv_path.with_name(csv_path.name + ".writing")
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_parquet(tmp_pq)
        with open(tmp_csv, "w", newline="") as fh:
            fh.write(text)
    except Exception:
        for tmp in (tmp_pq, tmp_csv):
            if tmp.exists():
                tmp.unlink()              # temps only — the originals were never opened
        raise
    os.replace(tmp_csv, csv_path)
    os.replace(tmp_pq, parquet_path)


# ── the LEVEL rail ────────────────────────────────────────────────────────────────

def load_level_declarations(path: Path = LEVEL_DECLARATIONS_PATH) -> Dict[str, dict]:
    """The hand-set facts the identity cannot establish: per name, `kind` (`scale_defect` — a level
    change the write may make if `declared_ratio` explains it; `reused_ticker` — class (i), never
    written), with its source. An absent file means no declarations; an unreadable one raises."""
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text()).get("declarations", {})


def level_identity(cached_close: pd.Series, unadjusted: pd.Series, actions: pd.DataFrame,
                   adjusted_as_of: pd.Timestamp) -> dict:
    """The cache's last bar against the level the provider says it SHOULD hold. The cache was
    adjusted as of `adjusted_as_of` (W): every split and dividend in (d, W] was already applied to
    its bars by its own writer, so the reference is the provider's split-adjusted close at d with
    only the splits AFTER W multiplied back in:
        reference = unadjusted(d) × Π(split factors after W);   identity = cache(d) / reference;
        the dividend factor over ex-dates in (d, W];             residual = identity / factor.
    A correct cached LEVEL reads residual 1. (Fixed 2026-10-15: the splits were first taken after
    d, which falsely read a STALE file split-adjusted by its writer — NVDA ends 2024-05-10, its 10:1
    split was 2024-06-10, the file was written 2026-04 — as ÷10. The 652-file sweep found it.)"""
    d = pd.Timestamp(cached_close.index.max())
    c = float(cached_close.iloc[-1])
    upto = unadjusted.loc[:d]
    if upto.empty:
        raise WriterRefusal(f"no provider print at or before the cache's last bar {d.date()}",
                            detail={"level": {"d_last": str(d.date())}})
    raw_d = float(upto.iloc[-1])
    actions = actions.copy()
    actions.index = pd.to_datetime(actions.index)      # an EMPTY record has no datetime index
    splits = actions["Stock Splits"] if "Stock Splits" in actions else pd.Series(dtype=float)
    splits = splits[(splits > 0) & (splits.index > pd.Timestamp(adjusted_as_of))]
    mult = float(splits.prod()) if len(splits) else 1.0
    reference = raw_d * mult
    divs = actions["Dividends"] if "Dividends" in actions else pd.Series(dtype=float)
    divs = divs[(divs > 0) & (divs.index > d) & (divs.index <= pd.Timestamp(adjusted_as_of))]
    factor = 1.0
    for ex, dv in divs.items():
        prev = unadjusted.loc[:ex - pd.Timedelta(days=1)]
        if prev.empty:
            raise WriterRefusal(f"no provider close before ex-date {ex.date()}",
                                detail={"level": {"d_last": str(d.date())}})
        factor *= 1.0 - float(dv) / float(prev.iloc[-1])
    identity = c / reference
    residual = identity / factor
    return {"d_last": str(d.date()), "cache_close": c, "unadjusted_close": raw_d,
            "splits_after_adjusted_as_of": mult, "reference": reference, "identity": identity,
            "dividend_factor": factor, "adjusted_as_of": str(pd.Timestamp(adjusted_as_of).date()),
            "residual": residual, "log_residual": float(np.log(residual))}


def _write_record_path(cache_dir: Path, ticker: str) -> Path:
    return Path(cache_dir) / WRITE_RECORDS_DIR / f"{ticker}.json"


def _read_write_record(cache_dir: Path, ticker: str) -> Optional[dict]:
    p = _write_record_path(cache_dir, ticker)
    return json.loads(p.read_text()) if p.exists() else None


def _write_record_atomically(cache_dir: Path, record: "WriteRecord") -> None:
    p = _write_record_path(cache_dir, record.ticker)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".writing")
    tmp.write_text(json.dumps(asdict(record), indent=1, default=str))
    os.replace(tmp, p)


def substrate_level_declarations(cache_dir: Path) -> dict:
    """The census block (`level_declarations`): every file in this substrate whose CURRENT version
    was written under a level declaration, read from the pinned per-file records. The records
    directory's presence is reported, never assumed: a substrate written before the rail has no
    records, which reads `records_dir_present: False`, not as a clean zero. The block names the
    directory it READ (`cache_dir`): on a proof-on-a-copy run the producers still read the canonical
    cache, so the label is what keeps the block from describing a substrate it did not read (R)."""
    d = Path(cache_dir) / WRITE_RECORDS_DIR
    out = {"cache_dir": str(Path(cache_dir)), "records_dir_present": d.is_dir(), "declared": {}}
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.json")):
        rec = json.loads(p.read_text())
        if rec.get("level_declared"):
            out["declared"][rec["ticker"]] = {"kind": rec["level_declared"].get("kind"),
                                              "declared_ratio": rec["level_declared"].get("declared_ratio"),
                                              "written_at": rec.get("written_at")}
    return out


# ── OPTION (a): seams and cache-convention declarations ───────────────────────────

def load_convention_declarations(path: Path = CONVENTION_DECLARATIONS_PATH) -> Dict[str, dict]:
    """`config/convention_declarations.json`: `seams` (per name: `seam_date`, `pre_seam`,
    `post_seam` — the classes (iii)/(iv) ruled to keep their deep history behind a declared seam),
    `whole_file_overrides` (per name: `convention` — a file regenerated whole after the merge,
    whose merge record is stale), `cache_convention_defects` (per name: `kind` in DEFECT_KINDS —
    the cache itself is on the wrong convention, and the declared check must verify it before a
    whole-span re-fetch replaces it). An absent file means no declarations; a malformed one or an
    unknown kind RAISES (a declaration that cannot be read must never license anything)."""
    path = Path(path)
    if not path.exists():
        return {s: {} for s in CONVENTION_SECTIONS}
    raw = json.loads(path.read_text())
    out = {s: dict(raw.get(s, {})) for s in CONVENTION_SECTIONS}
    for t, d in out["seams"].items():
        pd.Timestamp(d["seam_date"])
        if d.get("pre_seam") not in SEAM_PRE_CONVENTIONS or d.get("post_seam") not in SEAM_POST_CONVENTIONS:
            raise ValueError(f"convention_declarations.seams[{t}]: pre_seam must be one of "
                             f"{SEAM_PRE_CONVENTIONS}, post_seam one of {SEAM_POST_CONVENTIONS}")
    for t, d in out["whole_file_overrides"].items():
        if d.get("convention") not in WHOLE_CONVENTIONS:
            raise ValueError(f"convention_declarations.whole_file_overrides[{t}]: convention must be "
                             f"one of {WHOLE_CONVENTIONS}")
    for t, d in out["cache_convention_defects"].items():
        if d.get("kind") not in DEFECT_KINDS:
            raise ValueError(f"convention_declarations.cache_convention_defects[{t}]: kind must be "
                             f"one of {DEFECT_KINDS}")
        if d["kind"] == "mixed_convention_cache":
            steps = d.get("declared_steps") or []
            if not steps:
                raise ValueError(f"convention_declarations.cache_convention_defects[{t}]: a mixed "
                                 f"convention declares the ex-dates the cache missed")
            [pd.Timestamp(s) for s in steps]
    return out


def load_merge_meta(cache_dir: Path) -> Optional[Dict[str, dict]]:
    """The T-082b merge record's `per_ticker` map under this cache, or None when the cache has
    none. Never fabricated: a cache with no record has no seams the writer can keep."""
    p = Path(cache_dir) / MERGE_META_NAME
    if not p.exists():
        return None
    return json.loads(p.read_text()).get("per_ticker", {})


def seam_for(cache_dir: Path, ticker: str,
             conventions: Optional[Dict[str, dict]] = None) -> Optional[dict]:
    """Where this file's seam is, and who says so. A DECLARED seam (classes (iii)/(iv)) wins, and
    must agree with the merge record when both exist (a disagreement is refused, never resolved
    silently). Otherwise the merge record: a `both` file with pre-seam bars has its seam at
    `seam_date`; anything else has no seam (a whole-file write). None = no seam."""
    conventions = load_convention_declarations() if conventions is None else conventions
    meta = load_merge_meta(cache_dir) or {}
    entry = meta.get(ticker)
    decl = conventions["seams"].get(ticker)
    if decl is not None:
        if entry and entry.get("seam_date") and pd.Timestamp(entry["seam_date"]) != pd.Timestamp(decl["seam_date"]):
            raise WriterRefusal(f"{ticker}: the declared seam {decl['seam_date']} disagrees with the "
                                f"merge record's {entry['seam_date']} — re-rule it; not writing")
        return {"date": pd.Timestamp(decl["seam_date"]), "source": "declared",
                "pre_seam": decl["pre_seam"], "post_seam": decl["post_seam"], "declared": dict(decl)}
    if entry and entry.get("merge_case") == "both" and int(entry.get("n_stooq_pre_seam") or 0) > 0 \
            and entry.get("seam_date"):
        return {"date": pd.Timestamp(entry["seam_date"]), "source": "merge_meta",
                "pre_seam": DRIP, "post_seam": EXACT_TR, "declared": None}
    return None


def kept_pre_seam_convention(ticker: str, prior: Optional[dict], seam_spec: dict) -> dict:
    """What the KEPT pre-seam bars ARE (option (a′), T-387). `seam_spec`'s `pre_seam` (a declaration,
    or the merge record's `drip`) describes the file as merged; a pinned write record describes the
    file ITSELF, so when it carries a convention it wins — the writer never relabels era_tr bars as
    drip (a post-cutover refresh) nor drip bars as era_tr. Fail closed: a record whose seam is not
    this seam, a record that says the file was written WHOLE, an era_tr record without its
    `era_tr` block (the unverified spans unknown), or a seam DECLARED era_tr on a file with no record
    is REFUSED. Returns {"pre_seam", "source",
    "era_tr"} (the record's block, carried forward when the kept span is era_tr)."""
    conv = (prior or {}).get("convention")
    seam_date = str(pd.Timestamp(seam_spec["date"]).date())
    if not conv:
        if seam_spec["pre_seam"] == ERA_TR:
            # (T-387 review, MINOR-2) era_tr is only ever CARRIED from a record that has its block; a
            # DECLARED era_tr with no record would label the cached (drip) bars era_tr with no block
            raise WriterRefusal(f"{ticker}: the seam is declared {ERA_TR} but the file has no write record "
                                f"— an era_tr span is written by era_tr_rewrite (which records its "
                                f"unverified spans), never by a declaration; not writing",
                                detail={"seam": {k: str(v) for k, v in seam_spec.items()}})
        return {"pre_seam": seam_spec["pre_seam"], "source": seam_spec["source"], "era_tr": None}
    if "whole" in conv:
        raise WriterRefusal(f"{ticker}: the pinned write record says the file was written WHOLE "
                            f"({conv['whole']}); a seam at {seam_date} would keep its bars before the "
                            f"seam under a convention they do not carry — re-rule the seam; not writing",
                            detail={"prior_convention": conv, "seam": seam_date})
    if str(conv.get("seam_date")) != seam_date:
        raise WriterRefusal(f"{ticker}: the pinned write record's seam {conv.get('seam_date')} is not "
                            f"the seam {seam_date} — the kept bars' convention is unknown; not writing",
                            detail={"prior_convention": conv, "seam": seam_date})
    pre = conv.get("pre_seam")
    if pre not in PRE_SEAM_CONVENTIONS:
        raise WriterRefusal(f"{ticker}: the pinned write record's pre-seam convention {pre!r} is not "
                            f"one of {PRE_SEAM_CONVENTIONS}; not writing", detail={"prior_convention": conv})
    if pre == ERA_TR and not (prior or {}).get("era_tr"):
        raise WriterRefusal(f"{ticker}: the pinned write record says {ERA_TR} but carries no era_tr "
                            f"block — its unverified spans are unknown; not writing",
                            detail={"prior_convention": conv})
    return {"pre_seam": pre, "source": "write_record",
            "era_tr": (prior or {}).get("era_tr") if pre == ERA_TR else None}


def seam_ratio(cached_close: pd.Series, fetched_close: pd.Series, seam_date: pd.Timestamp) -> dict:
    """The provider/cache ratio AT the seam: the first bar on or after the seam both series hold.
    It is the factor the kept pre-seam bars are scaled by, so the seam-day return is unchanged."""
    j = pd.concat([cached_close.rename("c"), fetched_close.rename("f")], axis=1, join="inner").dropna()
    j = j[j.index >= pd.Timestamp(seam_date)]
    if j.empty:
        raise WriterRefusal(f"no common bar at or after the seam {pd.Timestamp(seam_date).date()} — "
                            f"the seam ratio cannot be measured; not writing")
    c, f = float(j["c"].iloc[0]), float(j["f"].iloc[0])
    return {"date": str(j.index[0].date()), "ratio": f / c, "log_ratio": float(np.log(f / c)),
            "floor": float(_floor(pd.Series([c])).iloc[0])}


def verify_split_only_cache(cached_tail: pd.Series, unadjusted_tail: pd.Series,
                            adjusted_overlap: dict) -> dict:
    """The declared check for a SPLIT-ONLY cache (the backfill_t052 trio): the cached tail must
    agree with the provider's split-only mode up to a rescale, AND must read a different
    convention against the total-return mode (the defect must be present, or the declaration no
    longer matches the data). Only then may a whole-span total-return re-fetch replace it."""
    against_split_only = classify_overlap(cached_tail, unadjusted_tail)
    if against_split_only["verdict"] not in ("APPEND", "RESCALED"):
        raise WriterRefusal(
            f"declared split_only_cache, but the cached tail reads {against_split_only['verdict']} "
            f"against the provider's SPLIT-ONLY mode too — the declaration does not explain the "
            f"cache; not writing",
            detail={"against_split_only": against_split_only, "against_total_return": adjusted_overlap})
    if adjusted_overlap["verdict"] != "DIFFERENT_CONVENTION":
        raise WriterRefusal(
            f"declared split_only_cache, but the cached tail reads {adjusted_overlap['verdict']} "
            f"against the TOTAL-RETURN mode — the declared defect is not present; re-rule it",
            detail={"against_split_only": against_split_only, "against_total_return": adjusted_overlap})
    return {"kind": "split_only_cache", "against_split_only": against_split_only,
            "against_total_return": adjusted_overlap}


def verify_mixed_convention(cached_close: pd.Series, fetched_close: pd.Series,
                            declared_steps) -> dict:
    """The declared check for a MIXED cache (AMCR: total return, then two missed ex-dates): the
    log ratio provider/cache over the common span must be piecewise CONSTANT with a step at EVERY
    declared date and at NO other. An undeclared step, or a declared date with no step, refuses."""
    j = pd.concat([cached_close.rename("c"), fetched_close.rename("f")], axis=1, join="inner").dropna()
    if len(j) < OVERLAP_MIN_BARS:
        raise WriterRefusal("declared mixed_convention_cache, but too few common bars to verify it",
                            detail={"n": int(len(j))})
    lr = np.log(j["f"] / j["c"])
    floor = _floor(j["c"])
    d = lr.diff().dropna()
    steps = d[d.abs() > 3 * floor.reindex(d.index)]
    declared = {pd.Timestamp(s) for s in declared_steps}
    found = set(steps.index)
    undeclared = sorted(str(x.date()) for x in found - declared)
    absent = sorted(str(x.date()) for x in declared - found)
    detail = {"kind": "mixed_convention_cache", "n": int(len(j)),
              "declared_steps": sorted(str(x.date()) for x in declared),
              "steps_found": {str(k.date()): float(v) for k, v in steps.items()},
              "undeclared_steps": undeclared, "declared_steps_absent": absent}
    if undeclared or absent:
        raise WriterRefusal(
            f"declared mixed_convention_cache does not match the data — undeclared steps "
            f"{undeclared}, declared steps absent {absent}; not writing", detail=detail)
    return detail


# ── the writer ────────────────────────────────────────────────────────────────────

def _read_cached(cache_dir: Path, ticker: str) -> Optional[pd.DataFrame]:
    pq = cache_dir / "parquet" / f"{ticker}_1d.parquet"
    csv = cache_dir / f"{ticker}_1d.csv"
    if pq.exists():
        return pd.read_parquet(pq)
    if csv.exists():
        return pd.read_csv(csv, parse_dates=["Date"]).set_index("Date")
    return None


def full_refetch(ticker: str, cache_dir: Path, providers: Dict[str, Provider], *,
                 today: pd.Timestamp, new_ticker_start: Optional[pd.Timestamp] = None,
                 write: bool = True, log_path: Optional[Path] = None,
                 actions: Optional[Actions] = None,
                 declarations: Optional[Dict[str, dict]] = None,
                 seam: Any = "auto",
                 conventions: Optional[Dict[str, dict]] = None) -> WriteRecord:
    """Replace `<ticker>_1d` with a total-return re-fetch from THE universe provider — or refuse.

    Never writes unless: the provider covers the span it replaces, the basis is not anomalous, the
    re-fetch agrees with the cached tail up to a rescale (APPEND or RESCALED — DIFFERENT_CONVENTION
    is refused unless a `cache_convention_defects` declaration names this file AND its declared
    check verifies; an overlap too short to measure when a cache exists is refused), the cache's
    LAST BAR equals the provider's true print up to the dividends its own adjustment applied (the
    LEVEL rail; a level change outside it needs a matching declaration, and a declared reused
    ticker is never written), and the pair can be written atomically. `actions` (the provider's
    dividend/split record) is REQUIRED when a cache exists: without it the identity cannot be
    checked, and the writer refuses. `write=False` measures and returns the record only (the
    proof-on-a-copy mode).

    OPTION (a) — `seam`: "auto" (the default) resolves the file's seam through `seam_for` (a
    declared seam, else the merge record under `cache_dir`); None forces a whole-file write; a dict
    from `seam_for` is used as given. With a seam, the cached bars BEFORE it are KEPT (the drip),
    scaled by the ratio measured at the seam bar; the provider must cover the POST-seam span only;
    and the seam ratio must equal the tail's rescale (the seam-ratio rail) unless a mixed-convention
    declaration explains the difference. The record says what each span IS (`convention`).

    OPTION (a′) (T-387): the kept span's label is what the KEPT bars ARE — the file's pinned record
    when it has one (`kept_pre_seam_convention`; an era_tr span keeps its label and its `era_tr`
    block), else the seam spec's. The (a′) rewrite of a drip span is `era_tr_rewrite`, offline.
    """
    cache_dir = Path(cache_dir)
    cached = _read_cached(cache_dir, ticker)
    cached_start = None if cached is None or cached.empty else pd.Timestamp(cached.index.min())
    if cached_start is None and new_ticker_start is None:
        raise WriterRefusal(f"{ticker}: no cached file and no start given for a new ticker")
    provider = UNIVERSE_PROVIDER
    if provider not in providers:
        raise WriterRefusal(f"{ticker}: no {provider} provider given — the writer will not "
                            f"substitute another provider for the universe's")
    symbol, kind = yahoo_symbol(ticker)      # the universe provider's ONE table; no symbol is guessed
    mapped = None if kind is None else f"{ticker} -> {symbol} ({kind})"
    who = f"{ticker} via {provider}" + ("" if mapped is None else f" [symbol mapped: {mapped}]")
    declarations = load_level_declarations() if declarations is None else declarations
    decl = declarations.get(ticker)
    if decl and decl.get("kind") == "reused_ticker":       # before any provider call
        raise WriterRefusal(f"{who}: declared a REUSED TICKER (class (i): {decl.get('source', '')}) — "
                            f"the cached file is another entity; never written",
                            detail={"level_declared": decl, "symbol_mapped": mapped})
    if decl and decl.get("kind") == "symbol_reused_by_later_entity":   # before any provider call
        # The MIRROR of class (i) (ruled 2026-10-23): the cached file IS the PIT entity and is KEPT;
        # the provider's series under the symbol (from `provider_series_start`) is a later company.
        # Never re-fetched under this symbol — a writer-side declaration, not a universe exclusion.
        raise WriterRefusal(f"{who}: declared SYMBOL REUSED BY A LATER ENTITY — the cached file is the "
                            f"PIT entity and is kept; the provider's series under this symbol (from "
                            f"{decl.get('provider_series_start')}) is another company; never re-fetched "
                            f"under this symbol ({decl.get('source', '')})",
                            detail={"level_declared": decl, "symbol_mapped": mapped})
    conventions = load_convention_declarations() if conventions is None else conventions
    defect = conventions["cache_convention_defects"].get(ticker)
    # OPTION (a): the seam. The kept span is the cached bars before it; the provider must cover the
    # rest. A seam with no cached bars on one side of it is a declaration that does not match.
    seam_spec = seam_for(cache_dir, ticker, conventions) if isinstance(seam, str) and seam == "auto" else seam
    prior_record = _read_write_record(cache_dir, ticker)
    pre, post, kept_conv = None, cached, None
    if seam_spec is not None:
        if cached is None or cached.empty:
            raise WriterRefusal(f"{who}: a seam is declared but there is no cached file to keep "
                                f"bars from; not writing", detail={"seam": seam_spec})
        kept_conv = kept_pre_seam_convention(who, prior_record, seam_spec)     # before any provider call
        seam_date = pd.Timestamp(seam_spec["date"])
        pre, post = cached[cached.index < seam_date], cached[cached.index >= seam_date]
        if pre.empty or post.empty:
            raise WriterRefusal(f"{who}: the seam {seam_date.date()} is not inside the cached span "
                                f"({cached_start.date()} → {cached.index.max().date()}) — the seam "
                                f"record does not match the file; not writing",
                                detail={"seam": {k: str(v) for k, v in seam_spec.items()}})
        start = seam_date
    else:
        start = cached_start if cached_start is not None else new_ticker_start
    fetched = providers[provider](symbol, start, today, True)
    ok, why = covers_span(fetched, post)
    if not ok:
        raise WriterRefusal(f"{who}: {why}" + ("" if seam_spec is None else
                                               f" (the post-seam span, seam {start.date()})"),
                            detail={"symbol_mapped": mapped})
    tail_start = today - pd.Timedelta(days=BASIS_WINDOW_DAYS)
    unadjusted = providers[provider](symbol, tail_start, today, False)
    basis = measure_basis(fetched["Close"][fetched.index >= tail_start], unadjusted["Close"])
    if basis["basis"].startswith("anomalous"):
        raise WriterRefusal(f"{who}: {basis['basis']} — not writing",
                            detail={"basis": basis, "symbol_mapped": mapped})
    overlap, convention_declared = None, None
    if cached is not None and not cached.empty:
        cached_tail = cached["Close"].iloc[-OVERLAP_TAIL_BARS:]
        overlap = classify_overlap(cached_tail,
                                   fetched["Close"][fetched.index >= cached_tail.index.min()])
        if overlap["verdict"] == "INSUFFICIENT":
            raise WriterRefusal(
                f"{who}: the re-fetch reads INSUFFICIENT against the last {len(cached_tail)} cached "
                f"bars — an overlap too short to measure; not writing",
                detail={"overlap": overlap, "basis": basis, "symbol_mapped": mapped})
        if defect is not None and defect["kind"] == "mixed_convention_cache":
            # The declared MIXED cache (AMCR): verified over the whole post-seam span — every declared
            # step present, no other — whatever the tail reads (a missed ex-date older than the
            # tail reads RESCALED there; the seam-ratio rail would catch it below).
            convention_declared = verify_mixed_convention(
                cached["Close"] if seam_spec is None else post["Close"], fetched["Close"],
                defect["declared_steps"])
        elif defect is not None and overlap["verdict"] == "DIFFERENT_CONVENTION":
            # The declared SPLIT-ONLY cache (the trio): verified against the provider's two modes.
            unadjusted_tail = providers[provider](symbol, cached_tail.index.min(), today, False)
            convention_declared = verify_split_only_cache(cached_tail, unadjusted_tail["Close"], overlap)
        elif defect is not None:
            raise WriterRefusal(
                f"{who}: a cache-convention defect ({defect['kind']}) is DECLARED but the re-fetch "
                f"reads {overlap['verdict']} against the cached tail — the declaration no longer "
                f"matches the data; re-rule it", detail={"overlap": overlap, "declaration": defect})
        elif overlap["verdict"] not in ("APPEND", "RESCALED"):
            raise WriterRefusal(
                f"{who}: the re-fetch reads {overlap['verdict']} against the last "
                f"{len(cached_tail)} cached bars (basis {basis['basis']!r}) — a whole-file "
                f"replacement must agree with the cache up to a rescale; not writing",
                detail={"overlap": overlap, "basis": basis, "symbol_mapped": mapped})
        if convention_declared is not None:
            convention_declared = {**convention_declared, "declaration": dict(defect)}
    level, level_declared = None, None
    if cached is not None and not cached.empty:
        if actions is None:
            raise WriterRefusal(f"{who}: no corporate-actions record given — the last-bar level "
                                f"identity cannot be checked; not writing",
                                detail={"symbol_mapped": mapped})
        prior = prior_record
        as_of = (pd.Timestamp(prior["adjusted_as_of"]) if prior and prior.get("adjusted_as_of")
                 else LEGACY_ADJUSTED_AS_OF)
        d_last = pd.Timestamp(cached.index.max())
        unadj = providers[provider](symbol, d_last - pd.Timedelta(days=10),
                                    max(d_last, as_of) + pd.Timedelta(days=3), False)
        level = level_identity(cached["Close"], unadj["Close"], actions(symbol), as_of)
        lr = level["log_residual"]
        if decl and decl.get("kind") == "scale_defect":
            if abs(lr + float(np.log(decl["declared_ratio"]))) <= LEVEL_TOLERANCE:
                level_declared = decl
            elif abs(lr) <= LEVEL_TOLERANCE:
                raise WriterRefusal(
                    f"{who}: a scale defect is DECLARED but the level identity holds (residual "
                    f"{level['residual']:.4f}) — the declaration no longer matches the data; re-rule it",
                    detail={"level": level, "level_declared": decl, "symbol_mapped": mapped})
            else:
                raise WriterRefusal(
                    f"{who}: the declared ratio {decl['declared_ratio']} does not explain the level "
                    f"residual {level['residual']:.4f}; not writing",
                    detail={"level": level, "level_declared": decl, "symbol_mapped": mapped})
        elif abs(lr) > LEVEL_TOLERANCE:
            raise WriterRefusal(
                f"{who}: LEVEL IDENTITY fails — the cache's last bar ({level['d_last']}) is "
                f"{level['identity']:.4f} of the provider's reference level, residual "
                f"{level['residual']:.4f} after the provider's dividends; a level change outside the "
                f"identity needs a declaration; not writing",
                detail={"level": level, "symbol_mapped": mapped})
    # OPTION (a): keep the pre-seam span, scaled by the ratio AT the seam. The seam-ratio rail: that
    # ratio must be the tail's rescale — a difference is a step the cache made between the seam and
    # the tail, a convention change, refused unless the mixed-convention declaration explains it.
    seam_record, convention = None, {"whole": EXACT_TR}
    if seam_spec is not None:
        sr = seam_ratio(post["Close"], fetched["Close"], seam_spec["date"])
        tail_log = float(overlap.get("median_log_ratio", 0.0)) if overlap else 0.0
        tol = SEAM_RATIO_FLOORS * (sr["floor"] + float(overlap.get("floor_median", sr["floor"])))
        gap = abs(sr["log_ratio"] - tail_log)
        explained = convention_declared is not None and convention_declared.get("kind") == "mixed_convention_cache"
        if gap > tol and not explained:
            raise WriterRefusal(
                f"{who}: the provider/cache ratio at the seam ({sr['ratio']:.6f} on {sr['date']}) is "
                f"not the tail's rescale ({float(np.exp(tail_log)):.6f}; gap {gap:.2e} > {tol:.2e}) — "
                f"the cache changed convention between the seam and the tail; an undeclared "
                f"mid-span step; not writing",
                detail={"seam_ratio": sr, "overlap": overlap, "symbol_mapped": mapped})
        kept = pre[COLUMNS].copy()
        for col in ("Open", "High", "Low", "Close"):
            kept[col] = kept[col] * sr["ratio"]
        out = with_derived_columns(pd.concat([kept, fetched[fetched.index >= seam_spec["date"]][COLUMNS]]))
        seam_record = {"date": str(pd.Timestamp(seam_spec["date"]).date()), "source": seam_spec["source"],
                       "declared": seam_spec.get("declared"), "n_pre_seam_bars_kept": int(len(kept)),
                       "pre_seam_span": [str(kept.index.min().date()), str(kept.index.max().date())],
                       "seam_ratio": sr, "tail_log_ratio": tail_log, "gap": gap, "tolerance": tol,
                       "gap_explained_by_declaration": bool(explained and gap > tol)}
        # what the KEPT bars ARE: the file's own record when it has one (option (a′): never relabelled)
        seam_record["pre_seam_label_source"] = kept_conv["source"]
        convention = {"pre_seam": kept_conv["pre_seam"], "seam_date": seam_record["date"],
                      "post_seam": seam_spec["post_seam"]}
    else:
        out = with_derived_columns(fetched)
    # The SPLIT-ONLY close as a second column (ruled 2026-10-15; CLOSE_UNADJ): the provider's
    # unadjusted mode over the file's whole span, NaN on bars the provider does not hold — measured,
    # never derived from the total-return close.
    file_start = cached_start if cached_start is not None else new_ticker_start
    unadj_full = providers[provider](symbol, file_start, today, False)
    out[CLOSE_UNADJ] = (unadj_full["Close"].astype(float).reindex(out.index)
                        if not unadj_full.empty else np.nan)
    have = out[CLOSE_UNADJ].notna()
    close_unadj = {"column": CLOSE_UNADJ, "mode": "unadjusted (split-only; the provider's auto_adjust=False)",
                   "n_bars": int(have.sum()), "n_missing": int((~have).sum()),
                   "span": ([str(out.index[have].min().date()), str(out.index[have].max().date())]
                            if have.any() else None)}
    record = WriteRecord(
        ticker=ticker, provider=provider, symbol_mapped=mapped, mode="adjusted",
        span_start=str(out.index.min().date()), span_end=str(out.index.max().date()),
        n_rows=int(len(out)), basis=basis["basis"], basis_detail=basis, overlap=overlap,
        cached_span=(None if cached is None or cached.empty
                     else [str(cached.index.min().date()), str(cached.index.max().date())]),
        written_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        level=level, level_declared=level_declared, adjusted_as_of=str(pd.Timestamp(today).date()),
        seam=seam_record, convention=convention, convention_declared=convention_declared,
        close_unadj=close_unadj, era_tr=None if kept_conv is None else kept_conv["era_tr"])
    if write:
        write_pair_atomically(out, cache_dir / "parquet" / f"{ticker}_1d.parquet",
                              cache_dir / f"{ticker}_1d.csv")
        _write_record_atomically(cache_dir, record)      # pinned under the substrate (R's (c))
        if log_path is not None:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a") as f:
                f.write(json.dumps(asdict(record)) + "\n")
    return record


# ── OPTION (a′): the era-aware pre-seam rewrite (USER RULING 2026-11-12, T-387) ─────

def era_tr_rewrite(ticker: str, cache_dir: Path, *, stooq: Optional[pd.Series],
                   reference_px: Optional[pd.DataFrame], reference_divs: Optional[pd.Series],
                   write: bool = True, conventions: Optional[Dict[str, dict]] = None,
                   provenance: Optional[dict] = None, log_path: Optional[Path] = None) -> dict:
    """Rewrite the PRE-seam span of `<ticker>_1d` under `cache_dir` from the T-082b drip to `era_tr`
    (option (a′)) — OFFLINE (no provider call), or refuse. Returns the record as written (or, with
    `write=False`, as it would be written — the proof-on-a-copy mode; nothing is touched).

    Inputs: the merge record under `cache_dir` (`_merge_meta.json`: the seam, the drip slope b, the
    kept bar count — never fabricated), the raw Stooq close series (`stooq`), and the yfinance
    reference (`reference_px` with `adj_close`/`close`, `reference_divs` by ex-date) — (None, None)
    for a name with no reference: its missed-era bars stay raw Stooq, LABELLED UNVERIFIED.

    Never writes unless: the file is a merged (`both`) file with pre-seam bars whose seam agrees
    with `seam_for`; the span it would rewrite IS the drip (its record's pre-seam label, else the
    seam spec's — an era_tr or whole-written file is refused, so the rewrite never runs twice); a
    prior record's kept bar count equals the merge record's; the shared build (`era_tr.build_file`)
    passes its own rails (the de-drifted cache proportional to raw Stooq; every post-seam Date/OHLCV
    field byte-identical, ATR from the 15th post-seam row and PrevClose from the 2nd byte-identical —
    the first 14 ATR values and the seam row's PrevClose are functions of pre-seam bars and change by
    construction; a carried `close_unadj` byte-identical on every row); and the WRITE-TIME rails pass on its output — the step
    audit (the pre-seam daily returns differ from raw Stooq's ONLY at the restored ex-dates, by
    exactly −log(1 − D/P_prev)) and the splice audit (ONE constant at the seam: the written seam-day
    return is Stooq's own, less any restored dividend ex on the seam bar; the cache's own when raw
    Stooq has no seam bar). The record keeps every prior field and sets `convention.pre_seam` =
    era_tr plus the `era_tr` block (the per-file `unverified_missed_era_spans` /
    `unverified_pre2003_span` the census reads back); a file with no prior record gets one that
    says it was never provider-written."""
    from engines.data_manager import era_tr as et      # lazy: era_tr imports this module's primitives

    cache_dir = Path(cache_dir)
    conventions = load_convention_declarations() if conventions is None else conventions
    meta = load_merge_meta(cache_dir)
    if meta is None:
        raise WriterRefusal(f"{ticker}: no {MERGE_META_NAME} under {cache_dir} — the seam and the drip "
                            f"slope are unknown; the (a′) rewrite is never run on a guess")
    entry = meta.get(ticker)
    if not entry or entry.get("merge_case") != "both" or int(entry.get("n_stooq_pre_seam") or 0) <= 0:
        raise WriterRefusal(f"{ticker}: not a merged file with pre-seam Stooq bars in the merge record — "
                            f"there is no drip span to rewrite", detail={"merge_record": entry})
    seam_spec = seam_for(cache_dir, ticker, conventions)
    if seam_spec is None or pd.Timestamp(seam_spec["date"]) != pd.Timestamp(entry["seam_date"]):
        raise WriterRefusal(f"{ticker}: the seam ({None if seam_spec is None else seam_spec['date']}) does "
                            f"not agree with the merge record's {entry['seam_date']}; not writing")
    seam = pd.Timestamp(entry["seam_date"])
    prior = _read_write_record(cache_dir, ticker)
    kept = kept_pre_seam_convention(ticker, prior, seam_spec)
    if kept["pre_seam"] != DRIP:
        raise WriterRefusal(f"{ticker}: the pre-seam span is {kept['pre_seam']!r} (per the "
                            f"{kept['source']}), not {DRIP!r} — the (a′) rewrite undoes the T-082b "
                            f"drip and applies to a drip span only; not writing",
                            detail={"kept": {k: v for k, v in kept.items() if k != "era_tr"}})
    n_meta = int(entry["n_stooq_pre_seam"])
    n_kept = ((prior or {}).get("seam") or {}).get("n_pre_seam_bars_kept")
    if prior and prior.get("seam") and n_kept != n_meta:
        raise WriterRefusal(f"{ticker}: the write record kept {n_kept} pre-seam bars but the merge "
                            f"record says {n_meta}; not writing")
    if stooq is None or stooq.empty:
        raise WriterRefusal(f"{ticker}: no raw Stooq series — the drip cannot be undone; not writing")
    csv_path = cache_dir / f"{ticker}_1d.csv"
    if not csv_path.exists():
        raise WriterRefusal(f"{ticker}: no {csv_path.name} under {cache_dir}; not writing")
    header, lines = et.read_cache_text(csv_path)
    frame = et.read_cache_frame(csv_path)
    ref = et.analyse_reference(ticker, stooq, reference_px, reference_divs, seam)
    try:
        res = et.build_file(ticker, entry, header, lines, frame, stooq, ref)
    except et.EraTrRefusal as e:
        raise WriterRefusal(f"{ticker}: the (a′) build refused — {e}", detail={"reference": ref.status}) from e
    # the WRITE-TIME rails, on the build's output
    new_close = pd.Series(res.frame["Close"].to_numpy(dtype=float), index=pd.DatetimeIndex(res.frame["Date"]))
    cache_close = pd.Series(frame["Close"].to_numpy(dtype=float), index=pd.DatetimeIndex(frame["Date"]))
    steps = et.step_audit(new_close, stooq, ref.labels, seam)
    splice = et.splice_audit(new_close, cache_close, stooq, ref.labels, seam, res.record["splice"])
    carried = et.carried_text_identical(res.text, header, lines)
    rails = {"step_audit": steps, "splice_audit": splice, "carried_columns_identical": carried}
    if not (steps["pass"] and splice["pass"] and carried):
        raise WriterRefusal(f"{ticker}: a write-time (a′) rail failed — step audit {steps['pass']} "
                            f"({steps['n_unexpected_steps']} unexpected, max dev {steps['max_abs_dev']:.2e}); "
                            f"splice {splice['pass']} (dev {splice['abs_dev']:.2e}); carried columns {carried}; "
                            f"not writing", detail={"rails": rails})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    block = {**res.record, "rails": rails, "rewritten_at": now, "inputs": dict(provenance or {}),
             "prior_pre_seam": {k: v for k, v in kept.items() if k != "era_tr"}}
    seam_date = str(seam.date())
    if prior is not None:
        conv = dict(prior.get("convention") or {})
        record = {**prior, "convention": {"pre_seam": ERA_TR, "seam_date": seam_date,
                                          "post_seam": conv.get("post_seam", seam_spec["post_seam"])},
                  "era_tr": block}
    else:
        dates = pd.DatetimeIndex(frame["Date"])
        record = asdict(WriteRecord(
            ticker=ticker, provider="none (no provider write: the merged file as cached)", symbol_mapped=None,
            mode="era_tr_pre_seam_rewrite (offline; no provider call)",
            span_start=str(dates.min().date()), span_end=str(dates.max().date()), n_rows=int(len(frame)),
            basis="not measured (no provider call)", basis_detail={}, overlap=None,
            cached_span=[str(dates.min().date()), str(dates.max().date())], written_at=now,
            seam={"date": seam_date, "source": seam_spec["source"], "declared": seam_spec.get("declared"),
                  "n_pre_seam_bars_kept": int(res.record["n_pre"]),
                  "pre_seam_span": [res.record["first_bar"], str(dates[res.record["n_pre"] - 1].date())]},
            convention={"pre_seam": ERA_TR, "seam_date": seam_date, "post_seam": seam_spec["post_seam"]},
            era_tr=block))
    if write:
        write_text_pair_atomically(res.text, et.frame_from_text(res.text),
                                   cache_dir / "parquet" / f"{ticker}_1d.parquet", csv_path)
        p = _write_record_path(cache_dir, ticker)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".writing")
        tmp.write_text(json.dumps(record, indent=1, default=str))
        os.replace(tmp, p)
        if log_path is not None:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a") as f:
                f.write(json.dumps(record, default=str) + "\n")
    return record


# ── real providers (network; injected, so tests never touch them) ─────────────────

def yfinance_provider(ticker: str, start: pd.Timestamp, end: pd.Timestamp, adjusted: bool) -> pd.DataFrame:
    """yfinance: auto_adjust=True -> total return; False -> split-adjusted Close."""
    import yfinance as yf
    df = yf.download(ticker, start=str(pd.Timestamp(start).date()),
                     end=str((pd.Timestamp(end) + pd.Timedelta(days=1)).date()),
                     auto_adjust=adjusted, progress=False, actions=False)
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNS)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[COLUMNS].sort_index()


def yfinance_actions(symbol: str) -> pd.DataFrame:
    """yfinance's corporate-actions record (dividends and split factors), tz-naive."""
    import yfinance as yf
    a = yf.Ticker(symbol).actions
    if a is None or a.empty:
        return pd.DataFrame(columns=["Dividends", "Stock Splits"])
    idx = pd.to_datetime(a.index)
    a.index = idx.tz_localize(None) if idx.tz is not None else idx
    return a


#: The default actions record for the universe provider (passed explicitly; never implied).
DEFAULT_ACTIONS: Actions = yfinance_actions

#: The universe provider only. The Alpaca provider is archived
#: (Archive/data_engine/tr_writer_alpaca_provider_2026_10_15.py) — see the module docstring.
DEFAULT_PROVIDERS: Dict[str, Provider] = {UNIVERSE_PROVIDER: yfinance_provider}
