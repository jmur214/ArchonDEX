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
