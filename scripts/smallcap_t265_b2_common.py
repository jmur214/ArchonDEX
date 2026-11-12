"""scripts/smallcap_t265_b2_common.py — shared machinery for the B-2 (T-381) harnesses.

Implements the FROZEN pre-registration `docs/Sources/prereg_b2_smallcap_t265_2026-11-11.md`
(§3–§4 + AMENDMENT 1). Standalone: never touches `BacktestController`, `engines/`, the governor
or the run registry; reads only the T-265 stages, the SEC Form 345 zips and the T-256 TR twins.
No network, no `.env`.

Design laws (each locked in tests/test_smallcap_t265_b2.py):
  * A SECURITY is a price-file SEGMENT: traded bars only (volume > 0), split at no-trade runs of
    >= 63 market days (reused tickers). The phantom zero-volume tail is dropped; the last traded
    bar of a segment is its DEATH when it is earlier than DEATH_CUTOFF (amendment A1.2).
  * A death applies D (BASE -30% Shumway / STRESS -100% / LAST-PRICE 0) after the last traded
    close; the proceeds earn BIL TR.
  * Missing is counted, never filled; a load-bearing input that is missing HALTS (exit 2).
  * ONE bootstrap draw per window on the MONTH INDICES (the B-1 pattern): every arm, twin and
    diagnostic in a window sees the same resampled months (paired). Auto block length.
  * Every census count the prereg declares for an input the harness CONSUMES (§3.3 price-file
    artefacts, §3.5 Form 4 + join, §3.6 windows) is recomputed exactly as the committed census
    script computed it and HALTS on any mismatch (§4.5). The check record goes to
    `<stem>_census_check.json`, beside — never inside — the canonical results. §3.1's EDGAR-
    cessation and in-band-death tables describe inputs the harness never reads; they are
    reproduced by `scripts/b2_census_t381/` only.
  * A statistic that cannot be evaluated (too few observations) raises NotEvaluable: the gate
    path HALTS; a descriptive cell records the literal "NOT-EVALUABLE", never a NaN read as
    "below 2".
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T265 = ROOT / "data" / "research" / "t265"
PRICES = T265 / "prices"
TWINS = ROOT / "data" / "processed" / "tr_reconciled"
ZIPS = ROOT / "data" / "edgar" / "insider_zips"
OUT = ROOT / "data" / "research" / "b2"

ENV_PINS = {"PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1", "OMP_DYNAMIC": "FALSE"}

PANEL_START = pd.Timestamp("2016-01-04")
TWIN_END = pd.Timestamp("2026-05-22")          # last day of the TR twins (prereg §3.4)
DEATH_CUTOFF = pd.Timestamp("2026-06-23")      # A1.2: last traded bar earlier than this = a death
SPLICE_GAP = 63                                # A1.2: >= 63 market days without a trade
MIN_FILE_BARS = 60                             # T-265 `_load_prices` rule
ADV_LO, ADV_MID, ADV_HI = 1e6, 2e7, 2e8        # band [$1M, $200M); buckets split at $20M
SATELLITE = 0.25
NW_LAGS = 6
BOOT_ITERS = 1000
BOOT_SEED = 0
MIN_BOOT_MONTHS = 24
EXPECTED_PHANTOM_TAIL_FILES = 151              # A1.2 (census_zerovol.py, trailing run >= 5)
EXPECTED_SPLICE_FILES = 141                    # A1.2 (census_splice.py, run >= 63)
DEATH_D = {"base": -0.30, "stress": -1.00, "lastprice": 0.0}
# per-side cost by ADV bucket (fraction): the GATE is 70/150 bps RT (A1.3); the brief's 35/75 RT
COST_SIDE = {"gate": {"small": 0.0035, "micro": 0.0075},
             "brief": {"small": 0.00175, "micro": 0.00375}}
MDE80 = {"momentum_satellite": 0.43, "insider_satellite": 0.56, "insider_car": 0.057}  # A1.6


class Halt(RuntimeError):
    """A fail-closed stop ([NN-FAIL-CLOSED]): the harness exits 2 and writes no headline."""


class NotEvaluable(Halt):
    """Too few observations for a statistic. Halts on the gate path; descriptive cells catch it."""


NOT_EVALUABLE = "NOT-EVALUABLE"

# prereg §3.3 (census_prices.py / census_zerovol.py / census_splice.py), recomputed by
# load_universe with the census scripts' own definitions.
EXPECTED_PRICE_CENSUS = {
    "files": 4674, "files_lt_60_bars": 44, "files_start_le_2016_01_05": 2577,
    "files_last_ge_2026_06_26": 4172, "first_bar_min": "2016-01-04", "last_bar_max": "2026-06-30",
    "files_last_close_lt_2026_06_01": 495, "nonpositive_close_files": 0,
    "zero_volume_bars": 220696, "files_with_zero_volume": 1307,
    "phantom_tail_files_ge5": 151, "phantom_tail_files_ge21": 145, "phantom_tail_files_ge252": 44,
    "terminations_last_traded_lt_2026_06_01": 532,
    "notrade_files_ge5": 511, "notrade_files_ge10": 318, "notrade_files_ge21": 198,
    "splice_files_ge63": 141, "notrade_files_ge252": 85,
}


def enforce_census(observed: Dict[str, object], expected: Dict[str, object]) -> Dict[str, dict]:
    """§4.5: every declared count must equal its recomputation; any mismatch (or a missing
    recomputation) HALTS. Returns the check record."""
    rec = {k: {"expected": v, "observed": observed.get(k), "ok": observed.get(k) == v}
           for k, v in expected.items()}
    bad = {k: (r["expected"], r["observed"]) for k, r in rec.items() if not r["ok"]}
    if bad:
        raise Halt(f"census recomputation disagrees with the prereg (expected, observed): {bad}")
    return rec


def write_census_check(rec: Dict[str, dict], out_dir: Path, stem: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{stem}_census_check.json").write_text(json.dumps(r12(rec), indent=2, sort_keys=True))


def env_pin_violations(env: Optional[dict] = None) -> List[str]:
    env = os.environ if env is None else env
    return [f"{k}={env.get(k)!r} (need {v!r})" for k, v in ENV_PINS.items() if env.get(k) != v]


# ============================================================ calendar + twins
def load_twin(name: str, twins_dir: Path = TWINS) -> pd.Series:
    # ticker-exclusions: bypassed — three named TR twin ETFs (SPY, IWM, BIL); never a universe read
    path = twins_dir / f"{name}_1d.csv"
    if not path.is_file():
        raise Halt(f"twin {path} missing")
    df = pd.read_csv(path, usecols=["Date", "Close"])
    s = pd.Series(df["Close"].to_numpy(dtype=float),
                  index=pd.DatetimeIndex(pd.to_datetime(df["Date"])).normalize(), name=name)
    return s[~s.index.duplicated(keep="last")].sort_index()


def market_calendar(twins_dir: Path = TWINS, start: Optional[pd.Timestamp] = PANEL_START
                    ) -> pd.DatetimeIndex:
    """Trading days of the SPY TR twin (prereg §4.1)."""
    idx = load_twin("SPY", twins_dir).index
    return idx[idx >= start] if start is not None else idx


def twins_on(cal: pd.DatetimeIndex, twins_dir: Path = TWINS) -> pd.DataFrame:
    """SPY / IWM / BIL TR closes on the calendar; any gap HALTS."""
    tw = pd.DataFrame({n: load_twin(n, twins_dir).reindex(cal) for n in ("SPY", "IWM", "BIL")})
    bad = {c: int(tw[c].isna().sum()) for c in tw if tw[c].isna().any()}
    if bad:
        raise Halt(f"twin gaps on the calendar: {bad}")
    return tw


def month_ends(cal: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(cal, index=cal)
    return pd.DatetimeIndex(s.groupby(cal.to_period("M")).max().to_numpy())


# ============================================================ segments
@dataclass
class Segment:
    seg_id: str
    ticker: str
    k: int                   # segment number within the file (0 = first)
    n_segments: int
    close: pd.Series         # traded closes (volume > 0), date-indexed
    dvol: pd.Series          # traded dollar volume (close x volume)
    first: pd.Timestamp
    last: pd.Timestamp
    death: Optional[pd.Timestamp]


def file_census(df: pd.DataFrame, cal: pd.DatetimeIndex) -> Dict[str, object]:
    """Per-file census, computed EXACTLY as census_prices.py / census_zerovol.py /
    census_splice.py do (same column, same NaN handling, same calendar)."""
    c = df["close"].dropna()
    ci = pd.DatetimeIndex(pd.to_datetime(c.index)).normalize()
    v = df["volume"].fillna(0)
    pos = v[v > 0]
    trail0 = int((v.index > pos.index.max()).sum()) if len(pos) else len(v)
    out = {"trailing_zero_vol_bars": trail0, "max_notrade": -1, "n_close": int(len(c)),
           "first": ci[0] if len(ci) else None, "last": ci[-1] if len(ci) else None,
           "n_nonpos": int((c <= 0).sum()), "n_zero_vol": int((v <= 0).sum()),
           "last_traded": pos.index.max() if len(pos) else None}
    idx = pd.DatetimeIndex(pd.to_datetime(df.index)).normalize()
    traded = idx[df["volume"].fillna(0).to_numpy() > 0]
    if len(traded) >= 2:
        life = cal[(cal >= traded[0]) & (cal <= traded[-1])]
        p = life.searchsorted(traded)
        out["max_notrade"] = int((p[1:] - p[:-1] - 1).max())
    return out


def split_segments(ticker: str, df: pd.DataFrame, cal: pd.DatetimeIndex,
                   death_cutoff: pd.Timestamp = DEATH_CUTOFF) -> List[Segment]:
    """Traded bars only; split where the census_splice gap (market days without a trade between
    consecutive trades, on the calendar) is >= SPLICE_GAP. Every non-final segment dies at its
    last traded bar; the final one dies there only if that bar is earlier than `death_cutoff`."""
    df = df.copy()
    df.index = pd.DatetimeIndex(pd.to_datetime(df.index)).normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    tr = df[(df["volume"].fillna(0) > 0) & df["close"].notna() & (df["close"] > 0)]
    if len(tr) < 2:
        return []
    life = cal[(cal >= tr.index[0]) & (cal <= tr.index[-1])]
    p = life.searchsorted(tr.index)
    cuts = np.where((p[1:] - p[:-1] - 1) >= SPLICE_GAP)[0]
    bounds = [0] + [int(c) + 1 for c in cuts] + [len(tr)]
    segs = []
    n = len(bounds) - 1
    for k in range(n):
        part = tr.iloc[bounds[k]:bounds[k + 1]]
        last = part.index[-1]
        final = k == n - 1
        death = last if (not final or last < death_cutoff) else None
        segs.append(Segment(seg_id=f"{ticker}#{k}", ticker=ticker, k=k, n_segments=n,
                            close=part["close"].astype(float),
                            dvol=(part["close"] * part["volume"]).astype(float),
                            first=part.index[0], last=last, death=death))
    return segs


def load_universe(cal: pd.DatetimeIndex, prices_dir: Path = PRICES,
                  tickers: Optional[List[str]] = None) -> Tuple[List[Segment], dict]:
    """Every T-265 price file -> segments, with the A1.2 recount (HALT on mismatch)."""
    files = sorted(prices_dir.glob("*.parquet"))
    if not files:
        raise Halt(f"no price files under {prices_dir}")
    segs: List[Segment] = []
    n_tail5 = n_tail_any = n_splice = n_short = 0
    rows = []
    for f in files:
        df = pd.read_parquet(f, columns=["close", "volume"])
        fc = file_census(df, cal)
        rows.append(dict(fc, ticker=f.stem))
        n_tail5 += fc["trailing_zero_vol_bars"] >= 5
        n_tail_any += fc["trailing_zero_vol_bars"] >= 1
        n_splice += fc["max_notrade"] >= SPLICE_GAP
        if tickers is not None and f.stem not in tickers:
            continue
        if int(df["close"].notna().sum()) < MIN_FILE_BARS:
            n_short += 1
            continue
        segs.extend(split_segments(f.stem, df, cal))
    census = {"files": len(files), "files_lt_60_bars": n_short,
              "phantom_tail_files_ge5": int(n_tail5), "phantom_tail_files_ge1": int(n_tail_any),
              "splice_files_ge63": int(n_splice), "segments": len(segs),
              "segments_from_splices": int(sum(1 for s in segs if s.n_segments > 1)),
              "segment_deaths": int(sum(1 for s in segs if s.death is not None))}
    if tickers is None:
        if n_tail5 != EXPECTED_PHANTOM_TAIL_FILES or n_splice != EXPECTED_SPLICE_FILES:
            raise Halt(f"A1.2 recount differs from the census: phantom tails {n_tail5} "
                       f"(declared {EXPECTED_PHANTOM_TAIL_FILES}), splices {n_splice} "
                       f"(declared {EXPECTED_SPLICE_FILES})")
    fcen = pd.DataFrame(rows).set_index("ticker")
    return segs, census, fcen


def price_census_observed(fcen: pd.DataFrame) -> Dict[str, object]:
    """The §3.3 counts from the per-file census, with the census scripts' definitions."""
    first, last = pd.to_datetime(fcen["first"]), pd.to_datetime(fcen["last"])
    lt = pd.to_datetime(fcen["last_traded"])
    tz, mn = fcen["trailing_zero_vol_bars"], fcen["max_notrade"]
    return {"files": int(len(fcen)), "files_lt_60_bars": int((fcen["n_close"] < MIN_FILE_BARS).sum()),
            "files_start_le_2016_01_05": int((first <= "2016-01-05").sum()),
            "files_last_ge_2026_06_26": int((last >= "2026-06-26").sum()),
            "first_bar_min": first.min().strftime("%Y-%m-%d"),
            "last_bar_max": last.max().strftime("%Y-%m-%d"),
            "files_last_close_lt_2026_06_01": int((last < "2026-06-01").sum()),
            "nonpositive_close_files": int((fcen["n_nonpos"] > 0).sum()),
            "zero_volume_bars": int(fcen["n_zero_vol"].sum()),
            "files_with_zero_volume": int((fcen["n_zero_vol"] > 0).sum()),
            "phantom_tail_files_ge5": int((tz >= 5).sum()), "phantom_tail_files_ge21": int((tz >= 21).sum()),
            "phantom_tail_files_ge252": int((tz >= 252).sum()),
            "terminations_last_traded_lt_2026_06_01": int((lt < "2026-06-01").sum()),
            "notrade_files_ge5": int((mn >= 5).sum()), "notrade_files_ge10": int((mn >= 10).sum()),
            "notrade_files_ge21": int((mn >= 21).sum()), "splice_files_ge63": int((mn >= 63).sum()),
            "notrade_files_ge252": int((mn >= 252).sum())}


def price_matrices(segs: List[Segment], cal: pd.DatetimeIndex) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """(traded close on the calendar, 20-day median dollar ADV on the calendar). ADV counts a
    no-trade day inside the segment's life as 0 and is NaN outside it (prereg §4.1)."""
    cols, closes, advs = [], [], []
    for s in segs:
        c = s.close.reindex(cal)
        life = (cal >= s.first) & (cal <= s.last)
        dv = s.dvol.reindex(cal)
        fill = life & dv.isna().to_numpy()
        dv = dv.mask(pd.Series(fill, index=cal), 0.0)
        adv = dv.rolling(20, min_periods=20).median()
        cols.append(s.seg_id)
        closes.append(c.to_numpy())
        advs.append(adv.to_numpy())
    C = pd.DataFrame(np.column_stack(closes) if closes else np.empty((len(cal), 0)),
                     index=cal, columns=cols)
    A = pd.DataFrame(np.column_stack(advs) if advs else np.empty((len(cal), 0)),
                     index=cal, columns=cols)
    return C, A


def side_cost(adv: float, basis: str) -> float:
    """Per-side cost by ADV bucket; ADV missing or < $20M -> the micro rate (A1.3)."""
    tab = COST_SIDE[basis]
    return tab["small"] if (adv is not None and np.isfinite(adv) and adv >= ADV_MID) else tab["micro"]


# ============================================================ statistics
def boot(n: int, fn: Callable[[np.ndarray], float], iters: int = BOOT_ITERS,
         seed: int = BOOT_SEED) -> Dict[str, float]:
    """Project-standard moving-block bootstrap on the MONTH INDICES (auto block length)."""
    if n < MIN_BOOT_MONTHS:
        raise Halt(f"bootstrap over {n} months < {MIN_BOOT_MONTHS}")
    from core.metrics_engine import MetricsEngine
    idx = pd.Series(np.arange(n, dtype=float))
    out = MetricsEngine.bootstrap_distribution(
        idx, lambda s: fn(s.to_numpy().astype(int)), n_iterations=iters,
        block_length=None, seed=seed)
    return {"point": out["point_estimate"], "ci_low": out["ci_low"], "ci_high": out["ci_high"],
            "boot_std": out["std"], "p_above_zero": out["p_above_zero"],
            "block_length": out["block_length"], "n": n}


def dlogw(arm: np.ndarray, spy: np.ndarray, bench: Optional[np.ndarray] = None):
    """Δ log terminal wealth of (75% SPY + 25% arm) vs 100% SPY, or vs (75% SPY + 25% bench)."""
    a = SATELLITE * arm + (1.0 - SATELLITE) * spy
    b = spy if bench is None else SATELLITE * bench + (1.0 - SATELLITE) * spy

    def f(i):
        return float(np.sum(np.log1p(a[i])) - np.sum(np.log1p(b[i])))
    return f


def sharpe_fn(r: np.ndarray):
    from core.metrics_engine import MetricsEngine as ME
    return lambda i: float(ME.sharpe_ratio(pd.Series(r[i]), 0.0, 12))


def sortino_fn(r: np.ndarray):
    from core.metrics_engine import MetricsEngine as ME
    return lambda i: float(ME.sortino_ratio(pd.Series(r[i]), 0.0, 12))


def max_dd(r: np.ndarray) -> float:
    from core.metrics_engine import MetricsEngine as ME
    return float(ME.max_drawdown(pd.Series(np.cumprod(1.0 + np.asarray(r, dtype=float)))))


def cagr(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    return float(np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0)


def nw_mean_t(x: np.ndarray, lags: int = NW_LAGS) -> Tuple[float, float, int]:
    """Mean and Newey-West (Bartlett, statsmodels HAC) t of a series' mean."""
    import statsmodels.api as sm
    x = np.asarray(x, dtype=float)
    if not np.all(np.isfinite(x)):
        raise Halt("non-finite value in a Newey-West input")
    if len(x) < 2 * lags:
        raise NotEvaluable(f"Newey-West t over {len(x)} observations < {2 * lags}")
    res = sm.OLS(x, np.ones((len(x), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(res.params[0]), float(res.tvalues[0]), len(x)


def nw_alpha(y: np.ndarray, x: np.ndarray, lags: int = NW_LAGS) -> Dict[str, float]:
    """Intercept (x12, annualized) and slope of y on [1, x] with HAC t (A1.6 diagnostics)."""
    import statsmodels.api as sm
    if len(y) < 2 * lags or not (np.all(np.isfinite(y)) and np.all(np.isfinite(x))):
        raise NotEvaluable(f"alpha regression over {len(y)} observations (or non-finite input)")
    res = sm.OLS(np.asarray(y, float), sm.add_constant(np.asarray(x, float), has_constant="add")
                 ).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return {"alpha_ann": float(res.params[0] * 12.0), "alpha_t_hac": float(res.tvalues[0]),
            "beta": float(res.params[1]), "beta_t_hac": float(res.tvalues[1]), "n": int(len(y))}


def arm_block(r: np.ndarray, spy: np.ndarray, iwm: np.ndarray, mde: float) -> dict:
    """Standalone + satellite statistics for one monthly arm on one paired bootstrap draw."""
    n = len(r)
    sat = boot(n, dlogw(r, spy))
    return {"n_months": n, "cagr": cagr(r), "ann_vol": float(np.std(r, ddof=1) * np.sqrt(12)),
            "max_dd": max_dd(r), "sharpe": boot(n, sharpe_fn(r)), "sortino": boot(n, sortino_fn(r)),
            "dlogw_vs_spy": sat, "dlogw_vs_iwm_sleeve": boot(n, dlogw(r, spy, iwm)),
            "realized_mde80": 2.80 * sat["boot_std"],
            "label": satellite_label(sat, mde)}


def satellite_label(sat: Dict[str, float], mde: float) -> str:
    """A1.6 binding labelling rule."""
    if sat["ci_low"] > 0:
        return "ci_low > 0"
    if sat["point"] < mde:
        return "null; not demonstrable at this length (point below the pre-data MDE80)"
    return "null (point at/above the pre-data MDE80; the CI is wider than assumed)"


# ============================================================ identity
def r12(o):
    if isinstance(o, (float, np.floating)):
        o = float(o)
        return float(f"{o:.12g}") if np.isfinite(o) else str(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, dict):
        return {str(k): r12(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [r12(v) for v in o]
    if isinstance(o, pd.Timestamp):
        return o.strftime("%Y-%m-%d")
    return o


def canonical_md5(results: dict) -> str:
    body = {k: v for k, v in results.items() if k not in ("run_meta",)}
    return hashlib.md5(json.dumps(r12(body), sort_keys=True).encode()).hexdigest()


def write_results(results: dict, out_dir: Path, stem: str) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    md5 = canonical_md5(results)
    results = dict(results)
    results["run_meta"] = dict(results.get("run_meta", {}), canonical_md5=md5)
    (out_dir / f"{stem}.json").write_text(json.dumps(r12(results), indent=2, sort_keys=True))
    return md5
