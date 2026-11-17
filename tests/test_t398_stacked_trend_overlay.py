"""T-398 — the stacked trend overlay harness: simulator identities, the frozen decision cell, the
integrity checks and the fail-closed refusals. Synthetic inputs only: no network, no data files.

Prereg: docs/Sources/prereg_t398_stacked_trend_overlay_2026-11-14.md (+ amendments 1-3).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import t398_stacked_trend_overlay as h


def _cal(n: int = 300, start: str = "2010-07-01") -> pd.DatetimeIndex:
    return pd.bdate_range(start, periods=n)


def _px(raw: np.ndarray, idx: pd.DatetimeIndex, adj: np.ndarray | None = None) -> pd.DataFrame:
    return pd.DataFrame({"adj_close": raw if adj is None else adj, "raw_close": raw}, index=idx).astype(float)


def _no_actions() -> pd.DataFrame:
    return pd.DataFrame(columns=["Dividends", "Capital Gains"], index=pd.DatetimeIndex([], name="Date"))


def _window(n: int = 260, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    dates = _cal(n, "2011-01-03")
    e = rng.normal(0.0004, 0.01, n)
    return {"dates": dates, "base_date": dates[0] - pd.Timedelta(days=3), "e": e,
            "x": rng.normal(0.0001, 0.005, n), "dcal": np.where(dates.dayofweek == 0, 3.0, 1.0),
            "bench": h.equity_sleeve(e)}


# --------------------------------------------------------------------------- the frozen decision cell
def test_decision_cell_constants_are_the_frozen_ones():
    assert (h.ER_S, h.S_H1, h.H_SURV) == (0.0100, 0.0050, 0.0100)
    assert (h.N_ITER, h.SEED, h.BLOCK_DAILY, h.SENS2_DAILY) == (1000, 0, 21, 252)
    assert (h.MIN_MEMBERS, h.E1_MIN_YEARS, h.E2_MIN_CORR) == (3, 12.0, 0.50)
    assert h.WINDOW_END == pd.Timestamp("2025-12-31") and h.YF_ASOF == "2026-01-01"
    assert h.ER_E == pytest.approx(0.0009)
    assert len(h.CANDIDATES) == 15 and set(h.FLAGGED) == {"RYMFX", "WTMF", "FMF", "EVOIX"}


def test_amendment_3_aqmix_er_is_the_conservative_one_and_the_as_written_value_is_kept():
    assert h.MEMBERSHIP_FROZEN["AQMIX"]["er"] == pytest.approx(0.0125)
    assert "unverified" in h.MEMBERSHIP_FROZEN["AQMIX"]["er_source"]
    assert h.AQMIX_ER_AS_WRITTEN == pytest.approx(0.0200)
    # no other member's frozen ER sits at or above the cap
    assert all(v["er"] < h.ER_CAP for k, v in h.MEMBERSHIP_FROZEN.items())
    assert set(h.MEMBERSHIP_FROZEN) == set(h.CANDIDATES)


# --------------------------------------------------------------------------- metadata rules (A1.1-2)
def test_er_units_are_fixed_by_spy():
    assert h.er_unit_from_spy(0.0945) == "percent"
    assert h.er_unit_from_spy(0.000945) == "fraction"
    assert h.er_unit_from_spy(None) is None and h.er_unit_from_spy(9.45) is None
    assert h.convert_er(1.45, "percent") == pytest.approx(0.0145)
    assert h.convert_er(0.0145, "fraction") == pytest.approx(0.0145)
    assert h.convert_er(0.05, "percent") is None          # 0.05 % is outside [0.20 %, 5.00 %]
    assert h.convert_er(1.45, None) is None


# --------------------------------------------------------------------------- §5: the stacked return
def test_cash_is_not_counted_twice():
    """A trend fund's TR = futures P&L + T-bill yield − its fee. The stack must earn equity + the
    futures P&L − spread − the stack's fee, with NO second T-bill yield (§5.2)."""
    n = 250
    rng = np.random.default_rng(1)
    e, pnl = rng.normal(0.0003, 0.01, n), rng.normal(0.0002, 0.006, n)
    cash, er_f, dcal = np.full(n, 0.05 / 360.0), 0.0150, np.ones(n)
    fund_tr = pnl + cash - er_f / h.TD
    x = fund_tr - cash + er_f / h.TD                       # §4.1
    np.testing.assert_allclose(x, pnl, atol=1e-15)
    stack = h.stacked_sleeve(e, x, dcal, s=h.S_H1, h_surv=0.0)
    np.testing.assert_allclose(stack, e + pnl - h.S_H1 / 360.0 - h.ER_S / h.TD, atol=1e-15)
    # the T-296 error: the fund's TOTAL return added to equity, same fees — overstates by the cash yield
    naive = h.stacked_sleeve(e, fund_tr + er_f / h.TD, dcal, s=h.S_H1, h_surv=0.0)
    np.testing.assert_allclose(naive - stack, cash, atol=1e-15)
    assert float(np.mean(naive - stack) * h.TD) == pytest.approx(0.05 * h.TD / 360.0)


def test_decision_arm_minus_benchmark_is_the_overlay_net_of_its_costs():
    w = _window()
    r = h.arm_returns(w, 1.0)
    want = w["x"] - h.H_SURV / h.TD - h.S_H1 * w["dcal"] / 360.0 - (h.ER_S - h.ER_E) / h.TD
    np.testing.assert_allclose(r - w["bench"], want, atol=1e-15)


def test_zero_overlay_at_the_equity_fee_is_the_benchmark():
    w = _window()
    free = h.stacked_sleeve(w["e"], np.zeros(len(w["e"])), w["dcal"], 0.0, 0.0, er_s=h.ER_E)
    np.testing.assert_allclose(free, w["bench"], atol=1e-15)


def test_two_sleeve_arms_lie_between_the_sleeves_and_pay_a_rebalance_cost():
    w = _window()
    r100, r50, r25 = (h.arm_returns(w, k) for k in (1.0, 0.5, 0.25))
    tot = [float(np.sum(np.log1p(r))) for r in (w["bench"], r25, r50, r100)]
    lo, hi = min(tot[0], tot[3]), max(tot[0], tot[3])
    assert lo - 1e-3 <= tot[1] <= hi + 1e-3 and lo - 1e-3 <= tot[2] <= hi + 1e-3
    # first day: no drift yet, so the +50 % arm is exactly the 50/50 mix
    assert r50[0] == pytest.approx(0.5 * w["bench"][0] + 0.5 * r100[0], abs=1e-15)
    # a costless identical-sleeve book would equal the benchmark; ours differs because sleeves differ
    assert not np.allclose(r50, r100)


def test_survivorship_haircut_moves_the_arm_one_for_one():
    w = _window()
    d0 = h.arm_returns(w, 1.0, h_surv=0.0) - h.arm_returns(w, 1.0, h_surv=0.02)
    np.testing.assert_allclose(d0, 0.02 / h.TD, atol=1e-15)


# --------------------------------------------------------------------------- membership (A1.1-4/5)
def test_a_fund_enters_the_month_after_the_month_of_its_first_price():
    cal = _cal(120, "2010-07-01")
    first = pd.Timestamp("2010-08-03")
    idx = cal[cal >= first]
    adj = pd.Series(np.linspace(10.0, 11.0, len(idx)), index=idx)
    ret, entry, last, dropped = h.member_returns(adj, cal)
    assert entry == pd.Timestamp("2010-09-01") and ret.index[0] == entry
    assert last == cal[-1] and dropped == 0 and np.isfinite(ret.values).all()
    # a first price on the last day of July enters in August
    idx2 = cal[cal >= pd.Timestamp("2010-07-30")]
    _, entry2, _, _ = h.member_returns(pd.Series(np.linspace(10, 11, len(idx2)), index=idx2), cal)
    assert entry2 == pd.Timestamp("2010-08-02")


def test_a_missing_price_day_is_filled_and_caught_up_never_invented():
    cal = _cal(80, "2010-07-01")
    adj = pd.Series(np.linspace(10.0, 12.0, len(cal)), index=cal)
    hole = cal[50]
    ret, _, _, _ = h.member_returns(adj.drop(hole), cal)
    assert ret.loc[hole] == 0.0
    assert ret.loc[cal[51]] == pytest.approx(adj.loc[cal[51]] / adj.loc[cal[49]] - 1.0)


# --------------------------------------------------------------------------- integrity (A1.1-12)
def test_d1_flags_an_unrecorded_distribution_and_a_recorded_one_clears_it():
    cal = _cal(60)
    raw = np.full(60, 10.0)
    raw[30:] = 9.5                                          # −5 % with nothing recorded
    others = pd.DataFrame({"B": np.zeros(60), "C": np.zeros(60)}, index=cal)
    flags = h.integrity_flags("A", _px(raw, cal), _no_actions(), cal, others)
    assert [(f["check"], f["date"]) for f in flags if f["check"] == "D1"] == [("D1", str(cal[30].date()))]
    act = pd.DataFrame({"Dividends": [0.5], "Capital Gains": [0.0]}, index=pd.DatetimeIndex([cal[30]], name="Date"))
    assert not [f for f in h.integrity_flags("A", _px(raw, cal), act, cal, others) if f["check"] == "D1"]
    # one trading day off still clears; two days off does not
    act1 = act.set_index(pd.DatetimeIndex([cal[31]], name="Date"))
    act2 = act.set_index(pd.DatetimeIndex([cal[32]], name="Date"))
    assert not [f for f in h.integrity_flags("A", _px(raw, cal), act1, cal, others) if f["check"] == "D1"]
    assert [f for f in h.integrity_flags("A", _px(raw, cal), act2, cal, others) if f["check"] == "D1"]


def test_d1_is_silent_on_a_day_the_whole_category_fell():
    cal = _cal(60)
    raw = np.full(60, 10.0)
    raw[30:] = 9.5
    down = np.zeros(60)
    down[30] = -0.03
    others = pd.DataFrame({"B": down, "C": down}, index=cal)
    assert not [f for f in h.integrity_flags("A", _px(raw, cal), _no_actions(), cal, others) if f["check"] == "D1"]


def test_d2_d3_d4_fire_on_planted_defects_and_not_on_a_clean_series():
    cal = _cal(80)
    rng = np.random.default_rng(3)
    clean = 10.0 * np.cumprod(1.0 + rng.normal(0, 0.004, 80))
    others = pd.DataFrame({"B": np.zeros(80), "C": np.zeros(80)}, index=cal)
    assert h.integrity_flags("A", _px(clean, cal), _no_actions(), cal, others) == []
    stale = clean.copy()
    stale[20:25] = stale[20]                                # five identical closes
    assert "D2" in {f["check"] for f in h.integrity_flags("A", _px(stale, cal), _no_actions(), cal, others)}
    four = clean.copy()
    four[20:24] = four[20]                                  # four identical closes: below the bar
    assert "D2" not in {f["check"] for f in h.integrity_flags("A", _px(four, cal), _no_actions(), cal, others)}
    keep = np.ones(80, dtype=bool)
    keep[30:36] = False                                     # a six-day gap
    assert "D3" in {f["check"] for f in h.integrity_flags("A", _px(clean[keep], cal[keep]), _no_actions(), cal, others)}
    jump = clean.copy()
    jump[40:] *= 1.09
    assert "D4" in {f["check"] for f in h.integrity_flags("A", _px(jump, cal), _no_actions(), cal, others)}


# --------------------------------------------------------------------------- §8.4
def test_episodes_run_from_the_day_after_the_high_to_the_day_of_the_low():
    r = np.array([0.02, -0.06, -0.06, 0.01, -0.02, 0.20, -0.03, 0.05])
    eps = h.find_episodes(r)
    assert len(eps) == 1
    a, b, dep = eps[0]
    assert (a, b) == (1, 4)                                 # the high is after return 0; the low after return 4
    assert dep == pytest.approx(0.94 * 0.94 * 1.01 * 0.98 - 1.0)
    assert h.find_episodes(np.array([0.01, -0.05, 0.10])) == []          # a 5 % dip is not an episode
    last = h.find_episodes(np.array([0.05, -0.08, -0.08]))               # unrecovered at the window end
    assert len(last) == 1 and last[0][:2] == (1, 2)


def test_worst_rolling_and_drought_on_a_known_path():
    d = np.concatenate([np.full(100, 0.001), np.full(50, -0.004), np.full(100, 0.001)])
    dates = _cal(250)
    wr = h.worst_rolling(d, dates, win=50)
    assert wr["sum_d"] == pytest.approx(-0.2) and wr["start"] == str(dates[100].date())
    assert h.worst_rolling(d, dates, win=756) is None
    dr = h.drought(d, dates)
    assert dr["deepest_sum_d"] == pytest.approx(-0.2) and dr["deepest_date"] == str(dates[149].date())
    # 50 days falling, then 100 days that win back only half: 150 days below the earlier peak
    assert dr["longest_days"] == 150 and dr["below_peak_at_window_end"]
    assert dr["longest_start"] == str(dates[100].date())
    assert h.span_sum(d, dates, str(dates[100].date()), str(dates[149].date()))["sum_d"] == pytest.approx(-0.2)


def test_the_correlation_bootstrap_is_paired():
    rng = np.random.default_rng(7)
    a = rng.normal(size=400)
    same = h.paired_corr_boot(a, a.copy())
    assert same["corr"] == pytest.approx(1.0) and same["ci_low"] == pytest.approx(1.0)
    b = rng.normal(size=400)
    ind = h.paired_corr_boot(a, b)
    assert ind["ci_low"] < 0 < ind["ci_high"] and ind["n_iterations"] == h.N_ITER
    assert "note" in h.paired_corr_boot(a[:10], b[:10])     # too short for an interval: says so


def test_constant_series_gives_no_correlation_rather_than_a_number():
    assert h._corr(np.full(50, 0.001), np.arange(50.0)) is None      # [NN-FP-GUARDS]: tolerance, not == 0


def test_accumulation_adds_five_thousand_before_each_later_year():
    dates = pd.DatetimeIndex(["2010-12-30", "2010-12-31", "2011-01-03", "2011-01-04", "2012-01-03"])
    out = h.accumulation(np.array([0.0, 0.0, 0.10, 0.0, 0.0]), dates)
    assert out["contributed_dollars"] == 20000.0
    assert out["terminal_dollars"] == pytest.approx((10000.0 + 5000.0) * 1.10 + 5000.0)


# --------------------------------------------------------------------------- transport reading (§10)
@pytest.mark.parametrize("lo, hi, key", [(7.0, 9.0, "CLOSED"), (2.5, 6.0, "void"), (-1.0, 0.5, "survive"),
                                         (0.5, 5.0, "not pinned"), (-1.0, 1.5, "not pinned")])
def test_transport_reading_closes_on_h_alone_and_survives_only_with_the_haircut_added(lo, hi, key):
    r = h.transport_reading({"point": (lo + hi) / 200.0, "ci_low": lo / 100.0, "ci_high": hi / 100.0})
    assert key in r["reading"]


# --------------------------------------------------------------------------- S3 selection
def test_s3_takes_one_oldest_class_per_new_family_and_skips_held_and_levered_copies():
    ms = lambda d: int(pd.Timestamp(d).timestamp() * 1000)  # noqa: E731
    quotes = [
        {"symbol": "AQMIX", "longName": "AQR Managed Futures Strategy I", "netExpenseRatio": 3.09,
         "firstTradeDateMilliseconds": ms("2010-01-05")},
        {"symbol": "QMHIX", "longName": "AQR Managed Futures Strategy HV I", "netExpenseRatio": 3.3,
         "firstTradeDateMilliseconds": ms("2013-07-16")},
        {"symbol": "MFTFX", "longName": "Arrow Managed Futures Strategy A", "netExpenseRatio": 1.9,
         "firstTradeDateMilliseconds": ms("2010-06-01")},
        {"symbol": "MFTTX", "longName": "Arrow Managed Futures Strategy C", "netExpenseRatio": 2.6,
         "firstTradeDateMilliseconds": ms("2010-05-05")},
        {"symbol": "NEWIX", "longName": "New Trend Fund I", "netExpenseRatio": 1.0,
         "firstTradeDateMilliseconds": ms("2024-05-01")},
    ]
    sel = h.s3_selection(quotes, {"AQMIX": "AQR Managed Futures Strategy I"})
    assert list(sel["chosen"]) == ["MFTTX"]
    assert sel["chosen"]["MFTTX"]["er"] == pytest.approx(h.ER_CAP)       # 2.6 % capped at 2.00 %
    assert "rule (d)" in sel["skipped"]["AQR Managed Futures Strategy HV"]
    assert "rule (c)" in sel["skipped"]["New Trend Fund"]
    assert sel["skipped"]["AQR Managed Futures Strategy"] == "already in the decision composite"


# --------------------------------------------------------------------------- fail-closed refusals
def test_no_price_may_be_fetched_before_the_membership_table_is_frozen(monkeypatch):
    monkeypatch.setattr(h, "MEMBERSHIP_FROZEN", None)
    with pytest.raises(h.T398Halt, match="not frozen"):
        h.cmd_fetch()


def test_only_barclayhedge_hosts_may_be_read(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "BTOP_DIR", tmp_path / "btop50")
    with pytest.raises(h.T398Halt, match="no mirror"):
        h.cmd_btop50_get("https://example.com/btop50", "x")
    with pytest.raises(h.T398Halt, match="no mirror"):
        h.cmd_btop50_get("https://notbarclayhedge.com/", "x")
    assert not (tmp_path / "btop50").exists()               # refused before anything was written or sent


def test_run_refuses_without_a_passed_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "GATES", tmp_path / "gates.json")
    with pytest.raises(h.T398Halt, match="NOT EVALUABLE"):
        h.cmd_run("A")
    (tmp_path / "gates.json").write_text('{"evaluable": false}')
    with pytest.raises(h.T398Halt, match="NOT EVALUABLE"):
        h.cmd_run("A")


def test_a_price_row_inside_the_2026_holdout_halts(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "INPUTS", tmp_path)
    idx = pd.DatetimeIndex(["2025-12-30", "2025-12-31", "2026-01-02"], name="Date")
    pd.DataFrame({"adj_close": [1.0, 1.0, 1.0], "raw_close": [1.0, 1.0, 1.0]}, index=idx).to_csv(tmp_path / "yf_ZZZ.csv")
    with pytest.raises(h.T398Halt, match="2026 holdout"):
        h.load_px("ZZZ")


# =========================================================================== review round 1
# The tests below DRIVE the harness's own Panel, halts and bindings on a synthetic snapshot
# (tmp_path + monkeypatched paths). Each was proven by reversion: see the verdict's review section.
_RATE = 0.036          # a flat 3.6 %/yr financing base => cash accrual 1e-4 per calendar day
_FUND_ER = {"RYMFX": 0.0199, "AQMIX": 0.0125, "ASFYX": 0.0145, "WTMF": 0.0066}


class _FakeSub:
    """Stands in for b5.Substrate: the equity calendar, the leg returns and the benchmark, built the
    way the real loader builds them (T-311 buyhold_equity = equity return − 0.09 %/252)."""

    def __init__(self, cal: pd.DatetimeIndex, base: pd.Series, seed: int = 11) -> None:
        rng = np.random.default_rng(seed)
        self.px2 = pd.DataFrame({"equity": 100.0 * np.cumprod(1.0 + rng.normal(0.0004, 0.01, len(cal))),
                                 "bond": 100.0 * np.cumprod(1.0 + rng.normal(0.0001, 0.003, len(cal)))}, index=cal)
        self.base = base

    def window(self, start: str, end: str, gold: bool) -> dict:
        idx = self.px2.index
        wd = idx[(idx >= pd.Timestamp(start)) & (idx <= pd.Timestamp(end))]
        i0 = idx.get_loc(wd[0])
        dates = idx[i0 - 1: i0 + len(wd)]
        rets = self.px2.loc[dates].pct_change().iloc[1:]
        r, dcal = h.b5.financing_arrays(dates, self.base)
        return {"dates": wd, "base_date": dates[0], "e": rets["equity"].values, "b": rets["bond"].values,
                "r": r, "dcal": dcal, "bench": rets["equity"].values - h.ER_E / h.TD}


def _snapshot(tmp_path, monkeypatch, funds=("RYMFX", "AQMIX", "ASFYX"), short: dict | None = None):
    """A synthetic snapshot: each fund's total return is pnl + cash − its own fee, so the excess
    return the harness must recover is exactly pnl. Returns (panel, pnl_by_fund, cal)."""
    cal = pd.bdate_range("2010-06-01", "2011-12-30")
    base = pd.Series(_RATE, index=pd.bdate_range("2010-01-04", "2011-12-30"))
    dcal = np.concatenate([[1.0], (cal[1:] - cal[:-1]).days.values.astype(float)])
    cash = _RATE * dcal / 360.0
    monkeypatch.setattr(h, "INPUTS", tmp_path)
    pnl, files = {}, {}
    for k, tk in enumerate(funds):
        rng = np.random.default_rng(100 + k)
        p = rng.normal(0.0002 * (k + 1), 0.004, len(cal))
        tr = p + cash - _FUND_ER[tk] / h.TD
        level = pd.Series(10.0 * np.cumprod(1.0 + tr), index=cal)
        first = cal[5 + 3 * k]                               # first prices in early June 2010
        last = cal[-1] if not short or tk not in short else pd.Timestamp(short[tk])
        s = level.loc[first:last]
        df = pd.DataFrame({"adj_close": s, "raw_close": s})
        df.index.name = "Date"
        df.to_csv(tmp_path / f"yf_{tk}.csv", float_format="%.17g")
        files[f"yf_{tk}.csv"] = {"md5": h.b5.md5_file(tmp_path / f"yf_{tk}.csv")}
        pnl[tk] = pd.Series(p, index=cal)
    frozen = {tk: {"rule_b": True, "er": _FUND_ER.get(tk, 0.01), "er_source": "test"} for tk in h.CANDIDATES}
    monkeypatch.setattr(h, "MEMBERSHIP_FROZEN", frozen)
    panel = h.Panel(man={"files": files}, base=base, sub=_FakeSub(cal, base))
    return panel, pnl, cal


def test_panel_excess_is_the_funds_return_minus_cash_plus_its_own_fee(tmp_path, monkeypatch):
    panel, pnl, _ = _snapshot(tmp_path, monkeypatch)
    assert panel.members == ["RYMFX", "AQMIX", "ASFYX"]
    for tk in panel.members:
        x = panel.excess(tk)
        assert x.index[0] == pd.Timestamp("2010-07-01")       # the month after the month of its first price
        # cash subtracted ONCE and the fund's own fee added back ONCE: what is left is the futures P&L
        np.testing.assert_allclose(x.values, pnl[tk].reindex(x.index).values, atol=1e-12)
        net = panel.excess(tk, gross_up=False)
        np.testing.assert_allclose((x - net).values, _FUND_ER[tk] / h.TD, atol=1e-15)


def test_panel_composite_is_the_equal_weight_mean_and_counts_members(tmp_path, monkeypatch):
    panel, pnl, _ = _snapshot(tmp_path, monkeypatch)
    x, cnt = panel.composite()
    want = pd.DataFrame({tk: pnl[tk] for tk in panel.members}).mean(axis=1).reindex(x.index)
    np.testing.assert_allclose(x.values, want.values, atol=1e-12)
    assert int(cnt.min()) == 3 and int(cnt.max()) == 3
    x2, cnt2 = panel.composite(["RYMFX", "AQMIX"])
    np.testing.assert_allclose(x2.values, ((pnl["RYMFX"] + pnl["AQMIX"]) / 2.0).reindex(x2.index).values, atol=1e-12)
    assert int(cnt2.max()) == 2
    # an ER override moves only that fund, by the difference in fees over the member count
    x3, _ = panel.composite(er_override={"AQMIX": 0.0200})
    np.testing.assert_allclose((x3 - x).values, (0.0200 - 0.0125) / h.TD / 3.0, atol=1e-15)


def test_panel_window_feeds_the_arm_the_composite_and_matches_the_benchmark(tmp_path, monkeypatch):
    panel, pnl, _ = _snapshot(tmp_path, monkeypatch)
    x, cnt = panel.composite()
    w = panel.window(x, cnt, h.MIN_MEMBERS, end=pd.Timestamp("2011-12-30"))
    assert w["dates"][0] == pd.Timestamp("2010-07-01") and int(w["n_members"].min()) == 3
    np.testing.assert_allclose(w["x"], x.reindex(w["dates"]).values, atol=0.0)
    r = h.arm_returns(w, 1.0, s=0.0, h_surv=0.0)
    np.testing.assert_allclose(r - w["bench"], w["x"] - (h.ER_S - h.ER_E) / h.TD, atol=1e-15)


def test_window_halts_when_the_composite_drops_below_three_members(tmp_path, monkeypatch):
    panel, _, _ = _snapshot(tmp_path, monkeypatch, short={"ASFYX": "2011-06-30"})
    x, cnt = panel.composite()
    with pytest.raises(h.T398Halt, match="fewer than 3 members"):
        panel.window(x, cnt, h.MIN_MEMBERS, end=pd.Timestamp("2011-12-30"))
    # positive control: the same panel is fine up to the day the third fund ends
    w = panel.window(x, cnt, h.MIN_MEMBERS, end=pd.Timestamp("2011-06-30"))
    assert int(w["n_members"].min()) == 3


def test_window_halts_when_there_are_never_three_members(tmp_path, monkeypatch):
    panel, _, _ = _snapshot(tmp_path, monkeypatch, funds=("RYMFX", "AQMIX"))
    x, cnt = panel.composite()
    with pytest.raises(h.T398Halt, match="never has 3 members"):
        panel.window(x, cnt, h.MIN_MEMBERS, end=pd.Timestamp("2011-12-30"))


def _pinned_snapshot(tmp_path, monkeypatch):
    """A manifest + files that verify_snapshot accepts (the positive control for the md5 halts)."""
    inputs, sub = tmp_path / "inputs", tmp_path / "sub"
    inputs.mkdir()
    sub.mkdir()
    pinned = {}
    files = {}
    for name in ("frb_h15_all_sdmx.zip", "nyfed_sofr.csv", "aqr_tsmom_monthly_t296.xlsx", "yf_AAA.csv"):
        (inputs / name).write_text(f"content of {name}\n")
        files[name] = {"md5": h.b5.md5_file(inputs / name)}
        if not name.startswith("yf_"):
            pinned[name] = files[name]["md5"]
    for name in ("equity_tr_daily.csv", "bond_tr_daily.csv"):
        (sub / name).write_text(f"content of {name}\n")
        pinned[name] = h.b5.md5_file(sub / name)
    (inputs / "MANIFEST.json").write_text(__import__("json").dumps({"files": files}))
    monkeypatch.setattr(h, "INPUTS", inputs)
    monkeypatch.setattr(h, "MANIFEST", inputs / "MANIFEST.json")
    monkeypatch.setattr(h, "SUB", sub)
    monkeypatch.setattr(h, "PINNED_MD5", pinned)
    return inputs, sub


def test_verify_snapshot_passes_a_clean_snapshot_and_halts_on_any_changed_byte(tmp_path, monkeypatch):
    inputs, sub = _pinned_snapshot(tmp_path, monkeypatch)
    assert set(h.verify_snapshot()["files"]) >= {"yf_AAA.csv"}            # positive control
    (inputs / "yf_AAA.csv").write_text("a different price file\n")
    with pytest.raises(h.T398Halt, match="md5 != manifest"):
        h.verify_snapshot()


def test_verify_snapshot_halts_on_a_changed_substrate(tmp_path, monkeypatch):
    _, sub = _pinned_snapshot(tmp_path, monkeypatch)
    (sub / "equity_tr_daily.csv").write_text("rebuilt\n")
    with pytest.raises(h.T398Halt, match="re-verify required"):
        h.verify_snapshot()


def test_verify_snapshot_halts_when_a_pinned_input_no_longer_matches_the_prereg(tmp_path, monkeypatch):
    _pinned_snapshot(tmp_path, monkeypatch)
    pinned = dict(h.PINNED_MD5)
    pinned["nyfed_sofr.csv"] = "0" * 32                                   # the prereg's md5 no longer matches
    monkeypatch.setattr(h, "PINNED_MD5", pinned)
    with pytest.raises(h.T398Halt, match="md5 != prereg"):
        h.verify_snapshot()


def test_fp_guard_uses_tolerance_on_a_tiny_but_nonzero_std():
    """[NN-FP-GUARDS]: a std of ~1e-17 is NOT zero, so a bare `== 0` guard would let it through and
    return a meaningless correlation. The guard must use tolerance."""
    a = np.full(60, 0.1)
    a[0] = np.nextafter(0.1, 1.0)
    sd = float(np.std(a, ddof=1))
    assert 0.0 < sd < 1e-12                                 # tiny, and genuinely non-zero
    b = np.random.default_rng(5).normal(size=60)
    assert h._corr(a, b) is None and h._corr(b, a) is None
    assert h._ann_ratio(a - 0.1, h.TD) == 0.0
    assert h._corr(b, b) == pytest.approx(1.0)               # positive control


def _bound_files(tmp_path, monkeypatch, unruled: int = 0):
    """manifest + rulings + integrity.json + gates.json, each bound to the ones before it."""
    import json
    man, rul = tmp_path / "MANIFEST.json", tmp_path / "integrity_rulings.json"
    integ, gates = tmp_path / "integrity.json", tmp_path / "gates.json"
    man.write_text('{"files": {}}')
    rul.write_text("{}")
    for name, path in (("MANIFEST", man), ("RULINGS", rul), ("INTEGRITY", integ), ("GATES", gates)):
        monkeypatch.setattr(h, name, path)
    integ.write_text(json.dumps({"unruled_candidate_flags": unruled, "candidates": {}, "anchors": {},
                                 "bound_to": {"manifest_md5": h.b5.md5_file(man), "rulings_md5": h.b5.md5_file(rul)}}))
    gates.write_text(json.dumps({"evaluable": True, "bound_to": {"manifest_md5": h.b5.md5_file(man),
                                                                 "integrity_md5": h.b5.md5_file(integ)}}))
    return man, rul, integ, gates


def test_bindings_pass_when_consistent_and_halt_on_each_stale_file(tmp_path, monkeypatch):
    import json
    man, rul, integ, gates = _bound_files(tmp_path, monkeypatch)
    h.check_bindings(json.loads(gates.read_text()), json.loads(integ.read_text()))        # positive control
    g, i = json.loads(gates.read_text()), json.loads(integ.read_text())
    man.write_text('{"files": {"re-pinned": 1}}')                         # the manifest changed under them
    with pytest.raises(h.T398Halt, match="integrity.json was not computed against this snapshot manifest"):
        h.check_bindings(g, i)
    man.write_text('{"files": {}}')
    rul.write_text('{"a new ruling": 1}')
    with pytest.raises(h.T398Halt, match="rulings file"):
        h.check_bindings(g, i)
    rul.write_text("{}")
    integ.write_text(json.dumps({**i, "extra": 1}))                       # integrity re-run after the gates
    with pytest.raises(h.T398Halt, match="gates.json was not computed against this integrity file"):
        h.check_bindings(g, i)
    with pytest.raises(h.T398Halt, match="missing"):
        h.check_bindings(None, i)
    with pytest.raises(h.T398Halt, match="snapshot manifest"):
        h.check_bindings(g, {"unruled_candidate_flags": 0})               # an unbound (old-format) file


def test_run_refuses_an_unruled_flag_and_stale_gate_files(tmp_path, monkeypatch):
    _bound_files(tmp_path, monkeypatch, unruled=2)
    with pytest.raises(h.T398Halt, match="no recorded ruling"):
        h.cmd_run("A")
    man, _, _, _ = _bound_files(tmp_path, monkeypatch, unruled=0)
    man.write_text('{"files": {"re-pinned": 1}}')                         # gates/integrity now stale
    with pytest.raises(h.T398Halt, match="stale"):
        h.cmd_run("A")


def test_determinism_command_exits_nonzero_on_a_mismatch_or_a_missing_run(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "OUT", tmp_path)
    monkeypatch.setattr(h, "DETERMINISM", tmp_path / "determinism.json")
    assert h.cmd_determinism() == 2                                       # no runs at all
    for tag in ("A", "B"):
        (tmp_path / f"run_{tag}").mkdir()
        (tmp_path / f"run_{tag}" / "results.json").write_text('{"x": 1}')
        (tmp_path / f"run_{tag}" / "returns.csv").write_text("a,b\n1,2\n")
    assert h.cmd_determinism() == 0 and h.compare_runs(tmp_path / "run_A", tmp_path / "run_B")["identical"]
    (tmp_path / "run_B" / "results.json").write_text('{"x": 2}')
    out = h.compare_runs(tmp_path / "run_A", tmp_path / "run_B")
    assert out["mismatch"] == ["results.json"] and not out["identical"]
    assert h.cmd_determinism() == 2
    (tmp_path / "run_B" / "results.json").write_text('{"x": 1}')
    (tmp_path / "run_B" / "extra.csv").write_text("only in B\n")
    assert h.cmd_determinism() == 2                                       # a file present in one run only


def test_ratio_ci_brackets_the_point_and_is_the_metrics_engines_bootstrap():
    rng = np.random.default_rng(9)
    x = rng.normal(0.0002, 0.01, 1500)
    out = h.ratio_ci(x, h.TD, h.BLOCK_DAILY)
    assert out["point"] == pytest.approx(h._ann_ratio(x, h.TD))
    assert out["ci_low"] < out["point"] < out["ci_high"]
    assert out["block_length"] == h.BLOCK_DAILY and out["n_iterations"] == h.N_ITER


def test_since_start_frame_differs_from_the_peak_relative_frame():
    """The review's MAJOR-1: 'behind its own earlier high' is not 'behind since the start'."""
    d = np.concatenate([np.full(100, 0.002), np.full(50, -0.002), np.full(50, 0.0)])   # +20 %, then −10 %
    dates = _cal(200, "2011-01-03")
    ss = h.since_start_frame(d, dates, [str(dates[99].date()), str(dates[-1].date())])
    assert ss["share_of_days_behind"] == 0.0                              # never behind since the start
    assert ss["at"][str(dates[-1].date())]["relative_wealth_pct"] == pytest.approx(np.expm1(0.1) * 100)
    dr = h.drought(d, dates)
    assert dr["longest_days"] == 100 and dr["below_peak_at_window_end"]   # yet below its own high for 100 days
    assert h.share_behind(d, dates, str(dates[100].date()), str(dates[-1].date()))[
        "share_of_days_behind_since_start"] == 0.0
