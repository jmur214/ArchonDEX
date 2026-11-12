"""scripts/lazy_prices/b6_harness_sp.py
====================================
T-383 (B-6) Phase 2 — the S&P-arm standalone harness (never `BacktestController`).

Frozen design: `docs/Sources/prereg_b6_lazy_prices_2026-11-11.md` (§5–§8, §11, AMENDMENT 1 incl.
the harness conventions A1.10). Order of operations is the fail-closed contract:

  1. Build the per-rebalance panel and its CENSUS from text signals + price-bar DATES only.
  2. HALT (exit 2, census written, no return touched) if any rebalance breaks §7.7 / §11:
     ranked < 150, a tercile < 40, or ranked < 80% of PIT members with a CIK.
  3. Only then compute returns: equal-weight legs (long top tercile = non-changers / high Δtone,
     short bottom tercile, universe), buy-and-hold within the quarter, exits at the last close
     with proceeds in BIL TR (D = 0; D = −30% diagnostic), |Δw|·RT/2 costs, the 25%/75% SPY TR
     satellite rebalanced quarterly, paired month-index block bootstrap, Newey-West short leg.
  4. Results JSON with sorted keys; its md5 is the determinism receipt (run twice).

No `.env`, no network, no engine import; `core` only for `MetricsEngine` (bootstrap).

Usage:
  python -m scripts.lazy_prices.b6_harness_sp --census-only            # the gate census
  python -m scripts.lazy_prices.b6_harness_sp --spec gate_similarity   # one arm (halts if census fails)
  python -m scripts.lazy_prices.b6_harness_sp --all --out data/b6_local/harness_sp/run1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "data" / "b6_local"
SIGNALS = LOCAL / "signals_sp.parquet"
UNIVERSE = LOCAL / "sp_universe_months.parquet"
T265 = ROOT / "data" / "research" / "t265"
PROCESSED = ROOT / "data" / "processed"
TWINS = PROCESSED / "tr_reconciled"

SATELLITE = 0.25
FILL_FROM = pd.Timestamp("2020-06-30")
FRESH_MONTHS = 6
MIN_RANKED, MIN_TERCILE, MIN_SHARE = 150, 40, 0.80
NW_LAGS = 3
BOOT_ITERS, BOOT_SEED = 1000, 0


class CensusHalt(RuntimeError):
    """A frozen fail-closed condition fired before any return was computed."""


@dataclass(frozen=True)
class Spec:
    """One arm: which signal ranks, on which window, at which cost and exit convention."""
    name: str
    col_10k: str
    col_10q: str
    why_10k: str
    why_10q: str
    start: str = "2016-03-31"
    end: str = "2025-12-31"
    cost_bps: float = 10.0
    exit_d: float = 0.0
    forms: tuple[str, ...] = ("10-K", "10-Q")
    price_mode: str = "d"          # "d": T-265 + fill from 2020-06-30; "c": data/processed only
    gate: bool = False


SIM = dict(col_10k="yoy_combo_cos", col_10q="yoy_mda_cos", why_10k="yoy_combo_why", why_10q="yoy_mda_why")
TONE = dict(col_10k="yoy_combo_dtone", col_10q="yoy_mda_dtone", why_10k="yoy_combo_why",
            why_10q="yoy_mda_why")

C = dict(start="2020-06-30", price_mode="c")   # AMENDMENT 2: the gate window and source

SPECS: dict[str, Spec] = {s.name: s for s in [
    # the gate (prereg AMENDMENT 2): window (c), data/processed TR closes, rebalances 2020-06-30 ->
    Spec("gate_similarity", **SIM, **C, gate=True),
    Spec("gate_tone", **TONE, **C, gate=True),
    # §7.5 pre-named diagnostics, on the gate's window (A2.2); none can meet H1
    Spec("cost20_similarity", **SIM, **C, cost_bps=20.0),
    Spec("exit30_similarity", **SIM, **C, exit_d=-0.30),
    Spec("jaccard", col_10k="yoy_combo_jac", col_10q="yoy_mda_jac", why_10k="yoy_combo_why",
         why_10q="yoy_mda_why", **C),
    Spec("tfidf", col_10k="yoy_combo_tfidf", col_10q="yoy_mda_tfidf", why_10k="yoy_combo_why",
         why_10q="yoy_mda_why", **C),
    Spec("risk_only", col_10k="yoy_risk_cos", col_10q="yoy_risk_cos", why_10k="yoy_risk_why",
         why_10q="yoy_risk_why", **C),
    Spec("mda_only", col_10k="yoy_mda_cos", col_10q="yoy_mda_cos", why_10k="yoy_mda_why",
         why_10q="yoy_mda_why", **C),
    Spec("q10_combo", col_10k="yoy_combo_cos", col_10q="yoy_combo_cos", why_10k="yoy_combo_why",
         why_10q="yoy_combo_why", **C),
    Spec("q10_adjacent", col_10k="yoy_combo_cos", col_10q="qoq_mda_cos", why_10k="yoy_combo_why",
         why_10q="qoq_mda_why", **C),
    Spec("tenk_only", **SIM, **C, forms=("10-K",)),
    Spec("tenq_only", **SIM, **C, forms=("10-Q",)),
    # window (d) — NOT EVALUABLE (AMENDMENT 2, A2.1): kept ONLY to reproduce the halted census;
    # excluded from --all; re-runs as its own pre-registered trial once the price hole closes
    Spec("d_similarity", **SIM, gate=True),
    Spec("d_tone", **TONE, gate=True),
]}
NOT_EVALUABLE = {"d_similarity", "d_tone"}


# --------------------------------------------------------------------------- #
# calendar
# --------------------------------------------------------------------------- #
def rebalance_dates(cal: pd.DatetimeIndex, start: str, end: str) -> list[pd.Timestamp]:
    qe = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="QE")
    return [cal[cal <= d].max() for d in qe]


def month_marks(cal: pd.DatetimeIndex, t0: pd.Timestamp, t1: pd.Timestamp) -> list[pd.Timestamp]:
    """Last calendar bar of each month-end strictly after t0 up to and including t1."""
    out = []
    for me in pd.date_range(t0 + pd.offsets.MonthEnd(1), t1, freq="ME"):
        d = cal[cal <= me].max()
        if d > t0:
            out.append(d)
    if not out or out[-1] != t1:
        out.append(t1)
    return sorted(set(out))


# --------------------------------------------------------------------------- #
# panel + census (no returns)
# --------------------------------------------------------------------------- #
def signals_at(sig: pd.DataFrame, t: pd.Timestamp, spec: Spec, ciks: set[int]) -> pd.DataFrame:
    """Each member's latest filing usable at t (decision_floor_date <= t, accepted within 6 months)
    whose ranking signal is defined; one row per CIK with its form and value."""
    s = sig[(sig["floor"] <= t) & (sig["acc"] > t - pd.DateOffset(months=FRESH_MONTHS))
            & sig["cik"].isin(ciks)]
    latest = s.sort_values(["floor", "acceptance_dt"]).groupby("cik").tail(1)
    k = latest[latest.form == "10-K"]
    q = latest[latest.form == "10-Q"]
    k = k.assign(value=k[spec.col_10k], ok=k[spec.why_10k] == "ok")
    q = q.assign(value=q[spec.col_10q], ok=q[spec.why_10q] == "ok")
    out = pd.concat([k, q])
    out = out[out.ok & np.isfinite(out.value.astype(float)) & out.form.isin(spec.forms)]
    return out[["cik", "form", "value", "accession"]]


def rank_terciles(df: pd.DataFrame) -> pd.DataFrame:
    """Percentile rank within form (average ties), pooled terciles (A1.10-8)."""
    df = df.copy()
    df["pct"] = df.groupby("form")["value"].rank(pct=True, method="average")
    df["leg"] = np.where(df.pct > 2 / 3, "long", np.where(df.pct <= 1 / 3, "short", "mid"))
    return df


@dataclass
class Prices:
    """Close series by source. `t265` keyed by T-265 ticker, `proc` by membership ticker."""
    t265_of_cik: dict[int, str]
    t265: dict[str, pd.Series]
    proc: dict[str, pd.Series]
    spy: pd.Series
    bil: pd.Series
    source_log: dict = field(default_factory=dict)

    def series_for(self, cik: int, ticker: str, t: pd.Timestamp, mode: str) -> tuple[str, pd.Series] | None:
        key = ticker.replace(".", "-")
        if mode == "c":
            s = self.proc.get(key)
            return ("processed", s) if s is not None and t in s.index else None
        tk = self.t265_of_cik.get(cik)
        if tk is not None:
            s = self.t265.get(tk)
            if s is not None and t in s.index:
                return ("t265", s)
        if t >= FILL_FROM:
            s = self.proc.get(key)
            if s is not None and t in s.index:
                return ("processed_fill", s)
        return None


def build_panel(spec: Spec, sig: pd.DataFrame, uni: pd.DataFrame, px: Prices,
                cal: pd.DatetimeIndex) -> tuple[list[dict], pd.DataFrame]:
    """Per rebalance: the ranked names with leg + source; and the census rows."""
    rebs = rebalance_dates(cal, spec.start, spec.end)
    panel, census = [], []
    for t in rebs:
        m = uni[uni.month == t.to_period("M").to_timestamp()].drop_duplicates("cik")
        members = dict(zip(m.cik.astype(int), m.ticker))
        s = signals_at(sig, t, spec, set(members))
        rows = []
        for r in s.itertuples():
            got = px.series_for(int(r.cik), members[int(r.cik)], t, spec.price_mode)
            if got is None:
                continue
            rows.append({"cik": int(r.cik), "ticker": members[int(r.cik)], "form": r.form,
                         "value": float(r.value), "source": got[0]})
        ranked = rank_terciles(pd.DataFrame(rows)) if rows else pd.DataFrame(
            columns=["cik", "ticker", "form", "value", "source", "pct", "leg"])
        legs = ranked.leg.value_counts().to_dict() if len(ranked) else {}
        census.append({"rebalance": t.date().isoformat(), "members_with_cik": len(members),
                       "usable_signal": int(len(s)), "ranked": int(len(ranked)),
                       "share": round(len(ranked) / max(1, len(members)), 4),
                       "long": int(legs.get("long", 0)), "short": int(legs.get("short", 0)),
                       "src_t265": int((ranked.source == "t265").sum()) if len(ranked) else 0,
                       "src_fill": int((ranked.source == "processed_fill").sum()) if len(ranked) else 0,
                       "src_processed": int((ranked.source == "processed").sum()) if len(ranked) else 0,
                       "n_10k": int((ranked.form == "10-K").sum()) if len(ranked) else 0,
                       "n_10q": int((ranked.form == "10-Q").sum()) if len(ranked) else 0})
        panel.append({"t": t, "ranked": ranked})
    return panel, pd.DataFrame(census)


def check_census(census: pd.DataFrame) -> list[str]:
    """The frozen halt conditions (§7.7, §11). Empty list = pass."""
    bad = []
    for r in census.itertuples():
        if r.ranked < MIN_RANKED:
            bad.append(f"{r.rebalance}: ranked {r.ranked} < {MIN_RANKED}")
        if min(r.long, r.short) < MIN_TERCILE:
            bad.append(f"{r.rebalance}: a tercile < {MIN_TERCILE} (long {r.long}, short {r.short})")
        if r.share < MIN_SHARE:
            bad.append(f"{r.rebalance}: ranked share {r.share:.3f} < {MIN_SHARE}")
    return bad


# --------------------------------------------------------------------------- #
# returns (only after the census passes)
# --------------------------------------------------------------------------- #
def growth(series: pd.Series, a: pd.Timestamp, b: pd.Timestamp) -> float:
    """Close-to-close gross return from a to b (last bar on or before each date)."""
    va = series[series.index <= a]
    vb = series[series.index <= b]
    if va.empty or vb.empty:
        return float("nan")
    return float(vb.iloc[-1] / va.iloc[-1])


def name_path(s: pd.Series, t0: pd.Timestamp, marks: list[pd.Timestamp], bil: pd.Series,
              exit_d: float) -> tuple[list[float], pd.Timestamp | None]:
    """Gross value of 1 invested at t0 at each mark. If the bars END before the quarter's last mark,
    the name exits at its last close: value × (1 + exit_d), then BIL TR to each later mark."""
    last = s.index.max()
    exited = last < marks[-1]
    out = []
    for m in marks:
        if exited and m > last:
            v = growth(s, t0, last) * (1.0 + exit_d) * growth(bil, last, m)
        else:
            v = growth(s, t0, m)
        out.append(v)
    return out, (last if exited else None)


def leg_returns(names: list[tuple[int, pd.Series]], t0: pd.Timestamp, marks: list[pd.Timestamp],
                bil: pd.Series, exit_d: float) -> tuple[np.ndarray, dict[int, float], list[dict]]:
    """Equal-weight at t0, buy-and-hold: monthly returns, end weights (for turnover), exits."""
    paths, exits = {}, []
    for cik, s in names:
        p, ex = name_path(s, t0, marks, bil, exit_d)
        if any(not np.isfinite(v) for v in p):
            raise CensusHalt(f"NaN return for CIK {cik} in quarter from {t0.date()} with no exit")
        paths[cik] = p
        if ex is not None:
            exits.append({"cik": cik, "exit_date": ex.date().isoformat(), "from": t0.date().isoformat()})
    V = np.mean(np.array(list(paths.values())), axis=0)
    prev = np.concatenate([[1.0], V[:-1]])
    r = V / prev - 1.0
    end = {c: p[-1] for c, p in paths.items()}
    tot = sum(end.values())
    w_end = {c: v / tot for c, v in end.items()} if tot > 1e-12 else {}
    return r, w_end, exits


def turnover(prev_w: dict[int, float], new_names: list[int]) -> float:
    tgt = {c: 1.0 / len(new_names) for c in new_names} if new_names else {}
    keys = set(prev_w) | set(tgt)
    return float(sum(abs(tgt.get(k, 0.0) - prev_w.get(k, 0.0)) for k in keys))


def run_returns(spec: Spec, panel: list[dict], px: Prices, cal: pd.DatetimeIndex,
                hold_end: pd.Timestamp) -> dict:
    """Monthly series for the legs, SPY, BIL and the satellite blend over the window."""
    rebs = [p["t"] for p in panel]
    ends = rebs[1:] + [hold_end]
    months, out = [], {"long": [], "short": [], "universe": [], "spy": [], "blend": []}
    prev_w = {"long": {}, "short": {}, "universe": {}}
    exits, turn = [], {"long": [], "short": [], "universe": []}
    for p, t1 in zip(panel, ends):
        t0, ranked = p["t"], p["ranked"]
        marks = month_marks(cal, t0, t1)
        series = {}
        for r in ranked.itertuples():
            s = px.t265[px.t265_of_cik[r.cik]] if r.source == "t265" else px.proc[r.ticker.replace(".", "-")]
            series[r.cik] = s[s.index >= t0]
        legs = {"long": ranked[ranked.leg == "long"].cik.tolist(),
                "short": ranked[ranked.leg == "short"].cik.tolist(),
                "universe": ranked.cik.tolist()}
        res = {}
        for name, ciks in legs.items():
            r, w_end, ex = leg_returns([(c, series[c]) for c in ciks], t0, marks, px.bil, spec.exit_d)
            to = turnover(prev_w[name], ciks)
            r = r.copy()
            r[0] -= to * spec.cost_bps / 1e4 / 2.0
            turn[name].append(to)
            prev_w[name] = w_end
            res[name] = r
            if name == "universe":
                exits.extend(ex)
        spy = np.array([growth(px.spy, a, b) - 1.0 for a, b in zip([t0] + marks[:-1], marks)])
        if not np.all(np.isfinite(spy)):
            raise CensusHalt(f"SPY TR missing in quarter from {t0.date()}")
        # satellite: 25/75 at t0, drifting within the quarter (A1.10-9)
        g_long = np.cumprod(1.0 + res["long"])
        g_spy = np.cumprod(1.0 + spy)
        Vb = SATELLITE * g_long + (1.0 - SATELLITE) * g_spy
        blend = Vb / np.concatenate([[1.0], Vb[:-1]]) - 1.0
        for k, v in (("long", res["long"]), ("short", res["short"]), ("universe", res["universe"]),
                     ("spy", spy), ("blend", blend)):
            out[k].extend(v.tolist())
        months.extend([m.date().isoformat() for m in marks])
    return {"months": months, **{k: np.array(v) for k, v in out.items()}, "exits": exits,
            "turnover": {k: float(np.mean(v)) for k, v in turn.items()}}


# --------------------------------------------------------------------------- #
# statistics
# --------------------------------------------------------------------------- #
def newey_west_t(x: np.ndarray, lags: int = NW_LAGS) -> float:
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < lags + 3:
        return float("nan")
    e = x - x.mean()
    lrv = float(np.dot(e, e) / n)
    for k in range(1, lags + 1):
        w = 1.0 - k / (lags + 1.0)
        lrv += 2.0 * w * float(np.dot(e[k:], e[:-k]) / n)
    if lrv is None or lrv < 1e-18 or not np.isfinite(lrv):
        return float("nan")
    return float(x.mean() / math.sqrt(lrv / n))


def boot(n: int, fn, confidence: float) -> dict:
    from core.metrics_engine import MetricsEngine
    idx = pd.Series(np.arange(n, dtype=float))
    out = MetricsEngine.bootstrap_distribution(idx, lambda s: fn(s.to_numpy().astype(int)),
                                               n_iterations=BOOT_ITERS, seed=BOOT_SEED,
                                               confidence=confidence)
    return {"point": out["point_estimate"], "ci_low": out["ci_low"], "ci_high": out["ci_high"],
            "sd": out["std"], "block_length": out["block_length"]}


def sharpe(r: np.ndarray) -> float:
    sd = float(np.std(r, ddof=1)) if len(r) > 1 else float("nan")
    if sd is None or sd < 1e-12 or not np.isfinite(sd):
        return 0.0
    return float(np.mean(r) / sd * math.sqrt(12.0))


def sortino(r: np.ndarray) -> float:
    dn = np.minimum(r, 0.0)
    dd = float(np.sqrt(np.mean(dn ** 2)))
    if dd < 1e-12 or not np.isfinite(dd):
        return 0.0
    return float(np.mean(r) / dd * math.sqrt(12.0))


def summarize(res: dict) -> dict:
    blend, spy = res["blend"], res["spy"]
    n = len(blend)
    if n < 24:
        raise CensusHalt(f"bootstrap needs >= 24 months, got {n}")

    def dlogw(i):
        return float(np.sum(np.log1p(blend[i])) - np.sum(np.log1p(spy[i])))

    g975 = boot(n, dlogw, 0.975)
    g95 = boot(n, dlogw, 0.95)
    short_leg = res["universe"] - res["short"]
    ls = res["long"] - res["short"]
    sh = boot(n, lambda i: sharpe(res["long"][i]), 0.95)
    so = boot(n, lambda i: sortino(res["long"][i]), 0.95)
    years = pd.Series(np.log1p(blend) - np.log1p(spy), index=pd.to_datetime(res["months"]))
    return {
        "n_months": n,
        "dlogw_point": g95["point"],
        "dlogw_ci_low_1p25": g975["ci_low"], "dlogw_ci_low_2p5": g95["ci_low"],
        "dlogw_ci_high_97p5": g95["ci_high"], "dlogw_boot_sd": g95["sd"],
        "realized_mde80": 2.80 * g95["sd"], "block_length": g95["block_length"],
        "short_leg_mean_ann": float(np.mean(short_leg) * 12), "short_leg_t_hac": newey_west_t(short_leg),
        "long_short_mean_ann": float(np.mean(ls) * 12), "long_short_t_hac": newey_west_t(ls),
        "long_minus_spy_ann": float((np.mean(res["long"]) - np.mean(spy)) * 12),
        "long_sharpe": sh["point"], "long_sharpe_ci_low": sh["ci_low"],
        "long_sortino": so["point"], "long_sortino_ci_low": so["ci_low"],
        "spy_sharpe": sharpe(spy),
        "per_year_dlogw": {str(int(k)): float(v) for k, v in years.groupby(years.index.year).sum().items()},
        "turnover_per_rebalance": res["turnover"], "n_exits": len(res["exits"]),
    }


# --------------------------------------------------------------------------- #
# real-data loaders + CLI
# --------------------------------------------------------------------------- #
def _close(path: Path, csv: bool) -> pd.Series:
    if csv:
        d = pd.read_csv(path, usecols=["Date", "Close"], parse_dates=["Date"])
        s = d.set_index("Date")["Close"].astype(float)
    else:
        s = pd.read_parquet(path, columns=["close"])["close"].astype(float)
        s.index = pd.to_datetime(s.index)
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[np.isfinite(s) & (s > 0)]


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, Prices, pd.DatetimeIndex]:
    sig = pd.read_parquet(SIGNALS)
    sig["floor"] = pd.to_datetime(sig.decision_floor_date)
    sig["acc"] = pd.to_datetime(sig.acceptance_dt.str[:10])
    uni = pd.read_parquet(UNIVERSE).dropna(subset=["cik"])
    uni["cik"] = uni.cik.astype(int)
    ct = pd.read_parquet(T265 / "cik_ticker_final.parquet")
    ct["cik"] = ct.cik.astype(int)
    shared = set(ct.groupby("ticker").cik.nunique().loc[lambda s: s > 1].index)
    need = set(uni.cik)
    t265_of_cik = {c: t for c, t in zip(ct.cik, ct.ticker) if c in need and t not in shared
                   and (T265 / "prices" / f"{t}.parquet").is_file()}
    t265 = {t: _close(T265 / "prices" / f"{t}.parquet", csv=False) for t in set(t265_of_cik.values())}
    proc = {}
    for tk in set(uni.ticker):
        k = tk.replace(".", "-")
        p = PROCESSED / f"{k}_1d.csv"  # ticker-exclusions: bypassed — named PIT members only; returns are scale-free ratios, so the level exclusion does not bind
        if p.is_file():
            proc[k] = _close(p, csv=True)  # ticker-exclusions: bypassed — named PIT members only; returns are scale-free ratios, so the level exclusion does not bind
    spy = _close(TWINS / "SPY_1d.csv", csv=True)
    bil = _close(TWINS / "BIL_1d.csv", csv=True)
    return sig, uni, Prices(t265_of_cik, t265, proc, spy, bil), pd.DatetimeIndex(spy.index)


def smoke(args: argparse.Namespace) -> int:
    """First 12 months of the gate window: census + returns + sanity numbers (never quoted)."""
    from dataclasses import replace
    sig, uni, px, cal = load_inputs()
    args.out.mkdir(parents=True, exist_ok=True)
    out = {}
    for n in ("gate_similarity", "gate_tone"):
        base = SPECS[n]
        rebs = rebalance_dates(cal, base.start, base.end)
        spec = replace(base, end=rebs[3].date().isoformat())
        panel, census = build_panel(spec, sig, uni, px, cal)
        bad = check_census(census)
        if bad:
            print(f"[b6-smoke] {n}: census HALT {bad}")
            return 2
        res = run_returns(spec, panel, px, cal, rebs[4])
        stats = {k: {"mean": float(np.mean(res[k])), "sd": float(np.std(res[k], ddof=1)),
                     "min": float(np.min(res[k])), "max": float(np.max(res[k])),
                     "n_nan": int(np.sum(~np.isfinite(res[k])))}
                 for k in ("long", "short", "universe", "spy", "blend")}
        out[n] = {"months": res["months"], "census": census.to_dict("records"), "stats": stats,
                  "n_exits": len(res["exits"]), "exits": res["exits"], "turnover": res["turnover"]}
        print(f"[b6-smoke] {n}: {len(res['months'])} months; ranked "
              f"{census.ranked.tolist()}; exits {len(res['exits'])}; NaN "
              f"{sum(v['n_nan'] for v in stats.values())}; turnover {res['turnover']}")
        for k, v in stats.items():
            print(f"    {k:9} mean {v['mean']:+.4f} sd {v['sd']:.4f} min {v['min']:+.4f} "
                  f"max {v['max']:+.4f}")
    (args.out / "smoke.json").write_text(_json(out))
    return 0


def _json(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B-6 S&P-arm standalone harness (fail-closed).")
    ap.add_argument("--spec", default="gate_similarity", choices=sorted(SPECS))
    ap.add_argument("--all", action="store_true", help="every pre-named spec (gate first)")
    ap.add_argument("--census-only", action="store_true", help="panel + census, no returns")
    ap.add_argument("--smoke", action="store_true",
                    help="the gate's FIRST FOUR rebalances (12 months): sanity statistics only, "
                         "no bootstrap, no headline — not quoted")
    ap.add_argument("--out", type=Path, default=LOCAL / "harness_sp" / "run")
    args = ap.parse_args(argv)
    names = ["gate_similarity", "gate_tone"] + [n for n in SPECS if not SPECS[n].gate
                                                and n not in NOT_EVALUABLE] if args.all else [args.spec]
    if args.smoke:
        return smoke(args)
    sig, uni, px, cal = load_inputs()
    args.out.mkdir(parents=True, exist_ok=True)
    hold_end = cal[cal <= pd.Timestamp("2026-03-31")].max()
    results = {}
    for n in names:
        spec = SPECS[n]
        panel, census = build_panel(spec, sig, uni, px, cal)
        census.to_csv(args.out / f"census_{n}.csv", index=False)
        bad = check_census(census)
        print(f"[b6-harness] {n}: {len(census)} rebalances; census "
              f"{'PASS' if not bad else 'HALT (' + str(len(bad)) + ' violations)'}", flush=True)
        if bad:
            (args.out / f"HALT_{n}.txt").write_text("\n".join(bad) + "\n")
            for b in bad[:20]:
                print("   ", b)
            if spec.gate:
                print(f"[b6-harness] GATE census failed — no return computed (exit 2). "
                      f"Census: {args.out / f'census_{n}.csv'}", flush=True)
                return 2
            results[n] = {"halted": bad}
            continue
        if args.census_only:
            continue
        res = run_returns(spec, panel, px, cal, hold_end)
        results[n] = {"spec": spec.__dict__ | {"forms": list(spec.forms)}, **summarize(res)}
    if args.census_only:
        return 0
    body = _json(results)
    (args.out / "results.json").write_text(body)
    md5 = hashlib.md5(body.encode()).hexdigest()
    (args.out / "results.md5").write_text(md5 + "\n")
    print(f"[b6-harness] results md5 {md5} -> {args.out / 'results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
