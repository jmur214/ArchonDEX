"""OPTION (a′) — the ERA-AWARE pre-seam convention (`era_tr`): the ONE shared implementation.

USER RULING 2026-11-12: the cutover adopts the T-384 option-(a′) v4 drip fix, amending the
2026-10-22 ruling "option (a)" (which kept T-082b's fitted pre-seam drift, `drip`). Proposal and
pre-declared acceptance test: `docs/Sources/proposal_drip_fix_a_prime_2026-11-11.md`. Moved here
from `scripts/drip_fix_candidate_t384.py` (T-387) so the writer (`tr_writer.era_tr_rewrite`, the
cutover write path) and the T-384 candidate script call the SAME code; the script imports from this
module and keeps only its fetch / acceptance / manifest commands and the v1–v3-only helpers.

THE DEFECT. The canonical cache `data/processed/<T>_1d.csv` merges raw Stooq (before each name's
seam) with Alpaca total return (after it). The T-082b merge (`scripts/merge_stooq_alpaca_substrate.py`)
assumed Stooq is total return and multiplied every pre-seam bar by a fitted exp(a + b·t). Raw Stooq
is dividend-adjusted by ERA (≈ 0 % of each dividend missed for ex-dates 2011-Q2 → 2022-Q4, ≈ 100 %
missed 2003-Q2 → 2011-Q1 and from 2023-Q1, per name before 2003), so b — Stooq's missed 2023+
dividends smeared over the overlap — is applied on top of bars that were already total return and
does not replace the dividends Stooq really missed.

THE CONVENTION (`era_tr`), per merged file with pre-seam bars (`build_file`, pure):
  1. undo the drip: pre-seam closes × exp(−b·(t − seam)) recovers the Stooq series the merge read
     (proven against the raw bundle: the log ratio must be constant to 1e-9, or REFUSE);
  2. Stooq is used AS-IS where it is already total return; every dividend it MISSED is restored in
     full (yfinance D / P_prev), each ex-date labelled by the fraction-missed probe against a
     yfinance reference, with Stooq's transient blocks masked; per-name era edges come from those
     labels, the global edges only where no label can be measured;
  3. a bar with no same-security reference stays RAW Stooq in every era — never approximated —
     and is LABELLED UNVERIFIED (`unverified_missed_era_spans`, `unverified_pre2003_span`);
  4. ONE constant at the seam (the Stooq seam-day return kept);
  5. the post-seam text is copied, byte for byte (and a carried `close_unadj` column on every row).
Nothing here reads or writes a fixed location: every input is passed in.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from engines.data_manager.tr_writer import CLOSE_UNADJ, with_derived_columns

OHLC = ["Open", "High", "Low", "Close"]
#: The cache's eight columns (the T-082b merge's layout).
EXPECTED_HEADER = "Date,Open,High,Low,Close,Volume,ATR,PrevClose"
#: The ONE trailing column a file may carry beyond the eight: the writer's split-only close (the
#: cutover copy's files). It is the price that TRADED, independent of the dividend convention, so
#: the rewrite carries it VERBATIM on every row, pre- and post-seam.
CARRIED_COLUMNS: Tuple[str, ...] = (CLOSE_UNADJ,)
N_CACHE_FIELDS = 8

# ═══════════════════════════════════════════════════════════════════════════════
# The era model — what Stooq's dividend adjustment covers
# ═══════════════════════════════════════════════════════════════════════════════

#: Global fallback ONLY (a name or span with no usable reference). Measured 2026-11-11 by the
#: per-ex-date probe over the universe (proposal §2): Stooq's capture flips in a single week
#: universe-wide — captured → missed between 2003-03-30 and 2003-04-07, missed → captured between
#: 2011-02-20 and 2011-02-21, captured → missed again from 2022-12-19. Before 2003-04-01 the
#: behaviour is PER NAME (BA missed 1980–1999, AEP captured 1971–2003, MO/AA/CAT missed from
#: 2001-Q2): the fallback there is "captured" (the measured majority) and is LABELLED unverified.
GLOBAL_MISSED_ERAS: Tuple[Tuple[pd.Timestamp, pd.Timestamp], ...] = (
    (pd.Timestamp("2003-04-01"), pd.Timestamp("2011-02-21")),
    (pd.Timestamp("2022-12-19"), pd.Timestamp("2262-01-01")),
)
#: Era blocks for the neighbour rule: a one-sided neighbour may only lend its label inside its
#: own block (it never extrapolates across a universe-wide flip).
GLOBAL_BLOCK_EDGES = pd.DatetimeIndex(["2003-04-01", "2011-02-21", "2022-12-19"])
PROBE_LEVEL_BARS = 1           # A1 (v3): the nearest CLEAN bar each side — v1's 3-return window when
                               # no transient block is near (v2's 5-bar medians made σ(m) √(10/3)× larger
                               # and lost the measured labels of noisy years: CMI/AXP/RTX 2000-01)
BLIP_MIN = 0.0025              # A1: |Δlog stooq − Δlog ref| above this may open a transient offset …
BLIP_MAX_BARS = 15             # … that a later bar undoes within this many bars …
BLIP_REVERT_TOL = 0.15         # … to within 15 % of its size
PRE_REFERENCE_STUB_DAYS = 45   # A3: Stooq bars this close before the reference's first bar are covered
NOISE_WINDOW = 127             # trading days around an ex-date for the robust noise scale
CONFIDENT_SM = 0.15            # σ(m) at or below this → the ex-date is MEASURED (0/1 are ≥ 3.3σ apart)
MISSED_M = 0.5                 # m ≥ 0.5 → Stooq missed the dividend
MAX_DIV_FRACTION = 0.95        # D/P_prev clip (a spin-off valued at most 95 % of the parent)
IDENTITY_MED_ABS_D = 0.004     # a reference year is the SAME security when median |Δr| ≤ this …
IDENTITY_CORR = 0.95           # … or the daily-return correlation is at least this
SEAM_TEXT_ROWS = 14            # ATR(14) + PrevClose: post-seam rows whose DERIVED fields change
FULL_YEAR_BARS = 200           # a name-year counts toward the cross-sectional yield median from here
PROPORTIONAL_TOL = 1e-9        # rule 1: the de-drifted cache vs raw Stooq, log-ratio range
#: |daily log-return difference vs raw Stooq| below this is float noise (the v4 step audit; the
#: writer's write-time rail). v4 measured a max deviation of 9.4e-16 over 575 files.
STEP_TOL = 1e-10
UNVERIFIED_MISSED_ERA_BIAS = ("raw Stooq kept: UNDER-counts by the name's dividend yield over these "
                              "spans IF it paid; exact if it did not (payer status not established)")


class EraTrRefusal(RuntimeError):
    """The (a′) build will not produce this file: a load-bearing check failed (fail closed)."""


def global_missed(dates: pd.DatetimeIndex) -> np.ndarray:
    """Boolean mask: the date lies in a universe-wide missed era (fallback rule)."""
    out = np.zeros(len(dates), dtype=bool)
    for lo, hi in GLOBAL_MISSED_ERAS:
        out |= (dates >= lo) & (dates < hi)
    return out


def global_block(dates: pd.DatetimeIndex) -> np.ndarray:
    return GLOBAL_BLOCK_EDGES.searchsorted(dates, side="right")


def align_reference(stooq: pd.Series, px: pd.DataFrame) -> pd.DataFrame:
    """Stooq close + yfinance (adj_close, close) on their common, strictly positive dates."""
    j = pd.concat([stooq.rename("stooq"), px[["adj_close", "close"]]], axis=1, join="inner").dropna()
    return j[(j > 0).all(axis=1)].sort_index()


def year_identity(j: pd.DataFrame) -> pd.DataFrame:
    """Per calendar year: is the reference the SAME security as the Stooq series?"""
    lr = np.log(j).diff().dropna()
    d = (lr["stooq"] - lr["adj_close"]).abs()
    yrs = lr.index.year
    med = d.groupby(yrs).median()
    corr = lr.groupby(yrs).apply(
        lambda g: float(np.corrcoef(g["stooq"], g["adj_close"])[0, 1]) if len(g) > 5
        and g["stooq"].std() > 1e-12 and g["adj_close"].std() > 1e-12 else np.nan)
    out = pd.DataFrame({"med_abs_d": med, "corr": corr, "n": d.groupby(yrs).size()})
    out["valid"] = (out["med_abs_d"] <= IDENTITY_MED_ABS_D) | (out["corr"] >= IDENTITY_CORR)
    out.index.name = "year"
    return out


def transient_offsets(d: np.ndarray) -> np.ndarray:
    """Bars that sit inside a TRANSIENT level offset of Stooq against the reference (amendment A1).

    A jump d[a] (|d| > BLIP_MIN) that a later d[b], a < b ≤ a + BLIP_MAX_BARS, undoes to within
    BLIP_REVERT_TOL of its size: bars a … b−1 carry the offset. Measured 2026-11-11 in raw Stooq
    vs yfinance: 4,517 such offsets over 414 names since 1995 — 2008-05-07 (214 names), 2009-01-23
    (162), 2011-03-21 (102), the 2013 month-ends (≈ 85 each), 2013-12-19 → 2014-01-03, 2015-03-12
    — most the size of one quarterly dividend. A one-day-late adjustment is the 1-bar case."""
    n = len(d)
    a = np.flatnonzero(np.abs(d) > BLIP_MIN)
    if n == 0 or len(a) == 0:
        return np.zeros(n, dtype=bool)
    k = np.arange(1, BLIP_MAX_BARS + 1)
    b = a[:, None] + k[None, :]
    inside = b < n
    bc = np.minimum(b, n - 1)
    da = d[a][:, None]
    hit = inside & (np.abs(d[bc]) > BLIP_MIN) & (np.abs(da + d[bc]) < BLIP_REVERT_TOL * np.abs(da))
    has = hit.any(axis=1)
    starts = a[has]
    ends = (a + 1 + np.argmax(hit, axis=1))[has]          # b = a + k[first hit]
    edge = np.zeros(n + 1, dtype=int)
    np.add.at(edge, starts, 1)
    np.add.at(edge, ends, -1)
    return np.cumsum(edge)[:n] > 0


def probe_exdates(j: pd.DataFrame, divs: Optional[pd.Series], k_bars: int = PROBE_LEVEL_BARS) -> pd.DataFrame:
    """The fraction of each dividend Stooq MISSED, measured against the reference (amendment A1:
    a LEVEL-SHIFT probe; v1's ex-day ± 1 sum was confused by Stooq's transient offsets).

    Levels:  X(t) = Σ_{≤t}(Δlog adj − Δlog stooq)  — what Stooq lacks relative to the reference
             Y(t) = Σ_{≤t}(Δlog adj − Δlog close)  — the dividends the reference applied
    For ex-date e (mapped to the first common bar p ≥ e), with PRE = the last k CLEAN bars ≤ p−2 and
    POST = the first k CLEAN bars ≥ p+1 (clean = outside a transient offset; the skipped bars make
    it robust to a one-day-early or one-day-late adjustment):
        x = median X(POST) − median X(PRE);  y = median Y(POST) − median Y(PRE);  m = x / y
    m = 0: Stooq captured it; m = 1: Stooq missed it.
    σ(m) = robust daily noise of (Δlog stooq − Δlog adj) on clean non-event bars × √(span) / |y|,
    span = the daily returns between the two nearest clean bars (+ 2(k−1)): 3 when no block is near."""
    cols = ["ex_date", "day", "pos", "D", "P_prev", "log_f", "y_lvl", "x_lvl", "m", "sm", "confident",
            "offset_bars_near"]
    if divs is None or len(divs) == 0 or len(j) < 4 * k_bars + 4:
        return pd.DataFrame(columns=cols)
    lr = np.log(j).diff().fillna(0.0)
    d = (lr["stooq"] - lr["adj_close"]).to_numpy()
    offset = transient_offsets(d)
    lvl_x = np.cumsum(lr["adj_close"].to_numpy() - lr["stooq"].to_numpy())
    lvl_y = np.cumsum(lr["adj_close"].to_numpy() - lr["close"].to_numpy())
    pos = j.index.searchsorted(divs.index, side="left")
    clean_pos = np.flatnonzero(~offset)
    kp = clean_pos.searchsorted(pos - 1, side="left")      # clean bars < p−1 are clean_pos[:kp]
    kq = clean_pos.searchsorted(pos + 1, side="left")      # clean bars ≥ p+1 start at clean_pos[kq]
    ok = (pos >= 2) & (pos < len(j)) & (kp >= k_bars) & (kq + k_bars <= len(clean_pos))
    pos, dv, kp, kq = pos[ok], divs[ok], kp[ok], kq[ok]
    if len(pos) == 0:
        return pd.DataFrame(columns=cols)
    ar = np.arange(k_bars)
    pre_idx = clean_pos[kp[:, None] - k_bars + ar[None, :]]
    post_idx = clean_pos[kq[:, None] + ar[None, :]]
    x_lvl = np.median(lvl_x[post_idx], axis=1) - np.median(lvl_x[pre_idx], axis=1)
    y_lvl = np.median(lvl_y[post_idx], axis=1) - np.median(lvl_y[pre_idx], axis=1)
    event = np.zeros(len(j), dtype=bool)
    for k in (-1, 0, 1):                                   # three fixed offsets, not a data loop
        event[np.clip(pos + k, 0, len(j) - 1)] = True
    d_abs = pd.Series(np.abs(d)).where(~event & ~offset)
    sig = (d_abs.rolling(NOISE_WINDOW, center=True, min_periods=30).median() * 1.4826).to_numpy()[pos]
    near = pd.Series(offset.astype(int)).rolling(2 * k_bars + 5, center=True, min_periods=1).sum().to_numpy()[pos]
    p_prev = j["close"].to_numpy()[pos - 1]
    frac = np.minimum(dv.to_numpy() / p_prev, MAX_DIV_FRACTION)
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.where(np.abs(y_lvl) > 1e-12, x_lvl / y_lvl, np.nan)
        span = (post_idx[:, 0] - pre_idx[:, -1]) + 2 * (k_bars - 1)
        sm = np.where(np.abs(y_lvl) > 1e-12, sig * np.sqrt(span) / np.abs(y_lvl), np.inf)
    sm = np.where(np.isfinite(sm), sm, np.inf)
    return pd.DataFrame({
        "ex_date": dv.index, "day": j.index[pos], "pos": pos, "D": dv.to_numpy(), "P_prev": p_prev,
        "log_f": np.log1p(-frac), "y_lvl": y_lvl, "x_lvl": x_lvl, "m": m, "sm": sm,
        "confident": np.isfinite(m) & (sm <= CONFIDENT_SM), "offset_bars_near": near.astype(int)})


def label_exdates(probe: pd.DataFrame) -> pd.DataFrame:
    """missed / captured per ex-date. MEASURED where confident; otherwise the confident neighbours
    (both agree, or the one present lies in the same global block); otherwise the global rule."""
    out = probe.copy()
    if out.empty:
        out["missed"] = pd.Series(dtype=bool)
        out["label_source"] = pd.Series(dtype=object)
        return out
    out = out.sort_values("day").reset_index(drop=True)
    days = pd.DatetimeIndex(out["day"])
    blk = global_block(days)
    conf = out["confident"].to_numpy(dtype=bool)
    lab = np.where(conf, (out["m"].to_numpy() >= MISSED_M).astype(float), np.nan)
    lab_s = pd.Series(lab)
    blk_conf = pd.Series(np.where(conf, blk, np.nan))
    prev_l, next_l = lab_s.ffill().to_numpy(), lab_s.bfill().to_numpy()
    prev_b, next_b = blk_conf.ffill().to_numpy(), blk_conf.bfill().to_numpy()
    glob = global_missed(days).astype(float)
    both = ~np.isnan(prev_l) & ~np.isnan(next_l)
    agree = both & (prev_l == next_l)
    only_prev = ~np.isnan(prev_l) & np.isnan(next_l) & (prev_b == blk)
    only_next = np.isnan(prev_l) & ~np.isnan(next_l) & (next_b == blk)
    final = np.select([conf, agree, only_prev, only_next], [lab, prev_l, prev_l, next_l], default=glob)
    source = np.select([conf, agree, only_prev | only_next], ["measured", "neighbours", "neighbour_same_block"],
                       default="global")
    out["missed"] = final.astype(bool)
    out["label_source"] = source
    return out


def missed_log_factor(dates: pd.DatetimeIndex, ex_days: pd.DatetimeIndex, log_f: np.ndarray) -> np.ndarray:
    """Back-adjustment for the missed dividends: logM(t) = Σ_{e > t} log(1 − D_e/P_e,prev), on the
    Stooq calendar `dates` (an ex-date that is not a bar lands on the next bar). Ex-dates after the
    last date contribute to every bar."""
    pos = dates.searchsorted(ex_days, side="left")
    acc = np.zeros(len(dates) + 1)
    np.add.at(acc, pos, log_f)
    total = acc.sum()
    # bar i is scaled by every event at a position > i
    return total - np.cumsum(acc)[: len(dates)]


# ═══════════════════════════════════════════════════════════════════════════════
# Per-name reference analysis (probe → labels → reference coverage)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NameReference:
    """What the yfinance reference says about one name's Stooq series."""
    ticker: str
    status: str                                   # "reference" | "no_prices" | "no_overlap" | "no_raw_stooq"
    labels: pd.DataFrame                          # labelled ex-dates (reference years only)
    valid_years: List[int] = field(default_factory=list)
    invalid_years: List[int] = field(default_factory=list)
    ref_first: Optional[pd.Timestamp] = None      # first common Stooq∩yf day
    yearly_yield: Optional[pd.Series] = None      # log(TR/PR) per valid calendar year

    def covered(self, dates: pd.DatetimeIndex) -> np.ndarray:
        """Bars whose year has a valid same-security reference — plus (amendment A3) a stub of at
        most PRE_REFERENCE_STUB_DAYS before the reference's first bar: a vendor IPO / relisting date
        offset (BLDR, LYV, TDC by days; CHTR's 2009-12 relisting by 34 days), not a missing source."""
        if self.status != "reference" or self.ref_first is None:
            return np.zeros(len(dates), dtype=bool)
        stub = (dates < self.ref_first) & (dates >= self.ref_first - pd.Timedelta(days=PRE_REFERENCE_STUB_DAYS))
        return ((dates >= self.ref_first) & np.isin(dates.year, self.valid_years)) | stub


def empty_labels() -> pd.DataFrame:
    """The labelled-ex-date frame of a name with no usable reference (no ex-date labelled)."""
    return label_exdates(probe_exdates(pd.DataFrame(), None))


def _naive_day_index(idx: pd.Index) -> pd.DatetimeIndex:
    out = pd.DatetimeIndex(idx)
    if out.tz is not None:
        out = out.tz_localize(None)
    return out.normalize()


def analyse_reference(ticker: str, stooq_full: pd.Series, px: Optional[pd.DataFrame],
                      divs: Optional[pd.Series], until: pd.Timestamp) -> NameReference:
    """Probe every reference ex-date up to `until` (the seam) and label it."""
    if px is None or divs is None:
        return NameReference(ticker, "no_prices", empty_labels())
    j = align_reference(stooq_full, px)
    if len(j) < 2 * NOISE_WINDOW:
        return NameReference(ticker, "no_overlap", empty_labels())
    ident = year_identity(j)
    valid = sorted(int(y) for y in ident.index[ident["valid"]])
    invalid = sorted(int(y) for y in ident.index[~ident["valid"]])
    divs = pd.Series(divs.to_numpy(dtype=float), index=_naive_day_index(divs.index)).sort_index()
    d_in = divs[(divs.index <= until) & (divs.index >= j.index[0])]
    probe = probe_exdates(j, d_in)
    if not probe.empty:
        probe = probe[np.isin(pd.DatetimeIndex(probe["day"]).year, valid)]
        probe = probe[pd.DatetimeIndex(probe["day"]) <= until]
    labels = label_exdates(probe)
    lr = np.log(j[["adj_close", "close"]]).diff().dropna()
    grp = (lr["adj_close"] - lr["close"]).groupby(lr.index.year)
    yy, n_y = grp.sum(), grp.size()
    yy = yy[yy.index.isin(valid) & (n_y >= FULL_YEAR_BARS)]   # full years only, for the medians
    return NameReference(ticker, "reference", labels, valid, invalid, j.index[0], yy)


def era_runs(labels: pd.DataFrame) -> List[dict]:
    """Contiguous runs of MISSED ex-dates (the name's measured missed eras), for the record."""
    if labels.empty:
        return []
    lab = labels.sort_values("day")
    flag = lab["missed"].to_numpy(dtype=bool)
    run_id = np.cumsum(np.r_[True, flag[1:] != flag[:-1]])
    runs = []
    for rid in np.unique(run_id[flag]):
        sel = lab[run_id == rid]
        runs.append({"first": str(pd.Timestamp(sel["day"].iloc[0]).date()),
                     "last": str(pd.Timestamp(sel["day"].iloc[-1]).date()), "n": int(len(sel)),
                     "n_measured": int((sel["label_source"] == "measured").sum())})
    return runs


def mask_runs(dates: pd.DatetimeIndex, mask: np.ndarray) -> List[List[str]]:
    """Contiguous runs of True in `mask`, as [first date, last date] pairs (for the record)."""
    if not mask.any():
        return []
    m = mask.astype(int)
    edges = np.diff(np.r_[0, m, 0])
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1) - 1
    return [[str(dates[a].date()), str(dates[b].date())] for a, b in zip(starts, ends)]


# ═══════════════════════════════════════════════════════════════════════════════
# Readers (every location is an argument)
# ═══════════════════════════════════════════════════════════════════════════════

def raw_stooq_index(raw_dir: Path) -> Dict[str, str]:
    """Ticker -> path of the raw Stooq daily file under `raw_dir` (`<raw_dir>/*/*/<t>.us.txt`). A
    ticker found under two exchange folders is AMBIGUOUS and raises (never a last-one-wins pick)."""
    out: Dict[str, str] = {}
    for p in sorted(Path(raw_dir).glob("*/*/*.us.txt")):
        t = p.name[: -len(".us.txt")].upper().replace("-", ".")
        if t in out:
            raise ValueError(f"raw Stooq: {t} is under two folders ({out[t]}, {p}) — ambiguous")
        out[t] = str(p)
    return out


def read_raw_stooq(path: str) -> pd.Series:
    df = pd.read_csv(path, usecols=["<DATE>", "<CLOSE>"])
    idx = pd.to_datetime(df["<DATE>"].astype(str), format="%Y%m%d")
    return pd.Series(df["<CLOSE>"].astype(float).values, index=idx, name="stooq").sort_index()


def read_yf(ticker: str, yf_dir: Path) -> Tuple[Optional[pd.DataFrame], Optional[pd.Series]]:
    """Cached yfinance (adj_close, close) and dividends. (None, None) when prices are absent:
    yfinance answers an EMPTY dividend series for a delisted symbol, so dividends without prices
    are never read as "no dividends"."""
    px_p, dv_p = Path(yf_dir) / f"{ticker}.parquet", Path(yf_dir) / f"{ticker}__div.parquet"
    if not px_p.exists() or not dv_p.exists():
        return None, None
    px = pd.read_parquet(px_p)
    px.index = _naive_day_index(px.index)
    dv = pd.read_parquet(dv_p)["dividend"].astype(float)
    dv.index = _naive_day_index(dv.index)
    dv = dv[dv > 0].groupby(level=0).sum().sort_index()
    return px.sort_index(), dv


def read_cache_text(csv_path: Path) -> Tuple[str, List[str]]:
    """A cached CSV as (header, data lines) — text, so post-seam rows can be copied verbatim."""
    with open(csv_path, "r", newline="") as fh:
        lines = fh.read().split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return lines[0], lines[1:]


def read_cache_frame(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, float_precision="round_trip")
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def frame_from_text(text: str) -> pd.DataFrame:
    """The parquet twin of a written csv: parsed FROM the text (round trip), Date index at
    microsecond resolution — the cache's own parquet layout (canonical, the cutover copy and v4)."""
    df = pd.read_csv(io.StringIO(text), float_precision="round_trip")
    df["Date"] = pd.to_datetime(df["Date"]).astype("datetime64[us]")
    return df.set_index("Date")


# ═══════════════════════════════════════════════════════════════════════════════
# The per-file build (pure: every input is passed in; nothing is read or written)
# ═══════════════════════════════════════════════════════════════════════════════

def recompute_derived(df: pd.DataFrame) -> pd.DataFrame:
    """ATR(14) + PrevClose on a Date-column frame — the writer's `with_derived_columns`, the
    T-082b merge's own arithmetic (`_recompute_derived`)."""
    return with_derived_columns(df.set_index("Date")).reset_index()


@dataclass
class BuildResult:
    ticker: str
    text: str
    frame: pd.DataFrame
    record: dict


def carried_columns(ticker: str, header: str) -> Tuple[str, ...]:
    """The trailing columns past the cache's eight that the build carries verbatim: none (the
    cache's layout) or exactly CARRIED_COLUMNS (the cutover copy's). Anything else REFUSES."""
    if header == EXPECTED_HEADER:
        return ()
    if header == ",".join([EXPECTED_HEADER, *CARRIED_COLUMNS]):
        return CARRIED_COLUMNS
    raise EraTrRefusal(f"{ticker}: unexpected header {header!r}")


def _carried_tails(lines: List[str]) -> List[Optional[str]]:
    """The text past the cache's eight fields on every line (None where a line has no such text)."""
    return [ln.split(",", N_CACHE_FIELDS)[N_CACHE_FIELDS] if ln.count(",") >= N_CACHE_FIELDS else None
            for ln in lines]


def _text_fields(lines: List[str], n: int) -> np.ndarray:
    """The first n comma-separated fields of every line (an object array; a missing field is '')."""
    f = pd.Series(lines, dtype=object).str.split(",", n=n, expand=True)
    f = f.reindex(columns=range(n)).fillna("")
    return f.to_numpy(dtype=object)


def check_text_bytes(new_lines: List[str], cache_lines: List[str], n_pre: int) -> Optional[str]:
    """The write-time byte rule on the cache's eight fields: every post-seam row's Date/OHLCV text
    identical; ATR from the 15th post-seam row and PrevClose from the 2nd identical; every pre-seam
    row's Date and Volume identical. None = pass, else the first violation (row order)."""
    if len(new_lines) != len(cache_lines):
        return "row count changed"
    new_f, old_f = _text_fields(new_lines, N_CACHE_FIELDS), _text_fields(cache_lines, N_CACHE_FIELDS)
    eq = new_f == old_f
    row = np.arange(len(new_lines))
    post = row >= n_pre
    bad_ohlcv = post & ~eq[:, :6].all(axis=1)
    bad_atr = (row >= n_pre + SEAM_TEXT_ROWS) & ~eq[:, 6]
    bad_prev = (row > n_pre) & ~eq[:, 7]
    bad_post = bad_ohlcv | bad_atr | bad_prev
    if bad_post.any():
        i = int(np.flatnonzero(bad_post)[0])
        if bad_ohlcv[i]:
            return f"post-seam row {i} OHLCV text differs: {list(new_f[i, :6])} vs {list(old_f[i, :6])}"
        return f"post-seam row {i} {'ATR' if bad_atr[i] else 'PrevClose'} text differs"
    bad_pre = ~post & ~(eq[:, 0] & eq[:, 5])
    if bad_pre.any():
        return f"pre-seam row {int(np.flatnonzero(bad_pre)[0])} Date/Volume text differs"
    return None


def build_file(ticker: str, meta_rec: dict, cache_header: str, cache_lines: List[str],
               cache_df: pd.DataFrame, stooq_raw: pd.Series, ref: NameReference) -> BuildResult:
    """Option (a′) for one merged file. Pure: every input is passed in; nothing is read or written.

    A bar with no same-security payer reference is NEVER moved off raw Stooq — not even inside a
    global missed era. It is LABELLED instead (`unverified_missed_era_spans`, with the bias
    direction), because no citable source establishes whether the name paid at all (v4, the
    independent review's MAJOR-1). A carried `close_unadj` column is copied verbatim on every row."""
    extra = carried_columns(ticker, cache_header)
    if len(cache_lines) != len(cache_df):
        raise EraTrRefusal(f"{ticker}: text rows {len(cache_lines)} != parsed rows {len(cache_df)}")
    seam = pd.Timestamp(meta_rec["seam_date"])
    b = float(meta_rec.get("fit_slope_per_day") or 0.0)
    dates = pd.DatetimeIndex(cache_df["Date"])
    pre = dates < seam
    n_pre = int(pre.sum())
    if n_pre != int(meta_rec.get("n_stooq_pre_seam") or -1):
        raise EraTrRefusal(f"{ticker}: {n_pre} pre-seam bars != merge record {meta_rec.get('n_stooq_pre_seam')}")
    if n_pre == 0 or n_pre == len(cache_df) or dates[n_pre] != seam:
        raise EraTrRefusal(f"{ticker}: the seam bar {seam.date()} is not the first post-seam row")
    pre_dates = dates[:n_pre]
    dt = (pre_dates - seam).days.to_numpy(dtype=float)
    undrift = np.exp(-b * dt)
    s_pre = cache_df["Close"].to_numpy()[:n_pre] * undrift

    # 1. the de-drifted cache IS the Stooq series the merge read (to the float floor), or refuse
    raw_on_pre = stooq_raw.reindex(pre_dates)
    if raw_on_pre.isna().any():
        raise EraTrRefusal(f"{ticker}: {int(raw_on_pre.isna().sum())} pre-seam bars absent from raw Stooq")
    log_lam = np.log(s_pre / raw_on_pre.to_numpy())
    if float(log_lam.max() - log_lam.min()) > PROPORTIONAL_TOL:
        raise EraTrRefusal(f"{ticker}: de-drifted cache is not proportional to raw Stooq "
                           f"(log-ratio range {float(log_lam.max() - log_lam.min()):.2e})")
    lam = float(np.exp(np.median(log_lam)))

    # 2. the dividends Stooq missed (measured labels) — up to and including the seam day
    covered = ref.covered(pre_dates)
    lab = ref.labels
    add = lab[lab["missed"]] if not lab.empty else lab
    log_m = (missed_log_factor(pre_dates.append(pd.DatetimeIndex([seam])),
                               pd.DatetimeIndex(add["day"]), add["log_f"].to_numpy())[:n_pre]
             if len(add) else np.zeros(n_pre))
    # 3. v4: NO approximation. A no-reference bar in a missed era stays raw Stooq and is LABELLED:
    #    if the name paid, those spans under-count by its (unknown) yield; if it did not, they are exact.
    unverified_missed = (~covered) & global_missed(pre_dates)
    log_a = np.zeros(n_pre)

    # 4. ONE constant at the seam: the Stooq seam-day return is kept
    c_seam = float(cache_df["Close"].iloc[n_pre])
    base = s_pre * np.exp(log_m + log_a)
    if seam in stooq_raw.index:
        k = c_seam / (lam * float(stooq_raw.loc[seam]))
        splice = "stooq_seam_return"
    else:
        k = float(cache_df["Close"].iloc[n_pre - 1]) / float(base[-1])
        splice = "cache_seam_return_kept (raw Stooq has no seam bar)"
    factor = undrift * np.exp(log_m + log_a) * k

    out = cache_df[["Date"] + OHLC + ["Volume"]].copy()
    for col in OHLC:
        vals = out[col].to_numpy(dtype=float).copy()
        vals[:n_pre] = vals[:n_pre] * factor
        out[col] = vals
    out = recompute_derived(out)
    # post-seam derived fields beyond the seam's reach are the cache's own values (text-identical)
    keep_atr = np.arange(len(out)) >= n_pre + SEAM_TEXT_ROWS
    out.loc[keep_atr, "ATR"] = cache_df.loc[keep_atr, "ATR"].to_numpy()
    keep_prev = np.arange(len(out)) > n_pre
    out.loc[keep_prev, "PrevClose"] = cache_df.loc[keep_prev, "PrevClose"].to_numpy()
    text = out.to_csv(index=False, date_format="%Y-%m-%d")

    # 5. post-seam bytes: OHLCV identical on every post-seam row; ATR from seam+14; PrevClose from seam+1
    new_lines = text.split("\n")[1:-1]
    why = check_text_bytes(new_lines, cache_lines, n_pre)
    if why is not None:
        raise EraTrRefusal(f"{ticker}: {why}")
    n_post = len(cache_lines) - n_pre
    if extra:   # the carried column(s), VERBATIM from the cache's own text on every row
        tails = _carried_tails(cache_lines)
        if any(t is None for t in tails):
            raise EraTrRefusal(f"{ticker}: a row lacks the carried column(s) {list(extra)} its header names")
        text = "\n".join([cache_header] + [a + "," + t for a, t in zip(new_lines, tails)]) + "\n"
        for col in extra:
            out[col] = cache_df[col].to_numpy()

    new_close = out["Close"].to_numpy()
    seam_ret_old = c_seam / float(cache_df["Close"].iloc[n_pre - 1]) - 1.0
    seam_ret_new = c_seam / float(new_close[n_pre - 1]) - 1.0
    src_counts = (add["label_source"].value_counts().to_dict() if len(add) else {})
    n_lab = int(len(lab))
    exceptions = 0
    if n_lab:
        g = global_missed(pd.DatetimeIndex(lab["day"]))
        exceptions = int(((lab["label_source"] == "measured") & (lab["missed"].to_numpy() != g)).sum())
    unverified = (~covered) & (pre_dates < GLOBAL_MISSED_ERAS[0][0])
    record = {
        "ticker": ticker, "seam": str(seam.date()), "b_per_day": b,
        "b_pct_per_year": b * 365.25 * 100, "n_pre": n_pre, "n_post": n_post,
        "first_bar": str(pre_dates[0].date()), "lambda_raw": lam, "k_splice": k, "splice": splice,
        "seam_ret_cache": seam_ret_old, "seam_ret_candidate": seam_ret_new,
        "reference": ref.status, "ref_first": str(ref.ref_first.date()) if ref.ref_first is not None else None,
        "invalid_years": ref.invalid_years,
        "covered_bars": int(covered.sum()),
        "n_div_labelled": n_lab, "n_div_added": int(len(add)),
        "added_by_source": {str(k_): int(v) for k_, v in src_counts.items()},
        "n_measured": int((lab["label_source"] == "measured").sum()) if n_lab else 0,
        "measured_exceptions_to_global": exceptions,
        "missed_runs": era_runs(lab),
        "approx_bars": 0, "approx_years": [],          # v4: the approximation is never applied
        "unverified_missed_era_bars": int(unverified_missed.sum()),
        "unverified_missed_era_spans": mask_runs(pre_dates, unverified_missed),
        "unverified_missed_era_bias": UNVERIFIED_MISSED_ERA_BIAS if unverified_missed.any() else None,
        "unverified_pre2003_bars": int(unverified.sum()),
        "unverified_pre2003_span": ([str(pre_dates[unverified][0].date()), str(pre_dates[unverified][-1].date())]
                                    if unverified.any() else None),
        "log_added_total": float(log_m[0] + log_a[0]) if n_pre else 0.0,
        "post_seam_derived_rows_changed": int(min(SEAM_TEXT_ROWS, n_post)),
        "carried_columns": list(extra),
    }
    return BuildResult(ticker, text, out, record)


# ═══════════════════════════════════════════════════════════════════════════════
# Write-time rails on a build's OUTPUT (the writer runs them before anything lands)
# ═══════════════════════════════════════════════════════════════════════════════

def step_audit(new_close: pd.Series, stooq_raw: pd.Series, labels: pd.DataFrame, seam: pd.Timestamp) -> dict:
    """R3 at write time: the pre-seam daily log returns may differ from raw Stooq's ONLY at the
    labelled ADDED ex-dates, and there by exactly −log(1 − D/P_prev). Anything else is a price that
    entered from somewhere other than raw Stooq and the restored dividends."""
    pre_c = new_close[new_close.index < seam]
    raw_pre = stooq_raw.reindex(pre_c.index)
    step = np.diff(np.log(pre_c.to_numpy() / raw_pre.to_numpy()))        # step[i-1] = bar i
    expected = np.zeros(len(pre_c) + 1)
    if not labels.empty:
        lab = labels[labels["missed"].to_numpy(dtype=bool) & (pd.DatetimeIndex(labels["day"]) < seam)]
        pos = pre_c.index.searchsorted(pd.DatetimeIndex(lab["day"]), side="left")
        np.add.at(expected, pos, -lab["log_f"].to_numpy(dtype=float))
    exp_bar = expected[1:len(pre_c)]
    dev = np.abs(step - exp_bar)
    unexpected = (np.abs(step) > STEP_TOL) & (exp_bar == 0)
    return {"n_steps_expected": int((exp_bar != 0).sum()), "n_unexpected_steps": int(unexpected.sum()),
            "max_abs_dev": float(dev.max()) if len(dev) else 0.0,
            "pass": bool(not unexpected.any() and (dev.max() <= STEP_TOL if len(dev) else True))}


def splice_audit(new_close: pd.Series, cache_close: pd.Series, stooq_raw: pd.Series,
                 labels: pd.DataFrame, seam: pd.Timestamp, splice: str) -> dict:
    """The ONE constant at the seam, at write time. The written seam-day log return must be Stooq's
    own seam-day return less the missed dividends whose ex-date maps to the seam bar (splice
    `stooq_seam_return`), or the cache's own seam-day return (when raw Stooq has no seam bar)."""
    n_pre = int((new_close.index < seam).sum())
    got = float(np.log(new_close.iloc[n_pre] / new_close.iloc[n_pre - 1]))
    if splice == "stooq_seam_return":
        prev_day = new_close.index[n_pre - 1]
        at_seam = 0.0
        if not labels.empty:
            sel = labels["missed"].to_numpy(dtype=bool) & (pd.DatetimeIndex(labels["day"]) == seam)
            at_seam = float(labels.loc[sel, "log_f"].sum())
        want = float(np.log(stooq_raw.loc[seam] / stooq_raw.loc[prev_day])) - at_seam
        tol = 10 * PROPORTIONAL_TOL          # the proportionality slack of rule 1, plus float noise
    else:
        want = float(np.log(cache_close.iloc[n_pre] / cache_close.iloc[n_pre - 1]))
        tol = 1e-12
    return {"splice": splice, "seam_log_return": got, "target_log_return": want,
            "abs_dev": abs(got - want), "tolerance": tol, "pass": bool(abs(got - want) <= tol)}


def carried_text_identical(new_text: str, cache_header: str, cache_lines: List[str]) -> bool:
    """Every carried column's text is the cache's own, on every row (the build copies it)."""
    if not carried_columns("?", cache_header):
        return True
    new_lines = new_text.split("\n")[1:-1]
    return len(new_lines) == len(cache_lines) and _carried_tails(new_lines) == _carried_tails(cache_lines)
