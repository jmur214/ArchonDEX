"""scripts/lazy_prices/b6_harness_t265.py
=======================================
T-383 (B-6) — the T-265 small-cap arm's standalone harness (never `BacktestController`).

Frozen design: `docs/Sources/prereg_b6_lazy_prices_2026-11-11.md` §5–§8, A1.7, A1.10, AMENDMENTS 5–7
(H_OOS, its accounting, the gap fill and the S&P harness's grid) and AMENDMENT 8 (the T-265 freeze).
Order of operations is the fail-closed contract:

  1. Verify the freeze manifest (§7.7 bullet 1): the LM dictionary md5, every T-265 signal file and
     its row count, the S&P-panel signals the overlap firms read. Any mismatch HALTS (exit 2).
  2. Prices — B-2's frozen machinery BY REFERENCE (`scripts/smallcap_t265_b2_common.py`, byte-
     identical to main): a security is a price-file SEGMENT (traded bars only, split at >= 63-day
     no-trade runs); the A1.2 recount and the §3.3 price census are recomputed and HALT on any
     mismatch; 20-day median dollar ADV (a no-trade day inside the life counts 0); SPY / IWM / BIL TR
     twins. Deaths at a segment's last traded bar: BASE -30% (gate), STRESS -100%, LAST-PRICE 0;
     proceeds in BIL TR.
  3. Per rebalance (the S&P harness's grid, imported): the identity rule (A8), a traded bar ON t,
     ADV at t in [$1M, $200M), a usable signal -> ranked within form, pooled terciles. CENSUS; HALT
     (exit 2, no return) if a rebalance has < 300 ranked or < 40 in a tercile (§7.7) — checked AFTER
     the band, never lowered.
  4. Returns: equal weight at t, buy-and-hold to the next rebalance, month-end marks; costs
     |Δw| x per-side rate by the name's ADV bucket at t (70/150 bps RT; dead proceeds sell free);
     the 25%/75% SPY TR satellite on the true path; paired month-index block bootstrap; NW 3 lags.
  5. H_OOS (A5/A6): the S&P `q10_adjacent` construction, GROSS, changers - universe, t_HAC <= -2.0.
  6. Results JSON with sorted keys; its md5 is the determinism receipt (run twice).

No `.env`, no network, no engine import; `core` only for `MetricsEngine` (bootstrap).

Usage:
  python -m scripts.lazy_prices.b6_harness_t265 --write-manifest            # at the freeze, once
  python -m scripts.lazy_prices.b6_harness_t265 --census-only --out data/b6_local/harness_t265/census
  python -m scripts.lazy_prices.b6_harness_t265 --smoke --out data/b6_local/harness_t265/smoke
  python -m scripts.lazy_prices.b6_harness_t265 --all --out data/b6_local/harness_t265/run1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import smallcap_t265_b2_common as cm
from scripts.lazy_prices import b6_harness_sp as H

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "data" / "b6_local"
T265_SIG_DIR = LOCAL / "t265_signals"
SP_V2_SIGNALS = LOCAL / "signals_sp_v2.parquet"
MANIFEST = LOCAL / "t265_freeze_manifest.json"
AMBIG_USERS = LOCAL / "cik_map" / "t265_ambiguous_ticker_users.parquet"
T265_MAP = cm.T265 / "cik_ticker_final.parquet"
LM_MD5 = "12dade0123e1d096c1d1192c755f08a3"

START, END = "2016-03-31", "2025-12-31"
HOLD_CAP = pd.Timestamp("2026-03-31")
MIN_RANKED, MIN_TERCILE = 300, 40
SURVIVOR_ASOF = pd.Timestamp("2026-05-22")      # B-2 A1.2: no death on or before the twins' end
HOLDER_PAD = pd.Timedelta(days=90)              # AMENDMENT 4's padding
HOOS_T = -2.0
MINBTL_SR_10Y = 0.68                            # prereg §9: required SR at N_eff 36.92, T = 10.0 yr
FLAT75_SIDE = 0.00375                           # the brief's flat 75 bps RT


class Halt(cm.Halt):
    """A frozen fail-closed condition fired; exit 2, no headline."""


@dataclass(frozen=True)
class T265Spec:
    """One arm: which signal ranks, under which cost basis, death penalty and universe filter."""
    name: str
    col_10k: str
    col_10q: str
    why_10k: str
    why_10q: str
    forms: tuple[str, ...] = ("10-K", "10-Q")
    cost: str = "gate"            # "gate" 70/150 RT by ADV bucket · "flat75" · "none" (gross)
    death: str = "base"           # B-2: base -30% · stress -100% · lastprice 0
    survivor_only: bool = False
    gate: bool = False
    hoos: bool = False


SIM, TONE = H.SIM, H.TONE
ADJ = dict(col_10k="yoy_combo_cos", col_10q="qoq_mda_cos", why_10k="yoy_combo_why", why_10q="qoq_mda_why")

SPECS: dict[str, T265Spec] = {s.name: s for s in [
    # the gate family (§7.1, §7.4): {similarity, Δtone}, Bonferroni 1.25th-percentile ci_low
    T265Spec("gate_similarity", **SIM, gate=True),
    T265Spec("gate_tone", **TONE, gate=True),
    # H_OOS (A5.2/A6.1): the S&P q10_adjacent construction, GROSS, the gate's inclusion + death rule
    T265Spec("hoos_adjacent", **ADJ, cost="none", hoos=True),
    # §7.5 pre-named diagnostics (cannot meet H1)
    T265Spec("flat75_similarity", **SIM, cost="flat75"),
    T265Spec("stress_similarity", **SIM, death="stress"),
    T265Spec("lastprice_similarity", **SIM, death="lastprice"),
    T265Spec("survivor_similarity", **SIM, survivor_only=True),
    T265Spec("jaccard", col_10k="yoy_combo_jac", col_10q="yoy_mda_jac", why_10k="yoy_combo_why",
             why_10q="yoy_mda_why"),
    T265Spec("tfidf", col_10k="yoy_combo_tfidf", col_10q="yoy_mda_tfidf", why_10k="yoy_combo_why",
             why_10q="yoy_mda_why"),
    T265Spec("risk_only", col_10k="yoy_risk_cos", col_10q="yoy_risk_cos", why_10k="yoy_risk_why",
             why_10q="yoy_risk_why"),
    T265Spec("mda_only", col_10k="yoy_mda_cos", col_10q="yoy_mda_cos", why_10k="yoy_mda_why",
             why_10q="yoy_mda_why"),
    T265Spec("q10_combo", col_10k="yoy_combo_cos", col_10q="yoy_combo_cos", why_10k="yoy_combo_why",
             why_10q="yoy_combo_why"),
    T265Spec("q10_adjacent", **ADJ),
    T265Spec("tenk_only", **SIM, forms=("10-K",)),
    T265Spec("tenq_only", **SIM, forms=("10-Q",)),
]}


# --------------------------------------------------------------------------- #
# the freeze manifest (§7.7 bullet 1)
# --------------------------------------------------------------------------- #
def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def manifest_now() -> dict:
    """Every T-265 text input as it stands: file -> rows + md5; the S&P-panel signals; LM md5."""
    files = {}
    for p in sorted(T265_SIG_DIR.glob("*.parquet")):
        files[p.name] = {"rows": int(pd.read_parquet(p, columns=["cik"]).shape[0]), "md5": _md5(p)}
    sp = {"rows": int(pd.read_parquet(SP_V2_SIGNALS, columns=["cik"]).shape[0]), "md5": _md5(SP_V2_SIGNALS)}
    from scripts.lazy_prices import b6_signals as S
    return {"lm_md5": S.lm_md5(), "t265_signal_files": files, "signals_sp_v2": sp,
            "n_files": len(files)}


def verify_manifest(path: Path = MANIFEST) -> dict:
    """HALT unless every recorded file exists with its recorded rows and md5, no file was added,
    and the LM dictionary is the frozen one (§7.7 bullet 1)."""
    if not path.is_file():
        raise Halt(f"freeze manifest {path} missing — the T-265 arm is not frozen")
    want = json.loads(path.read_text())
    from scripts.lazy_prices import b6_signals as S
    S.load_lm()                                       # halts on a file/manifest md5 mismatch
    if want["lm_md5"] != LM_MD5 or S.lm_md5() != LM_MD5:
        raise Halt(f"LM md5 {S.lm_md5()} / manifest {want['lm_md5']} != frozen {LM_MD5}")
    have = {p.name for p in T265_SIG_DIR.glob("*.parquet")}
    rec = set(want["t265_signal_files"])
    if have != rec:
        raise Halt(f"T-265 signal files differ from the freeze: added {sorted(have - rec)[:5]}, "
                   f"missing {sorted(rec - have)[:5]}")
    for name, r in want["t265_signal_files"].items():
        p = T265_SIG_DIR / name
        if _md5(p) != r["md5"]:
            raise Halt(f"{name}: md5 differs from the freeze")
    if _md5(SP_V2_SIGNALS) != want["signals_sp_v2"]["md5"]:
        raise Halt("signals_sp_v2.parquet md5 differs from the freeze")
    return want


# --------------------------------------------------------------------------- #
# text inputs
# --------------------------------------------------------------------------- #
def load_signals(universe: set[int]) -> tuple[pd.DataFrame, dict]:
    """The T-265 ranking panel: every streamed CIK's rows (incl. the A7 fill) + the S&P-panel rows
    of the overlap CIKs the stream did not take; keyed (cik, accession)."""
    parts = [pd.read_parquet(p) for p in sorted(T265_SIG_DIR.glob("signals_*.parquet"))]
    done = pd.concat([pd.read_parquet(p) for p in sorted(T265_SIG_DIR.glob("done_*.parquet"))],
                     ignore_index=True)
    streamed = set(done.cik.astype(int))
    st = pd.concat(parts, ignore_index=True)
    sp = pd.read_parquet(SP_V2_SIGNALS)
    overlap = universe - streamed
    sp = sp[sp.cik.astype(int).isin(overlap)]
    sig = pd.concat([st, sp], ignore_index=True)
    sig["cik"] = sig.cik.astype(int)
    sig = sig[sig.cik.isin(universe)].drop_duplicates(["cik", "accession"], keep="last")
    sig["floor"] = pd.to_datetime(sig.decision_floor_date)
    sig["acc"] = pd.to_datetime(sig.acceptance_dt.str[:10])
    info = {"streamed_ciks": len(streamed & universe), "overlap_from_sp_panel": len(overlap),
            "signal_rows": int(len(sig))}
    return sig.reset_index(drop=True), info


# --------------------------------------------------------------------------- #
# prices (B-2 by reference) + identity (A8)
# --------------------------------------------------------------------------- #
@dataclass
class Panel:
    cal: pd.DatetimeIndex              # B-2 calendar: SPY TR twin days from 2016-01-04
    C: np.ndarray                      # traded close (NaN on a no-trade day / outside the life)
    FF: np.ndarray                     # last traded close carried forward INSIDE the life only
    A: np.ndarray                      # 20-day median dollar ADV
    seg_ids: list[str]
    col: dict[str, int]                # seg_id -> column
    death_pos: np.ndarray              # calendar index of the death bar; -1 = no death
    survivor: np.ndarray               # bool: no death on or before SURVIVOR_ASOF
    seg_by_ticker: dict[str, list]     # ticker -> [(first, last, seg_id)] sorted
    cik2t: dict[int, str]
    ambiguous: set[str]                # shared (> 1 CIK) or reused (> 1 segment) tickers
    holders: dict[str, list]           # ticker -> [(cik, first, last)]
    spy: pd.Series
    iwm: pd.Series
    bil: pd.Series
    census: dict

    def pos(self, t: pd.Timestamp) -> int:
        i = int(self.cal.searchsorted(t))
        if i >= len(self.cal) or self.cal[i] != t:
            raise Halt(f"{t.date()} is not a calendar day of the B-2 calendar")
        return i

    def holders_at(self, ticker: str, t: pd.Timestamp) -> set[int]:
        return {c for c, a, b in self.holders.get(ticker, []) if a - HOLDER_PAD <= t <= b + HOLDER_PAD}

    def resolve(self, cik: int, t: pd.Timestamp) -> tuple[str | None, str]:
        """(seg_id, cause). The security a CIK holds at t: its one priced T-265 ticker's segment
        alive at t; an ambiguous ticker (shared or reused) only when the date-aware holder set at
        t is exactly {cik} (AMENDMENT 4's rule, applied by A8)."""
        tk = self.cik2t.get(cik)
        if tk is None or tk not in self.seg_by_ticker:
            return None, "no_price_file"
        if tk in self.ambiguous and self.holders_at(tk, t) != {cik}:
            return None, "identity_unresolved"
        for first, last, sid in self.seg_by_ticker[tk]:
            if first <= t <= last:
                return sid, "ok"
        return None, "no_live_segment"


def ambiguous_users(tickers: set[str]) -> pd.DataFrame:
    """Form 3/4/5 symbol users for the ambiguous tickers (cached; rebuilt when the set changes)."""
    side = AMBIG_USERS.with_suffix(".tickers.json")
    want = sorted(tickers)
    if AMBIG_USERS.is_file() and side.is_file() and json.loads(side.read_text()) == want:
        return pd.read_parquet(AMBIG_USERS)
    from scripts.lazy_prices.b6_cik_map import symbol_users
    out = symbol_users(set(want))
    AMBIG_USERS.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(AMBIG_USERS, index=False)
    side.write_text(json.dumps(want))
    return out


def load_panel() -> Panel:
    cal = cm.market_calendar()
    segs, ucen, fcen = cm.load_universe(cal)                    # A1.2 recount HALTS on mismatch
    rec = cm.enforce_census(cm.price_census_observed(fcen), cm.EXPECTED_PRICE_CENSUS)
    C, A = cm.price_matrices(segs, cal)
    Cv, Av = C.to_numpy(), A.to_numpy()
    ids = list(C.columns)
    col = {s: j for j, s in enumerate(ids)}
    FF = np.array(pd.DataFrame(Cv).ffill().to_numpy(), dtype=float, copy=True)   # writable
    last_pos = np.array([cal.searchsorted(s.last) for s in segs])
    rows = np.arange(len(cal))[:, None]
    FF[rows > last_pos[None, :]] = np.nan
    death_pos = np.array([cal.searchsorted(s.death) if s.death is not None else -1 for s in segs])
    survivor = np.array([(s.death is None) or (s.death > SURVIVOR_ASOF) for s in segs])
    seg_by_ticker: dict[str, list] = {}
    for s in segs:
        seg_by_ticker.setdefault(s.ticker, []).append((s.first, s.last, s.seg_id))
    for v in seg_by_ticker.values():
        v.sort()
    ct = pd.read_parquet(T265_MAP)
    ct["cik"] = ct.cik.astype(int)
    ct = ct[ct.ticker.isin(set(seg_by_ticker))]
    if ct.cik.duplicated().any():
        raise Halt("a T-265 CIK maps to more than one priced ticker — the identity rule assumes one")
    cik2t = dict(zip(ct.cik, ct.ticker))
    n = ct.groupby("ticker").cik.nunique()
    shared = set(n[n > 1].index)
    reused = {t for t, v in seg_by_ticker.items() if len(v) > 1}
    ambiguous = shared | reused
    hu = ambiguous_users(ambiguous)
    holders: dict[str, list] = {}
    for r in hu.itertuples():
        holders.setdefault(r.ticker, []).append((int(r.cik), pd.Timestamp(r.first), pd.Timestamp(r.last)))
    spy, iwm, bil = (cm.load_twin(x) for x in ("SPY", "IWM", "BIL"))
    census = {"price_census": rec, "universe": ucen, "priced_ciks": len(cik2t),
              "shared_tickers": len(shared), "shared_ciks": int(ct.ticker.isin(shared).sum()),
              "reused_tickers": len(reused), "ambiguous_tickers": len(ambiguous),
              "ambiguous_tickers_with_holder_record": int(len(set(hu.ticker)))}
    return Panel(cal, Cv, FF, Av, ids, col, death_pos, survivor, seg_by_ticker, cik2t, ambiguous,
                 holders, spy, iwm, bil, census)


# --------------------------------------------------------------------------- #
# panel + census (no returns)
# --------------------------------------------------------------------------- #
def eligible_at(spec: T265Spec, sig: pd.DataFrame, P: Panel, t: pd.Timestamp
                ) -> tuple[pd.DataFrame, dict]:
    """Names usable at t: signal (the S&P harness's `signals_at`), identity, a traded bar ON t,
    ADV at t in [$1M, $200M) (and, for the survivor diagnostic, a surviving segment)."""
    s = H.signals_at(sig, t, spec, set(P.cik2t))
    i = P.pos(t)
    cause = {"usable_signal": int(len(s))}
    rows = []
    for r in s.itertuples():
        sid, why = P.resolve(int(r.cik), t)
        if sid is None:
            cause[why] = cause.get(why, 0) + 1
            continue
        j = P.col[sid]
        if not np.isfinite(P.C[i, j]):
            cause["no_trade_at_t"] = cause.get("no_trade_at_t", 0) + 1
            continue
        adv = P.A[i, j]
        if not np.isfinite(adv):
            cause["no_adv"] = cause.get("no_adv", 0) + 1
            continue
        if adv < cm.ADV_LO:
            cause["adv_lt_1M"] = cause.get("adv_lt_1M", 0) + 1
            continue
        if adv >= cm.ADV_HI:
            cause["adv_ge_200M"] = cause.get("adv_ge_200M", 0) + 1
            continue
        if spec.survivor_only and not P.survivor[j]:
            cause["not_survivor"] = cause.get("not_survivor", 0) + 1
            continue
        rows.append({"cik": int(r.cik), "seg": sid, "form": r.form, "value": float(r.value),
                     "adv": float(adv)})
    return pd.DataFrame(rows), cause


CAUSES = ("usable_signal", "no_price_file", "identity_unresolved", "no_live_segment", "no_trade_at_t",
          "no_adv", "adv_lt_1M", "adv_ge_200M", "not_survivor")


def build_panel(spec: T265Spec, sig: pd.DataFrame, P: Panel, grid: list[pd.Timestamp]
                ) -> tuple[list[dict], pd.DataFrame]:
    panel, census = [], []
    for t in grid:
        df, cause = eligible_at(spec, sig, P, t)
        ranked = H.rank_terciles(df) if len(df) else pd.DataFrame(
            columns=["cik", "seg", "form", "value", "adv", "pct", "leg"])
        legs = ranked.leg.value_counts().to_dict() if len(ranked) else {}
        census.append({"rebalance": t.date().isoformat(), "ranked": int(len(ranked)),
                       "long": int(legs.get("long", 0)), "short": int(legs.get("short", 0)),
                       "n_10k": int((ranked.form == "10-K").sum()) if len(ranked) else 0,
                       "n_10q": int((ranked.form == "10-Q").sum()) if len(ranked) else 0,
                       "n_micro": int((ranked.adv < cm.ADV_MID).sum()) if len(ranked) else 0,
                       **{f"cause_{k}": int(cause.get(k, 0)) for k in CAUSES}})
        panel.append({"t": t, "ranked": ranked})
    return panel, pd.DataFrame(census)


def check_census(census: pd.DataFrame) -> list[str]:
    """§7.7 for T-265, AFTER the ADV band: < 300 ranked or < 40 in a tercile HALTS. Empty = pass."""
    bad = []
    for r in census.itertuples():
        if r.ranked < MIN_RANKED:
            bad.append(f"{r.rebalance}: ranked {r.ranked} < {MIN_RANKED}")
        if min(r.long, r.short) < MIN_TERCILE:
            bad.append(f"{r.rebalance}: a tercile < {MIN_TERCILE} (long {r.long}, short {r.short})")
    return bad


# --------------------------------------------------------------------------- #
# returns (only after the census passes)
# --------------------------------------------------------------------------- #
def name_values(P: Panel, segs: list[str], i0: int, mk: list[int], D: float, bil: np.ndarray
                ) -> tuple[np.ndarray, np.ndarray]:
    """Gross value of 1 invested at the close of calendar day i0 at each mark (rows = names).
    Alive: last traded close carried forward inside the life. Death at bar d <= a mark: close(d)
    x (1 + D), then BIL TR from d. Returns (values, died-in-the-quarter flags); a NaN with no
    death HALTS (§7.7)."""
    cols = np.array([P.col[s] for s in segs], dtype=int)
    p0 = P.C[i0, cols]
    if not np.all(np.isfinite(p0)):
        raise Halt("an entry without a traded close at t")
    mk_a = np.asarray(mk, dtype=int)
    V = P.FF[mk_a[None, :], cols[:, None]] / p0[:, None]
    dp = P.death_pos[cols]
    # a death on the formation day itself (bought on its last trade) takes D from that close
    died = (dp >= 0) & (dp >= i0) & (dp < mk_a[-1])
    for k in np.where(died)[0]:
        d = dp[k]
        after = mk_a > d
        V[k, after] = P.C[d, cols[k]] / p0[k] * (1.0 + D) * bil[mk_a[after]] / bil[d]
    bad = ~np.isfinite(V)
    if bad.any():
        k = int(np.where(bad.any(axis=1))[0][0])
        raise Halt(f"NaN value for {segs[k]} from {P.cal[i0].date()} without a death classification")
    return V, died


def side_rate(adv: float, basis: str) -> float:
    if basis == "none":
        return 0.0
    if basis == "flat75":
        return FLAT75_SIDE
    return cm.side_cost(adv, "gate")


def leg_quarter(P: Panel, segs: list[str], advs: dict[str, float], i0: int, mk: list[int], D: float,
                bil: np.ndarray, prev_w: dict[str, float], prev_dead: set[str], basis: str
                ) -> tuple[np.ndarray, dict, set, float, float, int]:
    """One leg over one quarter: monthly returns (cost in the first month), end weights, the names
    that died, cost and turnover (dead proceeds sell free — B-2 §4.1/A1.3), deaths."""
    if not segs:
        raise Halt(f"empty leg at {P.cal[i0].date()}")
    V, died = name_values(P, segs, i0, mk, D, bil)
    Vbar = V.mean(axis=0)
    r = Vbar / np.concatenate([[1.0], Vbar[:-1]]) - 1.0
    w = 1.0 / len(segs)
    cost, turn = 0.0, 0.0
    for s in segs:
        dw = abs(w - (0.0 if s in prev_dead else prev_w.get(s, 0.0)))
        cost += dw * side_rate(advs[s], basis)
        turn += dw
    i_adv = P.A[i0]
    cur = set(segs)
    for s, pw in prev_w.items():
        if s in cur or s in prev_dead:
            continue
        a = i_adv[P.col[s]]
        cost += pw * side_rate(float(a), basis)
        turn += pw
    r = r.copy()
    r[0] -= cost
    end = V[:, -1]
    tot = float(end.sum())
    w_end = {s: float(v / tot) for s, v in zip(segs, end)} if tot > 1e-12 else {}
    dead = {s for s, d in zip(segs, died) if d}
    return r, w_end, dead, cost, turn, int(died.sum())


def twin_returns(P: Panel, name: str, i0: int, mk: list[int]) -> np.ndarray:
    s = getattr(P, name)
    dates = [P.cal[i0]] + [P.cal[m] for m in mk]
    v = s.reindex(pd.DatetimeIndex(dates))
    if v.isna().any():
        raise Halt(f"{name.upper()} TR missing on {[d.date() for d in v[v.isna()].index][:3]} (§7.7)")
    a = v.to_numpy()
    return a[1:] / a[:-1] - 1.0


def run_returns(spec: T265Spec, panel: list[dict], P: Panel, cal_spy: pd.DatetimeIndex,
                hold_end: pd.Timestamp) -> dict:
    D = cm.DEATH_D[spec.death]
    bil = P.bil.reindex(P.cal).to_numpy()
    if not np.all(np.isfinite(bil)):
        raise Halt("BIL TR has a gap on the calendar (§7.7)")
    rebs = [p["t"] for p in panel]
    ends = rebs[1:] + [hold_end]
    months, out = [], {k: [] for k in ("long", "short", "universe", "spy", "iwm", "blend", "iwm_blend")}
    prev_w = {k: {} for k in ("long", "short", "universe")}
    prev_dead = {k: set() for k in ("long", "short", "universe")}
    costs = {k: [] for k in ("long", "short", "universe")}
    turns = {k: [] for k in ("long", "short", "universe")}
    deaths = {k: 0 for k in ("long", "short", "universe")}
    new_share, prev_long = [], None
    q10 = {"short": [], "universe": []}          # the 10-Q-names-only companion (H_OOS)
    for p, t1 in zip(panel, ends):
        t0, ranked = p["t"], p["ranked"]
        marks = H.month_marks(cal_spy, t0, t1)
        i0 = P.pos(t0)
        mk = [P.pos(m) for m in marks]
        advs = dict(zip(ranked.seg, ranked.adv))
        legs = {"long": ranked[ranked.leg == "long"].seg.tolist(),
                "short": ranked[ranked.leg == "short"].seg.tolist(),
                "universe": ranked.seg.tolist()}
        cur_long = set(legs["long"])
        if prev_long is not None and cur_long:
            new_share.append(len(cur_long - prev_long) / len(cur_long))
        prev_long = cur_long
        res = {}
        for name, segs in legs.items():
            r, w_end, dead, c, to, nd = leg_quarter(P, segs, advs, i0, mk, D, bil, prev_w[name],
                                                   prev_dead[name], spec.cost)
            prev_w[name], prev_dead[name] = w_end, dead
            costs[name].append(c)
            turns[name].append(to)
            deaths[name] += nd
            res[name] = r
        if spec.hoos:
            rq = ranked[ranked.form == "10-Q"]
            rq = H.rank_terciles(rq.drop(columns=["pct", "leg"]))
            for name, segs in (("short", rq[rq.leg == "short"].seg.tolist()), ("universe", rq.seg.tolist())):
                if not segs:
                    raise Halt(f"H_OOS 10-Q companion: empty {name} at {t0.date()}")
                V, _ = name_values(P, segs, i0, mk, D, bil)
                Vbar = V.mean(axis=0)
                q10[name].extend((Vbar / np.concatenate([[1.0], Vbar[:-1]]) - 1.0).tolist())
        spy = twin_returns(P, "spy", i0, mk)
        iwm = twin_returns(P, "iwm", i0, mk)
        g_spy = np.cumprod(1.0 + spy)
        for key, leg in (("blend", np.cumprod(1.0 + res["long"])), ("iwm_blend", np.cumprod(1.0 + iwm))):
            Vb = H.SATELLITE * leg + (1.0 - H.SATELLITE) * g_spy
            out[key].extend((Vb / np.concatenate([[1.0], Vb[:-1]]) - 1.0).tolist())
        for k, v in (("long", res["long"]), ("short", res["short"]), ("universe", res["universe"]),
                     ("spy", spy), ("iwm", iwm)):
            out[k].extend(v.tolist())
        months.extend([m.date().isoformat() for m in marks])
    res_all = {"months": months, **{k: np.array(v) for k, v in out.items()},
               "exits": [],
               "turnover": {k: float(np.mean(v)) for k, v in turns.items()},
               "cost_per_rebalance": {k: float(np.mean(v)) for k, v in costs.items()},
               "deaths": deaths,
               "long_new_name_share": float(np.mean(new_share)) if new_share else float("nan")}
    if spec.hoos:
        res_all["q10_short"] = np.array(q10["short"])
        res_all["q10_universe"] = np.array(q10["universe"])
    return res_all


# --------------------------------------------------------------------------- #
# statistics
# --------------------------------------------------------------------------- #
def summarize(res: dict, spec: T265Spec) -> dict:
    out = H.summarize(res)                     # Δ log W (1.25/2.5/97.5), short leg, long-short, ...
    out.pop("n_exits", None)
    iw = res["iwm_blend"]
    spy = res["spy"]
    n = len(spy)
    g = H.boot(n, lambda i: float(np.sum(np.log1p(iw[i])) - np.sum(np.log1p(spy[i]))), 0.95)
    out["iwm_sleeve_dlogw_point"] = g["point"]
    out["iwm_sleeve_dlogw_ci_low_2p5"] = g["ci_low"]
    out["iwm_sleeve_dlogw_ci_high_97p5"] = g["ci_high"]
    out["blend_minus_iwm_sleeve_dlogw_point"] = float(np.sum(np.log1p(res["blend"])) - np.sum(np.log1p(iw)))
    years = n / 12.0
    out["cost_drag_long_bps_per_yr"] = float(res["cost_per_rebalance"]["long"] * 4 * 1e4)
    out["deaths"] = res["deaths"]
    out["minbtl_required_sr_10y_neff36.92"] = MINBTL_SR_10Y
    out["years"] = years
    if spec.hoos:
        s = res["short"] - res["universe"]                       # changers - universe, GROSS
        t = H.newey_west_t(s)
        q = res["q10_short"] - res["q10_universe"]
        tq = H.newey_west_t(q)
        out["hoos"] = {"changers_minus_universe_mean_ann": float(np.mean(s) * 12), "t_hac": t,
                       "threshold": HOOS_T, "passes": bool(np.mean(s) < 0 and np.isfinite(t) and t <= HOOS_T),
                       "q10_only_companion_mean_ann": float(np.mean(q) * 12), "q10_only_companion_t_hac": tq,
                       "q10_only_companion_can_meet_hoos": False}
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _json(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


def load_all() -> tuple[pd.DataFrame, Panel, pd.DatetimeIndex, list[pd.Timestamp], pd.Timestamp, dict]:
    man = verify_manifest()
    P = load_panel()
    sig, info = load_signals(set(P.cik2t))
    cal_spy = pd.DatetimeIndex(H._close(H.TWINS / "SPY_1d.csv", csv=True).index)
    grid = H.rebalance_dates(cal_spy, START, END)
    if len(grid) != 40 or grid[0] < pd.Timestamp("2016-03-01") or grid[-1] > pd.Timestamp(END):
        raise Halt(f"the window is not 40 rebalances 2016-Q1 -> 2025-Q4: {len(grid)}")
    hold_end = cal_spy[cal_spy <= HOLD_CAP].max()
    meta = {"manifest_files": man["n_files"], "signals": info, "panel": {k: v for k, v in P.census.items()
                                                                       if k != "price_census"},
            "price_census_ok": all(r["ok"] for r in P.census["price_census"].values()),
            "grid": [d.date().isoformat() for d in grid], "hold_end": hold_end.date().isoformat()}
    return sig, P, cal_spy, grid, hold_end, meta


def smoke(args: argparse.Namespace) -> int:
    """First 12 months: the first four rebalances, held to the fifth — sanity only, never quoted."""
    sig, P, cal_spy, grid, _, meta = load_all()
    args.out.mkdir(parents=True, exist_ok=True)
    out = {"meta": meta}
    for n in ("gate_similarity", "gate_tone", "hoos_adjacent"):
        spec = SPECS[n]
        panel, census = build_panel(spec, sig, P, grid[:4])
        bad = check_census(census)
        if bad:
            print(f"[b6-t265-smoke] {n}: census HALT {bad}")
            return 2
        res = run_returns(spec, panel, P, cal_spy, grid[4])
        stats = {k: {"mean": float(np.mean(res[k])), "sd": float(np.std(res[k], ddof=1)),
                     "min": float(np.min(res[k])), "max": float(np.max(res[k])),
                     "n_nan": int(np.sum(~np.isfinite(res[k])))}
                 for k in ("long", "short", "universe", "spy", "iwm", "blend")}
        out[n] = {"months": res["months"], "census": census.to_dict("records"), "stats": stats,
                  "deaths": res["deaths"], "turnover": res["turnover"]}
        print(f"[b6-t265-smoke] {n}: {len(res['months'])} months; ranked {census.ranked.tolist()}; "
              f"deaths {res['deaths']}; NaN {sum(v['n_nan'] for v in stats.values())}")
    (args.out / "smoke.json").write_text(_json(out))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B-6 T-265 small-cap arm standalone harness (fail-closed).")
    ap.add_argument("--spec", default="gate_similarity", choices=sorted(SPECS))
    ap.add_argument("--all", action="store_true", help="every pre-named spec (gate first, then H_OOS)")
    ap.add_argument("--census-only", action="store_true", help="manifest + prices + panel + census, no returns")
    ap.add_argument("--smoke", action="store_true", help="first 12 months, sanity only, never quoted")
    ap.add_argument("--write-manifest", action="store_true", help="record the freeze manifest (once, at the freeze)")
    ap.add_argument("--out", type=Path, default=LOCAL / "harness_t265" / "run")
    args = ap.parse_args(argv)
    try:
        if args.write_manifest:
            if MANIFEST.is_file():
                raise Halt(f"{MANIFEST} exists — the freeze manifest is written once")
            m = manifest_now()
            MANIFEST.write_text(_json(m))
            print(f"[b6-t265] manifest {MANIFEST} md5 {_md5(MANIFEST)}: {m['n_files']} files, "
                  f"{sum(r['rows'] for r in m['t265_signal_files'].values())} rows")
            return 0
        if args.smoke:
            return smoke(args)
        sig, P, cal_spy, grid, hold_end, meta = load_all()
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "meta.json").write_text(_json(meta))
        names = list(SPECS) if args.all else [args.spec]
        results = {"_meta": meta}
        for n in names:
            spec = SPECS[n]
            panel, census = build_panel(spec, sig, P, grid)
            census.to_csv(args.out / f"census_{n}.csv", index=False)
            man = pd.concat([p_["ranked"].assign(rebalance=p_["t"].date().isoformat())
                             for p_ in panel if len(p_["ranked"])], ignore_index=True)
            man.to_csv(args.out / f"price_manifest_{n}.csv", index=False)
            bad = check_census(census)
            print(f"[b6-t265] {n}: {len(census)} rebalances; ranked {census.ranked.min()}-"
                  f"{census.ranked.max()}; census {'PASS' if not bad else 'HALT (' + str(len(bad)) + ')'}",
                  flush=True)
            if bad:
                (args.out / f"HALT_{n}.txt").write_text("\n".join(bad) + "\n")
                for b in bad[:20]:
                    print("   ", b)
                if spec.gate or spec.hoos:
                    print(f"[b6-t265] {n}: census failed — no return computed (exit 2)", flush=True)
                    return 2
                results[n] = {"halted": bad}
                continue
            if args.census_only:
                continue
            res = run_returns(spec, panel, P, cal_spy, hold_end)
            pd.DataFrame({k: res[k] for k in ("months", "long", "short", "universe", "spy", "iwm", "blend",
                                              "iwm_blend")}).to_csv(args.out / f"monthly_{n}.csv", index=False)
            results[n] = {"spec": spec.__dict__ | {"forms": list(spec.forms)}, **summarize(res, spec)}
        if args.census_only:
            return 0
        body = _json(results)
        (args.out / "results.json").write_text(body)
        md5 = hashlib.md5(body.encode()).hexdigest()
        (args.out / "results.md5").write_text(md5 + "\n")
        print(f"[b6-t265] results md5 {md5} -> {args.out / 'results.json'}")
        return 0
    except cm.Halt as e:
        print(f"[b6-t265] HALT: {e}", flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
