"""L4 locks — integer shares from the UNADJUSTED close where the substrate carries it (approved
2026-10-22; the defect: `docs/Sources/scan_price_level_consumers_item_d_2026_10_15.md`, L4).

Every lock drives a REAL entrypoint — a planted price file through `DataManager.load_cached` into
`RiskEngine.prepare_order`; `run_backtest_pure` through the real controller; the two census
producers; `optimize_integer_positions` — never a text match. Each was REVERSION-PROVEN: the guarded
line named in the docstring was reverted, the lock failed, the file was restored by `git checkout`
(the results are recorded in `docs/Sessions/2026-10/2026-10-22_session_agent_l4_share_sizing.md`).
"""
from __future__ import annotations

import ast
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core.census import assert_census
from core.measured import MeasurementHalt
from core.share_sizing import (
    BASIS_TOTAL_RETURN,
    BASIS_UNADJUSTED,
    BASIS_UNADJUSTED_NAN,
    share_price_basis_summary,
    size_real_shares,
    size_shares,
    size_units,
    trunc_shares,
)
from engines.engine_b_risk.risk_engine import RiskEngine

REPO = Path(__file__).resolve().parents[1]
TICKER = "ZZT"
EX1, EX2, DIV = "2024-01-16", "2024-03-15", 2.0   # EX1 is the sizing bar; EX2 scales it (TR)


# --------------------------------------------------------------------------- #
# A planted total-return file across two ex-dates, loaded through the REAL loader
# --------------------------------------------------------------------------- #
def _planted(with_unadj: bool = True, nan_on: str | None = None) -> pd.DataFrame:
    """As the total-return writer writes it AFTER EX2: every bar before an ex-date is scaled by
    (1 - d/P_prev). The sizing bar EX1 is itself an ex-date and is scaled by EX2's dividend, so on
    it `Close` (total return) != `close_unadj` (the print that traded)."""
    idx = pd.bdate_range("2023-10-02", "2024-03-28")
    n = len(idx)
    unadj = np.linspace(101.3, 139.7, n)
    p1, p2 = idx.get_loc(pd.Timestamp(EX1)), idx.get_loc(pd.Timestamp(EX2))
    factor = np.ones(n)
    factor[:p2] *= 1.0 - DIV / unadj[p2 - 1]
    factor[:p1] *= 1.0 - DIV / unadj[p1 - 1]
    close = unadj * factor
    df = pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
                       "Volume": 5_000_000.0}, index=idx)
    if with_unadj:
        df["close_unadj"] = unadj
    if nan_on is not None:
        df.loc[pd.Timestamp(nan_on), "close_unadj"] = np.nan
    df.index.name = "Date"
    return df


def _planted_high_price() -> pd.DataFrame:
    """The DAL-class case the scan quotes (~$4,000 prints): a constant 0.625 dividend factor so
    $10,000 buys 2 real shares (3 units) where the old arithmetic bought 4 units."""
    idx = pd.bdate_range("2023-10-02", EX1)
    unadj = np.linspace(3_950.0, 3_990.0, len(idx))
    close = unadj * 0.625
    df = pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
                       "Volume": 5_000_000.0, "close_unadj": unadj}, index=idx)
    df.index.name = "Date"
    return df


def _load(tmp_path: Path, df: pd.DataFrame) -> pd.DataFrame:
    """Through DataManager.load_cached — proves the loader serves the column, not just the test."""
    from engines.data_manager.data_manager import DataManager
    cache = tmp_path / "cache"
    cache.mkdir()
    df.to_csv(cache / f"{TICKER}_1d.csv", date_format="%Y-%m-%d")
    out = DataManager(cache_dir=str(cache)).load_cached(TICKER, "1d")
    assert out is not None and len(out) >= 60
    return out.loc[:EX1]


def _engine(**over) -> RiskEngine:
    cfg = {"min_bars_warmup": 30, "enforce_target_allocations": True, "max_pct_adv": 0.5,
           "sector_map_path": str(REPO / "config" / "__no_such_sector_map__.json"),
           "risk_advisory_enabled": False}
    cfg.update(over)
    return RiskEngine(cfg=cfg)


def _signal() -> dict:
    return {"ticker": TICKER, "side": "long", "strength": 0.5}


# --------------------------------------------------------------------------- #
# Lock 1 — on an ex-date, the share count is notional / close_unadj to the share
# --------------------------------------------------------------------------- #
def test_lock1_path_A_shares_equal_notional_over_close_unadj_through_the_real_sizing_call(tmp_path):
    """Reverted line: `core/share_sizing.py::trunc_shares` `have = np.isfinite(cu) & (cu > 0.0)`
    -> `have = ... & False` (ignore the column). The lock fails: shares_traded None, basis
    total_return, qty == int(notional / Close)."""
    hist = _load(tmp_path, _planted(with_unadj=True))
    close, cu = float(hist["Close"].iloc[-1]), float(hist["close_unadj"].iloc[-1])
    assert hist.index[-1] == pd.Timestamp(EX1) and cu > close, "the sizing bar must be back-adjusted"
    re = _engine()
    order = re.prepare_order(_signal(), equity=100_000.0, df_hist=hist, current_qty=0,
                             target_weights={TICKER: 0.10})
    assert order is not None, re.last_skip_by_ticker
    shares = math.floor(10_000.0 / cu)                       # the shares the print allowed
    units = math.floor(shares * cu / close)                  # their value, in ledger units
    assert order["meta"]["shares_traded"] == shares
    assert order["qty"] == units
    assert order["meta"]["share_price_basis"] == BASIS_UNADJUSTED
    assert order["meta"]["close_unadj"] == cu
    assert order["meta"]["sizing_mode"] == "target_weight"
    # the dollars deployed are the dollars that would have traded, to within one unit
    assert abs(order["qty"] * close - shares * cu) < close
    assert re.share_price_basis_counts == {BASIS_UNADJUSTED: 1}


def test_lock1_high_priced_name_buys_the_real_shares_not_the_adjusted_units(tmp_path):
    """$10,000 at a ~$4,000 print (adjusted ~$2,500): 2 real shares, carried as 3 units. The old
    `int(delta_notional / price)` bought 4 — the defect the scan quotes for DAL."""
    hist = _load(tmp_path, _planted_high_price())
    close, cu = float(hist["Close"].iloc[-1]), float(hist["close_unadj"].iloc[-1])
    re = _engine()
    order = re.prepare_order(_signal(), equity=100_000.0, df_hist=hist, current_qty=0,
                             target_weights={TICKER: 0.10})
    assert order is not None, re.last_skip_by_ticker
    assert order["meta"]["shares_traded"] == 2 == math.floor(10_000.0 / cu)
    assert order["qty"] == 3 == math.floor(2 * cu / close)
    assert int(10_000.0 / close) == 4, "the old arithmetic bought 4 units here"


def test_lock1_path_B_atr_sizing_lands_on_real_shares(tmp_path):
    """Path B (no target weights): the ATR budget lands in units; the integer step converts them to
    the real shares the print allowed and back to units. Reverted line: `risk_engine.py`
    `sizing = size_units(max(target_qty - abs(int(current_qty)), 0), price, close_unadj)` ->
    `size_units(..., price, None)`. The lock fails: basis total_return."""
    hist = _load(tmp_path, _planted(with_unadj=True))
    close, cu = float(hist["Close"].iloc[-1]), float(hist["close_unadj"].iloc[-1])
    re = _engine(enforce_target_allocations=False)
    order = re.prepare_order(_signal(), equity=100_000.0, df_hist=hist, current_qty=0,
                             target_weights=None)
    assert order is not None, re.last_skip_by_ticker
    meta = order["meta"]
    assert meta["sizing_mode"] == "atr_risk" and meta["share_price_basis"] == BASIS_UNADJUSTED
    shares = math.floor(meta["target_qty"] * close / cu)     # the units' dollars, in real shares
    assert meta["shares_traded"] == shares
    assert order["qty"] == math.floor(shares * cu / close)
    assert order["qty"] <= meta["target_qty"]


def _planted_factor(volume: float, factor: float = 0.625) -> pd.DataFrame:
    """A constant dividend factor (SPY-2000-like 0.625) ending at a $140 print on EX1, with a
    chosen constant Volume so the ADV limit (Volume × max_pct_adv) is exact."""
    idx = pd.bdate_range("2023-10-02", EX1)
    unadj = np.linspace(120.0, 140.0, len(idx))
    close = unadj * factor
    df = pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
                       "Volume": float(volume), "close_unadj": unadj}, index=idx)
    df.index.name = "Date"
    return df


# --------------------------------------------------------------------------- #
# Lock 1-ADV — the liquidity check and the clip are in REAL shares (Volume is real shares)
# --------------------------------------------------------------------------- #
def test_lock1_adv_check_runs_on_real_shares_not_units(tmp_path):
    """$10,000 at a $140 print marked $87.5: 71 real shares carried as 113 units. ADV limit 80
    shares (Volume 8,000 × max_pct_adv 0.01): 71 passes; a check on the 113 units would clip.
    Reverted line: `risk_engine.py` `liq_qty = sizing.shares_traded if ... else add_qty` ->
    `liq_qty = add_qty`. The lock fails: the order is clipped."""
    hist = _load(tmp_path, _planted_factor(volume=8_000.0))
    close, cu = float(hist["Close"].iloc[-1]), float(hist["close_unadj"].iloc[-1])
    assert (math.floor(10_000.0 / cu), math.floor(71 * cu / close)) == (71, 113)
    re = _engine(max_pct_adv=0.01)
    order = re.prepare_order(_signal(), equity=100_000.0, df_hist=hist, current_qty=0,
                             target_weights={TICKER: 0.10})
    assert order is not None, re.last_skip_by_ticker
    assert (order["qty"], order["meta"]["shares_traded"]) == (113, 71)
    assert "liquidity_clipped" not in order["meta"]
    assert TICKER not in re.last_skip_by_ticker


def test_lock1_adv_clip_is_in_real_shares_carried_as_units(tmp_path):
    """ADV limit 10 shares (Volume 1,000 × 0.01): 71 shares clip to 10, carried as
    trunc(10 × 140 / 87.5) = 16 units. Reverted line: `risk_engine.py`
    `sizing = size_real_shares(limit_qty, price, close_unadj)` -> `add_qty = limit_qty` (a clip in
    units). The lock fails: qty 10."""
    hist = _load(tmp_path, _planted_factor(volume=1_000.0))
    close, cu = float(hist["Close"].iloc[-1]), float(hist["close_unadj"].iloc[-1])
    re = _engine(max_pct_adv=0.01)
    order = re.prepare_order(_signal(), equity=100_000.0, df_hist=hist, current_qty=0,
                             target_weights={TICKER: 0.10})
    assert order is not None, re.last_skip_by_ticker
    assert order["meta"]["shares_traded"] == 10
    assert order["qty"] == 16 == math.floor(10 * cu / close)
    assert order["meta"]["liquidity_clipped"] is True
    assert re.last_skip_by_ticker.get(TICKER) == "liquidity_limit_exceeded"   # as before: noted, then clipped
    assert abs(order["qty"] * close - 10 * cu) < close


# --------------------------------------------------------------------------- #
# Lock 2 — no close_unadj column: the basis is RECORDED total_return, the count is unchanged
# --------------------------------------------------------------------------- #
def test_lock2_without_the_column_the_basis_is_recorded_total_return_and_the_count_is_unchanged(
        tmp_path, monkeypatch):
    """Reverted line: `core/share_sizing.py::read_close_unadj` `if CLOSE_UNADJ_COLUMN not in row:
    return None` -> `return float(row["Close"])` (a silent fallback that sizes on Close under the
    unadjusted label). The lock fails: basis unadjusted, shares_traded not None."""
    hist = _load(tmp_path, _planted(with_unadj=False))
    assert "close_unadj" not in hist.columns
    close = float(hist["Close"].iloc[-1])
    re = _engine()
    order = re.prepare_order(_signal(), equity=100_000.0, df_hist=hist, current_qty=0,
                             target_weights={TICKER: 0.10})
    assert order is not None, re.last_skip_by_ticker
    assert order["qty"] == int(10_000.0 / close), "the pre-cutover arithmetic, byte for byte"
    assert order["meta"]["share_price_basis"] == BASIS_TOTAL_RETURN
    assert order["meta"]["shares_traded"] is None and order["meta"]["close_unadj"] is None
    assert re.share_price_basis_counts == {BASIS_TOTAL_RETURN: 1}
    rec = share_price_basis_summary(re.share_price_basis_counts)
    assert rec == {"basis": "total_return", "counts": {"total_return": 1}, "n_sized": 1}
    # In a MEASURED run the same sizing runs (no halt) and the record is a census FACT, not a failure.
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    re2 = _engine()
    order2 = re2.prepare_order(_signal(), equity=100_000.0, df_hist=hist, current_qty=0,
                               target_weights={TICKER: 0.10})
    assert order2 is not None and order2["qty"] == order["qty"]
    v = assert_census({"census": {**_CANONICAL, "share_price_basis": rec},
                       "bootstrap_ci_skip_reason": "lock"})
    assert v.canonical, v.failures


def test_lock2b_a_hole_in_a_present_column_halts_measured_and_is_recorded_otherwise(tmp_path,
                                                                                    monkeypatch):
    """The column exists but the sizing bar is NaN: outside measured mode the bar sizes on Close
    under its OWN label (unadjusted_nan — never a silent unadjusted or total_return); in a measured
    run `read_close_unadj` HALTS through core.measured. Reverted line: `read_close_unadj`
    `halt_or_degrade(...)` removed. The lock fails: no MeasurementHalt."""
    hist = _load(tmp_path, _planted(with_unadj=True, nan_on=EX1))
    assert np.isnan(hist["close_unadj"].iloc[-1])
    close = float(hist["Close"].iloc[-1])
    monkeypatch.delenv("ARCHONDEX_MEASURED", raising=False)
    monkeypatch.delenv("ARCHONDEX_HERMETIC", raising=False)
    re = _engine()
    order = re.prepare_order(_signal(), equity=100_000.0, df_hist=hist, current_qty=0,
                             target_weights={TICKER: 0.10})
    assert order is not None and order["qty"] == int(10_000.0 / close)
    assert order["meta"]["share_price_basis"] == BASIS_UNADJUSTED_NAN
    assert re.share_price_basis_counts == {BASIS_UNADJUSTED_NAN: 1}
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    with pytest.raises(MeasurementHalt):
        _engine().prepare_order(_signal(), equity=100_000.0, df_hist=hist, current_qty=0,
                                target_weights={TICKER: 0.10})


# --------------------------------------------------------------------------- #
# Lock 3 — BOTH census producers write share_price_basis; an unmeasured basis fails the gate
# --------------------------------------------------------------------------- #
_CANONICAL = {
    "edges_blind": [], "edges_errored": {}, "n_resolved": 10, "n_in_panel": 10,
    "n_trades": 5, "trades_canon_md5": "0" * 32, "trades_empty": False,
    "fundamentals_blind": 0, "regime_unknown_frac": 0.1, "regime_total_bars": 100,
    "config_provenance": {"degraded": False}, "data_feed": {"yfinance_tickers": []},
    "data_exclusions": {}, "census_kind": "backtest", "regime_layer": "on",
}


def _assigned_from(fn_node, key: str, producer: str) -> bool:
    for a in ast.walk(fn_node):
        if (isinstance(a, ast.Assign) and isinstance(a.value, ast.Call)
                and (getattr(a.value.func, "id", None) or getattr(a.value.func, "attr", None)) == producer
                and any(isinstance(t, ast.Subscript) and ast.unparse(t.slice).strip("'\"") == key
                        for t in a.targets)):
            return True
    return False


def test_lock3_both_producers_write_share_price_basis_from_the_one_summary_function():
    """Reverted line: `_build_census` `census["share_price_basis"] = share_price_basis_summary(...)`
    removed (and the candidate block's). The lock fails on the AST and on the candidate record."""
    tree = ast.parse((REPO / "backtester" / "backtest_controller.py").read_text())
    build = next(n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef) and n.name == "_build_census")
    assert _assigned_from(build, "share_price_basis", "share_price_basis_summary")

    from engines.engine_d_discovery.discovery import candidate_census_block

    class _C:
        nonzero_calls, errors = 1, 0
    idx = pd.bdate_range("2025-01-02", periods=20)
    clean = {t: pd.DataFrame({"Close": 1.0}, index=idx) for t in ("SPY", "AAA")}
    window = (str(idx[0].date()), str(idx[-1].date()))
    block = candidate_census_block("cand_v1", _C(), n_trades=4, data_map=clean, window=window,
                                   share_basis_counts={"unadjusted": 3, "total_return": 1})
    assert block["share_price_basis"] == {"basis": "mixed",
                                          "counts": {"total_return": 1, "unadjusted": 3},
                                          "n_sized": 4}
    assert assert_census({"census": block, "bootstrap_ci_skip_reason": "lock"}).canonical
    # counts never supplied -> an ERROR record -> the gate refuses (the basis was not measured)
    missing = candidate_census_block("cand_v1", _C(), n_trades=4, data_map=clean, window=window)
    assert "error" in missing["share_price_basis"]
    v = assert_census({"census": missing, "bootstrap_ci_skip_reason": "lock"})
    assert not v.canonical and any("share_price_basis" in f for f in v.failures)


def test_lock3_gate_shapes_recorded_fact_errored_record_missing_record():
    base = {"census": dict(_CANONICAL), "bootstrap_ci_skip_reason": "lock"}
    v = assert_census(base)
    assert v.canonical and any("share_price_basis" in w for w in v.warnings)   # predates the field
    ok = {**base, "census": {**_CANONICAL, "share_price_basis":
                             {"basis": "total_return", "counts": {"total_return": 9}, "n_sized": 9}}}
    v = assert_census(ok)
    assert v.canonical and not any("share_price_basis" in w for w in v.warnings)
    bad = {**base, "census": {**_CANONICAL, "share_price_basis": {"error": "planted"}}}
    assert not assert_census(bad).canonical
    assert share_price_basis_summary({}) == {"basis": "none", "counts": {}, "n_sized": 0}
    assert share_price_basis_summary({"unadjusted": 7}) == {"basis": "unadjusted",
                                                            "counts": {"unadjusted": 7}, "n_sized": 7}
    assert "error" in share_price_basis_summary(None)


def test_lock3_end_to_end_the_counter_is_fed_through_the_real_controller():
    """The first artifact of the wiring: `run_backtest_pure` (the real controller + risk engine)
    on a planted two-name map with a speaking edge leaves the counter on the pure result — the
    unadjusted basis when the frames carry close_unadj, total_return when they do not."""
    from orchestration.run_backtest_pure import PureBacktestResult, run_backtest_pure
    assert "share_price_basis_counts" in PureBacktestResult.__dataclass_fields__

    class _Edge:
        def compute_signals(self, data_map, now):
            return {"AAA": 0.8, "BBB": 0.6}

    def _map(with_unadj: bool):
        base = _planted(with_unadj=with_unadj)
        return {"AAA": base.copy(), "BBB": (base * 1.1).copy()}

    common = dict(edges={"spk": _Edge()}, edge_weights={"spk": 1.0},
                  start_date="2024-01-02", end_date="2024-03-28",
                  exec_params={"slippage_bps": 5.0, "slippage_model": "fixed", "commission": 0.0},
                  initial_capital=100_000.0, use_regime_detector=False, use_governor=False)
    res_un = run_backtest_pure(data_map=_map(True), **common)
    res_tr = run_backtest_pure(data_map=_map(False), **common)
    assert res_un.share_price_basis_counts.get(BASIS_UNADJUSTED, 0) > 0, res_un.share_price_basis_counts
    assert set(res_un.share_price_basis_counts) == {BASIS_UNADJUSTED}
    assert res_tr.share_price_basis_counts.get(BASIS_TOTAL_RETURN, 0) > 0, res_tr.share_price_basis_counts
    assert set(res_tr.share_price_basis_counts) == {BASIS_TOTAL_RETURN}


# --------------------------------------------------------------------------- #
# Lock 4 — ONE helper: Engine B and Engine C's parity baseline both read it; no duplicated arithmetic
# --------------------------------------------------------------------------- #
def _imports_from(tree: ast.AST, module: str) -> set:
    return {a.name for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module == module for a in n.names}


def _calls(node: ast.AST) -> set:
    return {(getattr(c.func, "id", None) or getattr(c.func, "attr", None))
            for c in ast.walk(node) if isinstance(c, ast.Call)}


def test_lock4_risk_engine_and_dynamic_optimizer_call_the_one_helper_and_divide_nowhere_else():
    """Reverted line: `risk_engine.py` `sizing = size_shares(delta_notional, price, close_unadj)`
    -> `add_qty = int(delta_notional / price)` (the defect line restored). The lock fails: an
    `int(<a / b>)` inside prepare_order."""
    rt = ast.parse((REPO / "engines" / "engine_b_risk" / "risk_engine.py").read_text())
    assert {"size_shares", "size_units", "size_real_shares", "read_close_unadj"} <= \
        _imports_from(rt, "core.share_sizing")
    # risk_engine.py defines `prepare_order` TWICE (a dead stub near line 350 precedes the live
    # method); Python binds the LAST definition, so the lock reads that one.
    prep = [n for n in ast.walk(rt) if isinstance(n, ast.FunctionDef) and n.name == "prepare_order"][-1]
    assert {"size_shares", "size_units", "size_real_shares", "read_close_unadj"} <= _calls(prep)
    int_of_quotient = [c.lineno for c in ast.walk(prep)
                       if isinstance(c, ast.Call) and getattr(c.func, "id", None) == "int"
                       and c.args and isinstance(c.args[0], ast.BinOp) and isinstance(c.args[0].op, ast.Div)]
    assert not int_of_quotient, f"prepare_order truncates a quotient outside the helper at {int_of_quotient}"

    ot = ast.parse((REPO / "engines" / "engine_c_portfolio" / "dynamic_optimizer.py").read_text())
    assert "trunc_shares" in _imports_from(ot, "core.share_sizing")
    naive = next(n for n in ast.walk(ot)
                 if isinstance(n, ast.FunctionDef) and n.name == "naive_rounded_positions")
    assert "trunc_shares" in _calls(naive)
    np_trunc = [c.lineno for c in ast.walk(ot) if isinstance(c, ast.Call)
                and isinstance(c.func, ast.Attribute) and c.func.attr == "trunc"]
    assert not np_trunc, f"dynamic_optimizer truncates on its own at {np_trunc}"
    opt = next(n for n in ast.walk(ot)
               if isinstance(n, ast.FunctionDef) and n.name == "optimize_integer_positions")
    assert "prices_unadj" in {a.arg for a in opt.args.args} and "halt_or_degrade" in _calls(opt)

    pt = ast.parse((REPO / "engines" / "engine_c_portfolio" / "portfolio_engine.py").read_text())
    apply = next(n for n in ast.walk(pt)
                 if isinstance(n, ast.FunctionDef) and n.name == "_apply_dynamic_optimization")
    passed = [kw.arg for c in ast.walk(apply) if isinstance(c, ast.Call)
              and getattr(c.func, "id", None) == "optimize_integer_positions" for kw in c.keywords]
    assert "prices_unadj" in passed


def test_lock4_parity_baseline_is_engine_b_arithmetic_on_both_bases():
    rng = np.random.default_rng(7)
    n = 6
    w = rng.dirichlet(np.ones(n)) * 0.9
    p = np.exp(rng.uniform(np.log(5.0), np.log(500.0), n))
    cur = rng.integers(-20, 40, n).astype(np.int64)
    eq = 25_000.0
    cu = p * rng.uniform(1.0, 1.6, n)
    cu[2] = np.nan                                              # one name without the column
    from engines.engine_c_portfolio.dynamic_optimizer import naive_rounded_positions
    got = naive_rounded_positions(w, p, cur, eq, prices_unadj=cu)
    want = np.array([cur[i] + size_shares(w[i] * eq - cur[i] * p[i], p[i],
                                          None if np.isnan(cu[i]) else cu[i]).qty for i in range(n)])
    assert np.array_equal(got, want)
    old = cur + np.trunc((w * eq - cur * p) / p).astype(np.int64)   # the pre-L4 expression
    assert np.array_equal(naive_rounded_positions(w, p, cur, eq), old)


def test_lock4_optimizer_refuses_the_real_share_lattice_declared_or_halted(monkeypatch):
    from engines.engine_c_portfolio.dynamic_optimizer import optimize_integer_positions
    tickers = ["T00", "T01"]
    weights, prices = {"T00": 0.3, "T01": 0.3}, {"T00": 50.0, "T01": 80.0}
    cov = pd.DataFrame(np.eye(2) * 1e-4, index=tickers, columns=tickers)
    monkeypatch.delenv("ARCHONDEX_MEASURED", raising=False)
    monkeypatch.delenv("ARCHONDEX_HERMETIC", raising=False)
    res = optimize_integer_positions(weights, prices, {"T00": 0, "T01": 0}, 10_000.0, cov,
                                     prices_unadj={"T00": 60.0})
    assert res.skipped and res.skip_reason == "unadjusted_basis_lattice_unsupported"
    assert res.weights == weights
    # None / absent / NaN -> today's path runs
    ok = optimize_integer_positions(weights, prices, {"T00": 0, "T01": 0}, 10_000.0, cov,
                                    prices_unadj={"T00": float("nan")})
    assert not ok.skipped
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    with pytest.raises(MeasurementHalt):
        optimize_integer_positions(weights, prices, {"T00": 0, "T01": 0}, 10_000.0, cov,
                                   prices_unadj={"T00": 60.0})


# --------------------------------------------------------------------------- #
# Lock 5 — the paper and live paths never see the helper (they size on live broker prices)
# --------------------------------------------------------------------------- #
def test_lock5_paper_and_live_paths_never_import_or_name_the_helper():
    """Reverted check: plant `from core.share_sizing import size_shares` into a paper_trader
    module. The lock fails on the import."""
    forbidden_names = {"close_unadj", "size_shares", "size_units", "size_real_shares",
                       "read_close_unadj", "share_price_basis", "trunc_shares"}
    offenders = []
    for root in (REPO / "paper_trader", REPO / "live_trader"):
        if not root.exists():
            continue
        for py in sorted(root.rglob("*.py")):
            tree = ast.parse(py.read_text())
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("core.share_sizing"):
                    offenders.append(f"{py}:{n.lineno} imports core.share_sizing")
                elif isinstance(n, ast.Import) and any(a.name.startswith("core.share_sizing") for a in n.names):
                    offenders.append(f"{py}:{n.lineno} imports core.share_sizing")
                elif isinstance(n, (ast.Name, ast.Attribute)) and \
                        (getattr(n, "id", None) or getattr(n, "attr", None)) in forbidden_names:
                    offenders.append(f"{py}:{n.lineno} names {getattr(n, 'id', None) or n.attr}")
                elif isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in forbidden_names:
                    offenders.append(f"{py}:{n.lineno} string {n.value!r}")
    assert not offenders, "\n".join(offenders)


# --------------------------------------------------------------------------- #
# Lock 7 — the total-return path is today's arithmetic byte for byte; the unadjusted path is exact
# --------------------------------------------------------------------------- #
def test_lock7_total_return_path_is_int_of_the_quotient_and_the_unadjusted_path_is_exact_on_integers():
    rng = np.random.default_rng(0)
    for _ in range(20_000):
        n = rng.uniform(-50_000, 50_000)
        p = float(np.exp(rng.uniform(np.log(0.5), np.log(5_000.0))))
        assert size_shares(n, p, None).qty == int(n / p)
        u = rng.uniform(0, 500)
        assert size_units(u, p, None).qty == int(u)
        k = int(rng.integers(1, 500))
        assert size_real_shares(k, p, None).qty == k
        # a non-payer (close_unadj == Close): an exact k-unit trade is k shares and k units
        r = size_units(float(k), p, p)
        assert (r.qty, r.shares_traded, r.basis) == (k, k, BASIS_UNADJUSTED)
    units, shares = trunc_shares(np.array([10_000.0, -10_000.0, 500.0]), np.array([87.5] * 3),
                                 np.array([140.0, np.nan, 140.0]))
    assert units.tolist() == [113.0, -114.0, 4.0] and shares[0] == 71.0 and np.isnan(shares[1])
    s = size_shares(10_000.0, 87.5, 140.0)                # SPY, 2000: factor 0.625
    assert (s.qty, s.shares_traded) == (113, 71) and abs(s.qty * 87.5 - 71 * 140.0) < 87.5
