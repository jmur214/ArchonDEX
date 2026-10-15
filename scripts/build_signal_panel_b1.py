"""scripts/build_signal_panel_b1.py — B-1 month-end signal panel + census.

Implements step 3 of the FROZEN B-1 pre-registration
(`docs/Sources/prereg_b1_raw_signal_decile_2026-09-30.md` §11.1). A standalone harness:
it never touches `BacktestController`.

    PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    OMP_DYNAMIC=FALSE python -m scripts.build_signal_panel_b1 \
        --start 2000-01 --end 2025-12 --out data/research/b1/

What it writes (both gitignored under `data/`):
  census_<md5>.json        always — the census, including any HALT reasons
  signal_panel_<md5>.parquet  ONLY if the census passes (a halted panel is never consumable)

Exit codes: 0 ok · 2 census HALT (`[NN-FAIL-CLOSED]`) · 3 env pins wrong (refused, never
re-exec'd) · 4 disk below the floor · 5 code provenance outside this worktree.

Design laws (each tested in tests/test_build_signal_panel_b1.py):
  * POINT-IN-TIME is enforced in ONE place (`pit_slice`). Several edges read `iloc[-1]`
    and assume their input already ends at the as-of date; every signal sees only data
    on or before the month-end.
  * Missing has three spellings in the foundry (None, NaN, constant 0.0). A signal-month
    is UNUSABLE unless it has >= MIN_NAMES finite values with cross-sectional std >= 1e-12.
  * Engine A edges emit SELECTIONS (1/0, ±1, vol-targeted weights), not raw scores; they
    are expected to be SPARSE and are tested under the frozen §4.2 rule by the harness.
"""
from __future__ import annotations

import os
import sys

# ---- env pins: checked BEFORE numpy is imported; REFUSE, never re-exec (§11.1 step 1) ----
ENV_PINS = {"PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1", "OMP_DYNAMIC": "FALSE"}


def env_pin_violations(env=None) -> list:
    env = os.environ if env is None else env
    return [f"{k}={env.get(k)!r} (need {v!r})" for k, v in ENV_PINS.items() if env.get(k) != v]


if __name__ == "__main__":
    _bad = env_pin_violations()
    if _bad:
        print("[B1-PANEL] REFUSING: determinism env pins wrong — " + "; ".join(_bad) +
              ". Export them BEFORE python starts (prereg §11.1 step 1). Never re-exec'd.",
              file=sys.stderr)
        sys.exit(3)

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402
import time  # noqa: E402
from datetime import date  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Callable, Dict, Iterable, List, Optional, Tuple  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DISK_FLOOR_GB = 5.0            # rescore_rr1.MIN_FREE_GB; checked before EVERY write
MIN_NAMES = 10                 # fewer finite values than this = an unusable signal-month
UNUSABLE_HALT_SHARE = 0.10     # prereg §3.4: HALT a signal unusable in > 10% of its months
# prereg §5.2 as amended 2026-10-14 (second amendment): the first month-end at which every
# SimFin edge forms its inputs for >= 30 names. 2020-04 came from the excluded
# earnings_proximity_5d's calendar and never described SimFin coverage.
SHORT_WINDOW_START = "2021-07"

# ---- the FROZEN inventory (prereg §4, §5.2). Order is the panel's column order. ----
MAIN_FEATURES = ["mom_12_1", "mom_6_1", "reversal_1m", "dist_52w_high", "realized_vol_60d",
                 "beta_252d", "skew_60d", "high_minus_low_60d", "drawdown_60d",
                 "ma_cross_50_200", "moving_avg_distance_50d", "vol_regime_5_60"]
MAIN_EDGES = {"overnight_intraday_v1": ("overnight_intraday_edge", "OvernightIntradayEdge"),
              "volume_anomaly_v1": ("volume_anomaly_edge", "VolumeAnomalyEdge")}
SENSITIVITY_EDGES = {"momentum_12_1_v1": ("momentum_12_1_v1", "Momentum12_1Edge"),
                     "momentum_6_1_v1": ("momentum_6_1_v1", "Momentum6_1Edge"),
                     "short_term_reversal_v1": ("short_term_reversal_v1", "ShortTermReversalEdge"),
                     "low_vol_factor_v1": ("low_vol_factor_edge", "LowVolFactorEdge"),
                     "betting_against_beta_v1": ("betting_against_beta_edge", "BettingAgainstBetaEdge")}
SHORT_FEATURES: List[str] = []
SHORT_EDGES = {"value_book_to_market_v1": ("value_book_to_market_edge", "ValueBookToMarketEdge"),
               "value_earnings_yield_v1": ("value_earnings_yield_edge", "ValueEarningsYieldEdge"),
               "quality_gross_profitability_v1": ("quality_gross_profitability_edge",
                                                  "QualityGrossProfitabilityEdge"),
               "quality_roic_v1": ("quality_roic_edge", "QualityROICEdge"),
               "accruals_inv_sloan_v1": ("accruals_inv_sloan_edge", "AccrualsInvSloanEdge"),
               "accruals_inv_asset_growth_v1": ("accruals_inv_asset_growth_edge",
                                                "AccrualsInvAssetGrowthEdge")}
# POST-FREEZE, PRE-DATA inventory amendment (director ruling 2026-10-14, made before any
# return/IC/wealth existed). Excluded signals are NOT computed — the pair_zscore_60d
# disposition: structurally ineligible for a month-end construction, not weak signals.
EXCLUDED_BY_RULING = {
    "pair_zscore_60d": "prereg §3.3 — defined for 10 hand-picked tickers only",
    "herding_v1": "ruling 2026-10-14 — daily EVENT edge, all zeros at 8 of 12 smoke month-ends",
    "earnings_proximity_5d": "ruling 2026-10-14 — all zeros at month-ends between earnings seasons",
}
# PRE-RULED (2026-10-14): if the full-window census trips the 10% unusable bar, the SAME
# exclusion applies automatically and is recorded — no decision made after seeing anything.
PRE_RULED_AUTO_EXCLUDE = {"volume_anomaly_v1"}
EXPECTED_FAMILY_COUNTS = {"main": 14, "sensitivity": 5, "short_window": 6}

FAMILY = {**{s: "main" for s in MAIN_FEATURES + list(MAIN_EDGES)},
          **{s: "sensitivity" for s in SENSITIVITY_EDGES},
          **{s: "short_window" for s in SHORT_FEATURES + list(SHORT_EDGES)}}
SIGNALS = list(FAMILY)

# §2.2 orientation check: duplicate edges vs their foundry reference, and the sign the
# edge's NATIVE score must show against that reference's RAW value.
ORIENTATION_REFS = {"momentum_12_1_v1": ("mom_12_1", +1), "momentum_6_1_v1": ("mom_6_1", +1),
                    "short_term_reversal_v1": ("reversal_1m", -1),
                    "low_vol_factor_v1": ("realized_vol_60d", -1),
                    "betting_against_beta_v1": ("beta_252d", -1)}


# ============================================================ guards
def disk_free_gb(path: Path) -> float:
    return shutil.disk_usage(str(path)).free / 1e9


def assert_disk_floor(path: Path, floor: float = DISK_FLOOR_GB) -> None:
    free = disk_free_gb(path)
    if free < floor:
        print(f"[B1-PANEL] REFUSING TO WRITE: {free:.2f} GB free < {floor} GB floor.",
              file=sys.stderr)
        sys.exit(4)


def provenance(modules: Iterable) -> Dict[str, str]:
    """Resolved file of each module that does real work. All must sit under ROOT — a run
    that imports another tree's code reports that tree's behaviour under this one's name."""
    out = {"self": str(Path(__file__).resolve())}
    for m in modules:
        out[m.__name__] = str(Path(m.__file__).resolve())
    return out


def provenance_violations(prov: Dict[str, str], root: Path = ROOT) -> List[str]:
    r = str(root.resolve())
    return [f"{k} -> {v}" for k, v in prov.items() if not v.startswith(r + os.sep)]


# ============================================================ data
def month_ends(trading_days: pd.DatetimeIndex, start: str, end: str) -> List[pd.Timestamp]:
    """The LAST trading day of each calendar month in [start, end] (YYYY-MM)."""
    d = pd.DatetimeIndex(trading_days).sort_values()
    d = d[(d >= pd.Timestamp(start + "-01")) & (d <= pd.Timestamp(end + "-01") + pd.offsets.MonthEnd(0))]
    if len(d) == 0:
        return []
    s = pd.Series(d, index=d)
    return list(s.groupby([d.year, d.month]).max())


def load_ohlcv(ticker: str, root: Path) -> Optional[pd.DataFrame]:
    p = root / f"{ticker}_1d.csv"
    if not p.is_file():
        return None
    df = pd.read_csv(p, parse_dates=["Date"], index_col="Date")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df[[c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]]


def pit_slice(prices: Dict[str, pd.DataFrame], as_of: pd.Timestamp) -> Dict[str, pd.DataFrame]:
    """THE point-in-time boundary — the ONLY way any signal sees prices. Rows strictly
    after `as_of` never reach a feature or an edge."""
    out = {}
    for t, df in prices.items():
        sub = df.loc[:as_of]
        if len(sub):
            out[t] = sub
    return out


def forward_return(df: Optional[pd.DataFrame], me: pd.Timestamp,
                   next_me: pd.Timestamp) -> Tuple[float, str]:
    """Close(next month-end) / Close(month-end) - 1. If the series ends inside the next
    month (delisted / acquired / file ends), exit at its LAST available close in that
    month — dropping the name would bias returns up. Returns (value, how)."""
    if df is None:
        return float("nan"), "no_file"
    c = df["Close"]
    c0 = c.loc[:me]
    if not len(c0) or c0.index[-1] != me:
        return float("nan"), "no_price_at_month_end"
    after = c.loc[(c.index > me) & (c.index <= next_me)]
    if not len(after):
        return float("nan"), "no_price_after"
    how = "full" if after.index[-1] == next_me else "last_price_proxy"
    return float(after.iloc[-1] / c0.iloc[-1] - 1.0), how


# ============================================================ signals
def foundry_values(feature_ids: List[str], tickers: List[str], me: pd.Timestamp,
                   registry=None) -> Dict[str, Dict[str, float]]:
    if registry is None:
        from core.feature_foundry.feature import get_feature_registry
        registry = get_feature_registry()
    d = me.date()
    out: Dict[str, Dict[str, float]] = {}
    for fid in feature_ids:
        f = registry.get(fid)
        if f is None:
            raise RuntimeError(f"[NN-FAIL-CLOSED] foundry feature {fid!r} not registered")
        col = {}
        for t in tickers:
            v = f(t, d)
            col[t] = float(v) if v is not None else float("nan")
        out[fid] = col
    return out


def make_edges(spec: Dict[str, Tuple[str, str]]) -> Dict[str, object]:
    import importlib
    edges = {}
    for eid, (mod, cls) in spec.items():
        m = importlib.import_module(f"engines.engine_a_alpha.edges.{mod}")
        e = getattr(m, cls)()
        if getattr(e, "EDGE_ID", eid) != eid:
            raise RuntimeError(f"{mod}.{cls}.EDGE_ID != {eid}")
        edges[eid] = e
    return edges


def edge_values(edges: Dict[str, object], pit_map: Dict[str, pd.DataFrame],
                me: pd.Timestamp) -> Dict[str, Dict[str, float]]:
    out = {}
    for eid, e in edges.items():
        raw = e.compute_signals(pit_map, me) or {}
        out[eid] = {t: (float(raw[t]) if raw.get(t) is not None else float("nan"))
                    for t in pit_map}
    return out


# ============================================================ census
def month_usable(vals: np.ndarray, min_names: int = MIN_NAMES) -> bool:
    """None, NaN and a constant (incl. the foundry's 0.0 fallback) are all 'missing'."""
    v = vals[np.isfinite(vals)]
    if len(v) < min_names:
        return False
    sd = float(np.std(v))
    return not (sd < 1e-12 or not np.isfinite(sd))       # [NN-FP-GUARDS]


def modal_share(vals: np.ndarray) -> float:
    v = vals[np.isfinite(vals)]
    if not len(v):
        return 1.0
    _, counts = np.unique(np.round(v, 12), return_counts=True)
    return float(counts.max() / len(v))


def build_census(panel: pd.DataFrame, coverage: List[dict], signals: List[str],
                 family: Dict[str, str], short_start: str = SHORT_WINDOW_START,
                 orientation: Optional[Dict[str, dict]] = None,
                 pre_ruled: Iterable[str] = PRE_RULED_AUTO_EXCLUDE,
                 expected_counts: Dict[str, int] = EXPECTED_FAMILY_COUNTS
                 ) -> Tuple[dict, List[str]]:
    halts: List[str] = []
    auto_excluded: Dict[str, str] = {}
    pre_ruled = set(pre_ruled)
    cen = {"coverage": coverage, "signals": {}, "excluded_by_ruling": EXCLUDED_BY_RULING}
    cov = pd.DataFrame(coverage)
    if len(cov):
        cen["coverage_share_months_below_80pct"] = float((cov["coverage_pct"] < 80.0).mean())
    for s in signals:
        months = sorted(panel.index.get_level_values("month_end").unique())
        if family.get(s) == "short_window":
            months = [m for m in months if m >= pd.Timestamp(short_start + "-01")]
        if not months:
            cen["signals"][s] = {"family": family.get(s), "months": 0, "note": "outside window"}
            continue
        usable, shares = [], []
        for m in months:
            vals = panel.xs(m, level="month_end")[s].to_numpy(dtype=float)
            usable.append(month_usable(vals))
            shares.append(modal_share(vals))
        unusable_share = 1.0 - float(np.mean(usable))
        measured = "CROSS-SECTIONAL" if np.mean(usable) >= 0.5 else "NOT-CROSS-SECTIONAL"
        sparse = bool(np.median(shares) > 0.5)
        # the months by name, so a HALT says WHERE (a contiguous run at a window start is a
        # warm-up, scattered months are missingness) without a second diagnostic pass
        cen["signals"][s] = {"family": family.get(s), "months": len(months),
                             "unusable_share": round(unusable_share, 4),
                             "unusable_months": [str(pd.Timestamp(m).date())
                                                 for m, ok in zip(months, usable) if not ok],
                             "measured": measured, "sparse": sparse,
                             "median_modal_share": round(float(np.median(shares)), 4)}
        if s in pre_ruled and unusable_share > UNUSABLE_HALT_SHARE:
            # The pre-ruling keys on the unusable SHARE, whichever check would fire first:
            # a herding-like signal (> 50% unusable) also fails the classification check,
            # and that is exactly the case the ruling was written for.
            auto_excluded[s] = (f"unusable in {unusable_share:.1%} of its months "
                                f"(measured {measured}) — EXCLUDED under the 2026-10-14 "
                                f"pre-ruling, not halted")
        elif measured != "CROSS-SECTIONAL":
            halts.append(f"{s}: measured {measured} but the frozen §4 inventory declares it "
                         f"cross-sectional")
        elif unusable_share > UNUSABLE_HALT_SHARE:
            halts.append(f"{s}: unusable in {unusable_share:.1%} of its months "
                         f"(> {UNUSABLE_HALT_SHARE:.0%}, prereg §3.4)")
    for eid, o in (orientation or {}).items():
        cen["signals"].setdefault(eid, {})["orientation"] = o
        if o.get("ok") is False:
            halts.append(f"{eid}: native orientation vs {o['reference']} is "
                         f"{o['spearman']:+.3f}, expected sign {o['expected_sign']:+d} "
                         f"(prereg §2.2 — never flipped)")
    # an orientation that could not be tested is not a mismatch (no HALT), but it must
    # never pass silently: a check that ran on nothing is listed by name
    cen["orientation_untestable"] = sorted(e for e, o in (orientation or {}).items()
                                           if o.get("ok") is None)
    cen["auto_excluded_pre_ruled"] = auto_excluded
    fam: Dict[str, int] = {}
    for s in signals:
        if s not in auto_excluded:
            fam[family[s]] = fam.get(family[s], 0) + 1
    expected = dict(expected_counts)
    for s in auto_excluded:
        expected[family[s]] -= 1
    cen["family_counts"] = fam
    if fam != expected:
        halts.append(f"family counts {fam} != the amended inventory {expected} "
                     f"(2026-10-14: main 14, sensitivity 5, short-window 6, less any "
                     f"pre-ruled auto-exclusion)")
    cen["halt_reasons"] = halts
    return cen, halts


def orientation_check(panel: pd.DataFrame, refs: Dict[str, Tuple[str, int]]) -> Dict[str, dict]:
    """Pooled Spearman of an edge's native score vs its foundry reference, over every
    (month, name) where both are finite. Mechanical, before any return is computed."""
    out = {}
    for eid, (ref, sign) in refs.items():
        if eid not in panel or ref not in panel:
            continue
        both = panel[[eid, ref]].dropna()
        # Correlate over ALL rows, zeros included. The edges emit SELECTIONS (1/0, ±1):
        # restricting to the selected rows leaves a constant column, and the check could
        # then never fire on real data — a control that cannot fail (caught by its test).
        if len(both) < 30 or both[eid].nunique() < 2:
            out[eid] = {"reference": ref, "expected_sign": sign, "spearman": float("nan"),
                        "ok": None, "note": "edge abstained everywhere — orientation UNTESTABLE"}
            continue
        rho = float(both[eid].rank().corr(both[ref].rank()))
        out[eid] = {"reference": ref, "expected_sign": sign, "spearman": round(rho, 4),
                    "ok": bool(np.sign(rho) == sign)}
    return out


def input_manifest(price_root: Path, membership_path: Optional[Path]) -> dict:
    files = sorted(price_root.glob("*_1d.csv"))
    h = hashlib.md5()
    for f in files:
        st = f.stat()
        h.update(f"{f.name}|{st.st_size}|{int(st.st_mtime)}\n".encode())
    return {"price_root_real": str(price_root.resolve()), "n_price_files": len(files),
            "price_manifest_md5": h.hexdigest(),
            "membership_real": str(membership_path.resolve()) if membership_path else None}


def canonical_md5(panel: pd.DataFrame) -> str:
    """Identity of CONTENT, not of parquet bytes (writer metadata is not the measurement).
    Streaming — the column list plus pandas' row hashes of the values rounded to 10
    decimals — so a 150k-row panel never becomes a Python list on an 8 GB host."""
    p = panel.sort_index().round(10)
    h = hashlib.md5(json.dumps(list(p.columns)).encode())
    h.update(pd.util.hash_pandas_object(p, index=True).to_numpy().tobytes())
    return h.hexdigest()


# ============================================================ main
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", required=True, help="YYYY-MM (first month-end in the panel)")
    ap.add_argument("--end", required=True, help="YYYY-MM (last month-end in the panel)")
    ap.add_argument("--out", required=True, help="output directory (under data/, gitignored)")
    a = ap.parse_args(argv)

    if Path.cwd().resolve() != ROOT:
        # the foundry's price source reads `data/processed` RELATIVE to the cwd: run from
        # anywhere else and every feature silently returns None (prereg §11.1 step 0)
        print(f"[B1-PANEL] REFUSING: cwd {Path.cwd()} is not the worktree root {ROOT}",
              file=sys.stderr)
        return 5
    import core.feature_foundry as cff
    import core.feature_foundry.features as fpkg
    import engines.data_manager.membership as mem
    import engines.engine_a_alpha.edges as edges_pkg
    import importlib
    import pkgutil
    prov = provenance([cff, mem, edges_pkg])
    print("[B1-PANEL] provenance: " + json.dumps(prov))
    bad = provenance_violations(prov)
    if bad:
        print(f"[B1-PANEL] REFUSING: code from outside this worktree: {bad}", file=sys.stderr)
        return 5
    for m in pkgutil.iter_modules(fpkg.__path__):
        importlib.import_module(f"{fpkg.__name__}.{m.name}")

    out = Path(a.out)
    price_root = ROOT / "data" / "processed"
    t0 = time.time()
    spy = load_ohlcv("SPY", price_root)
    if spy is None:
        print("[B1-PANEL] HALT: SPY_1d.csv missing — no trading calendar", file=sys.stderr)
        return 2
    mes = month_ends(spy.index, a.start, a.end)
    all_mes = month_ends(spy.index, a.start, (pd.Timestamp(a.end + "-01") + pd.offsets.MonthBegin(1)).strftime("%Y-%m"))
    have = {f.name[:-7] for f in price_root.glob("*_1d.csv")}

    edges = {**make_edges(MAIN_EDGES), **make_edges(SENSITIVITY_EDGES), **make_edges(SHORT_EDGES)}
    short_edges = set(SHORT_EDGES)
    cache: Dict[str, Optional[pd.DataFrame]] = {}
    frames, coverage, fwd_how = [], [], {}
    for i, me in enumerate(mes):
        members = sorted(mem.members_on(me))
        tickers = [t for t in members if t in have]
        coverage.append({"month_end": str(me.date()), "n_pit_members": len(members),
                         "n_with_price": len(tickers),
                         "coverage_pct": round(100.0 * len(tickers) / max(1, len(members)), 2)})
        for t in tickers:
            if t not in cache:
                cache[t] = load_ohlcv(t, price_root)
        pit = pit_slice({t: cache[t] for t in tickers if cache[t] is not None}, me)
        in_short = me >= pd.Timestamp(SHORT_WINDOW_START + "-01")
        vals = foundry_values(MAIN_FEATURES + (SHORT_FEATURES if in_short else []), list(pit), me)
        run_edges = {k: v for k, v in edges.items() if in_short or k not in short_edges}
        vals.update(edge_values(run_edges, pit, me))
        nxt = all_mes[all_mes.index(me) + 1] if all_mes.index(me) + 1 < len(all_mes) else None
        names = list(pit)
        fwd = []
        for t in names:
            r, how = forward_return(cache[t], me, nxt) if nxt is not None else (float("nan"), "no_next_month")
            fwd_how[how] = fwd_how.get(how, 0) + 1
            fwd.append(r)
        # columnar per month: a list of per-row dicts would cost ~0.5 GB on the full panel
        mdf = pd.DataFrame({s: pd.Series(vals.get(s, {}), dtype=float).reindex(names)
                            for s in SIGNALS}, index=names)
        mdf["__fwd_ret_1m"] = fwd
        mdf.index = pd.MultiIndex.from_product([[me], names], names=["month_end", "ticker"])
        frames.append(mdf)
        if (i + 1) % 12 == 0 or i == len(mes) - 1:
            print(f"[B1-PANEL] {me.date()}  {i + 1}/{len(mes)} months  "
                  f"{time.time() - t0:.0f}s  cache={len(cache)} tickers", flush=True)

    panel = pd.concat(frames).sort_index()
    del frames
    orient = orientation_check(panel, ORIENTATION_REFS)
    cen, halts = build_census(panel[SIGNALS], coverage, SIGNALS, FAMILY, orientation=orient)
    cen.update({"window": [a.start, a.end], "n_month_ends": len(mes), "n_rows": len(panel),
                "forward_return_how": fwd_how, "provenance": prov,
                "input_manifest": input_manifest(price_root, getattr(mem, "MEMBERSHIP_PARQUET", None)),
                "env_pins": {k: os.environ.get(k) for k in ENV_PINS},
                "wall_seconds": round(time.time() - t0, 1),
                "substrate_note": ("closes in data/processed are DIVIDEND-ADJUSTED (SPY "
                                   "1993-01-29 = 24.18 vs a ~43.9 nominal close) — returns are "
                                   "total-return on both legs, not price-only as the prereg says"),
                "engine_a_note": ("Engine A edges emit SELECTIONS (1/0, ±1, vol-targeted "
                                  "weights), not raw scores; tested under the frozen §4.2 "
                                  "sparse rule")})
    dropped = list(cen["auto_excluded_pre_ruled"])
    if dropped:
        panel = panel.drop(columns=dropped)
        print(f"[B1-PANEL] pre-ruled auto-exclusion applied (recorded): {dropped}")
    digest = canonical_md5(panel)
    cen["panel_canonical_md5"] = digest
    out.mkdir(parents=True, exist_ok=True)
    assert_disk_floor(out)
    (out / f"census_{digest[:12]}.json").write_text(json.dumps(cen, indent=2, default=str))
    print(f"[B1-PANEL] census -> {out / f'census_{digest[:12]}.json'}")
    if halts:
        print("[B1-PANEL] HALT ([NN-FAIL-CLOSED]) — no panel written:\n  " + "\n  ".join(halts),
              file=sys.stderr)
        return 2
    assert_disk_floor(out)
    panel.to_parquet(out / f"signal_panel_{digest[:12]}.parquet")
    print(f"[B1-PANEL] panel -> {out / f'signal_panel_{digest[:12]}.parquet'}  "
          f"({len(panel)} rows, {time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    # load_local_env: offline by design — B-1 runs on the CACHED substrate with no .env (it ran in
    # Agent A's worktree without one) and its own census is fail-closed; it must not pick up keys.
    sys.exit(main())
