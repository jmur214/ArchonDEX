"""tests/test_build_signal_panel_b1.py — the B-1 panel builder's design laws.

Every law here was written into the FROZEN prereg §11.1 before the builder existed; these
tests drive the real functions (and, for the env guard, the real entrypoint in a
subprocess) — not text assertions about them.
"""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import build_signal_panel_b1 as b1

ROOT = Path(__file__).resolve().parents[1]
PINS = dict(b1.ENV_PINS)


def _prices(n=300, seed=0, start="2023-01-02"):
    idx = pd.bdate_range(start, periods=n)
    rng = np.random.RandomState(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    return pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close,
                         "Volume": 1e6}, index=idx)


# ------------------------------------------------------------------ env pins (step 1)
def test_wrong_env_pins_are_REFUSED_by_the_real_entrypoint_never_re_execd():
    env = {**os.environ, **PINS, "OMP_NUM_THREADS": "4"}
    r = subprocess.run([sys.executable, "-m", "scripts.build_signal_panel_b1",
                        "--start", "2024-01", "--end", "2024-01", "--out", "/nonexistent"],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 3, r.stderr
    assert "REFUSING" in r.stderr and "Never re-exec" in r.stderr
    assert "OMP_NUM_THREADS='4'" in r.stderr


def test_env_pin_violations_names_each_wrong_pin():
    assert b1.env_pin_violations(PINS) == []
    bad = b1.env_pin_violations({**PINS, "PYTHONHASHSEED": "1", "MKL_NUM_THREADS": None})
    assert len(bad) == 2 and any("PYTHONHASHSEED" in x for x in bad)


# ------------------------------------------------------------------ calendar + PIT
def test_month_ends_are_the_last_TRADING_day_of_each_month():
    idx = pd.bdate_range("2024-01-01", "2024-03-31")
    me = b1.month_ends(idx, "2024-01", "2024-03")
    assert [str(m.date()) for m in me] == ["2024-01-31", "2024-02-29", "2024-03-29"]


def test_pit_slice_is_the_only_door_and_no_signal_can_see_the_future():
    """Several edges read iloc[-1] and assume their input already ends at as-of.
    Perturb every price AFTER as-of: a consumer of the pit map must not move."""
    px = _prices()
    as_of = px.index[200]
    future = px.copy()
    future.loc[future.index > as_of, "Close"] *= 50.0

    class LastCloseEdge:            # the iloc[-1] shape real edges use
        def compute_signals(self, data_map, now):
            return {t: float(df["Close"].iloc[-1]) for t, df in data_map.items()}

    a = b1.edge_values({"e": LastCloseEdge()}, b1.pit_slice({"X": px}, as_of), as_of)
    b = b1.edge_values({"e": LastCloseEdge()}, b1.pit_slice({"X": future}, as_of), as_of)
    assert a == b
    assert b1.pit_slice({"X": px}, as_of)["X"].index.max() == as_of


# ------------------------------------------------------------------ forward returns
def test_forward_return_full_and_the_delisting_proxy():
    px = _prices(n=60, start="2024-01-01")
    me, nxt = pd.Timestamp("2024-01-31"), pd.Timestamp("2024-02-29")
    r, how = b1.forward_return(px, me, nxt)
    assert how == "full" and r == pytest.approx(px.loc[nxt, "Close"] / px.loc[me, "Close"] - 1)
    delisted = px.loc[:"2024-02-15"]          # file ends mid-month: exit at the LAST price
    r2, how2 = b1.forward_return(delisted, me, nxt)
    assert how2 == "last_price_proxy"
    assert r2 == pytest.approx(delisted["Close"].iloc[-1] / px.loc[me, "Close"] - 1)
    assert b1.forward_return(px.loc[:"2024-01-31"], me, nxt)[1] == "no_price_after"
    assert b1.forward_return(None, me, nxt)[1] == "no_file"


# ------------------------------------------------------------------ the census (§3.4 et al.)
def test_three_spellings_of_missing_are_all_unusable():
    assert not b1.month_usable(np.array([np.nan] * 50))              # None/NaN
    assert not b1.month_usable(np.zeros(50))                         # the constant-0.0 fallback
    assert not b1.month_usable(np.array([1.0, 2.0, np.nan]))         # too few names
    assert b1.month_usable(np.random.RandomState(0).normal(size=50))


def _synthetic_panel(months, n=60, seed=0, overrides=None):
    rng = np.random.RandomState(seed)
    frames = []
    for m in months:
        names = [f"T{i:03d}" for i in range(n)]
        d = {s: rng.normal(size=n) for s in b1.SIGNALS}
        for s, fn in (overrides or {}).items():
            d[s] = fn(m, n, rng)
        f = pd.DataFrame(d, index=names)
        f.index = pd.MultiIndex.from_product([[m], names], names=["month_end", "ticker"])
        frames.append(f)
    return pd.concat(frames)


MONTHS = list(pd.date_range("2019-01-31", "2024-12-31", freq="ME"))


def test_a_clean_panel_passes_the_census():
    cen, halts = b1.build_census(_synthetic_panel(MONTHS), [], b1.SIGNALS, b1.FAMILY)
    assert halts == [], halts
    assert cen["family_counts"] == {"main": 14, "sensitivity": 5, "short_window": 6}


def test_the_earnings_proximity_shape_HALTS_constant_zero_not_nan():
    """Constant 0.0 for every name in most months — invisible to a NaN-only census."""
    ov = {"mom_12_1": lambda m, n, rng: np.zeros(n) if m.year < 2023 else rng.normal(size=n)}
    _, halts = b1.build_census(_synthetic_panel(MONTHS, overrides=ov), [], b1.SIGNALS, b1.FAMILY)
    assert any(h.startswith("mom_12_1") for h in halts), halts


def test_a_market_wide_signal_in_the_panel_HALTS():
    """Same value for every ticker on a date — the 17 features excluded in §3.1."""
    ov = {"skew_60d": lambda m, n, rng: np.full(n, rng.normal())}
    _, halts = b1.build_census(_synthetic_panel(MONTHS, overrides=ov), [], b1.SIGNALS, b1.FAMILY)
    assert any("skew_60d" in h and "NOT-CROSS-SECTIONAL" in h for h in halts), halts


def test_short_window_signals_are_judged_on_their_window_only():
    """A SimFin edge is constant before 2020-04 (no fundamentals panel); that must NOT halt."""
    ov = {"value_book_to_market_v1": lambda m, n, rng:
          np.zeros(n) if m < pd.Timestamp("2020-04-01") else rng.normal(size=n)}
    _, halts = b1.build_census(_synthetic_panel(MONTHS, overrides=ov), [], b1.SIGNALS, b1.FAMILY)
    assert not any("value_book_to_market_v1" in h for h in halts), halts


def test_a_selection_edge_is_flagged_SPARSE_not_halted():
    ov = {"momentum_12_1_v1": lambda m, n, rng: (rng.rand(n) < 0.15).astype(float)}
    cen, halts = b1.build_census(_synthetic_panel(MONTHS, overrides=ov), [], b1.SIGNALS, b1.FAMILY)
    assert cen["signals"]["momentum_12_1_v1"]["sparse"] is True
    assert not any("momentum_12_1_v1" in h for h in halts)


# ------------------------------------------------- the 2026-10-14 inventory amendment
def test_signals_excluded_by_ruling_are_never_computed():
    """herding_v1 and earnings_proximity_5d join pair_zscore_60d: structurally ineligible
    for a month-end construction — not in the inventory at all, so never ranked."""
    for s in ("herding_v1", "earnings_proximity_5d", "pair_zscore_60d"):
        assert s not in b1.SIGNALS and s in b1.EXCLUDED_BY_RULING


def test_volume_anomaly_tripping_the_bar_is_AUTO_EXCLUDED_and_recorded_not_halted():
    """The pre-ruling: tripping 10% applies the same exclusion automatically — no decision
    is made after seeing anything — and the family count accepts the reduced main family."""
    ov = {"volume_anomaly_v1": lambda m, n, rng: np.zeros(n) if m.month % 3 else rng.normal(size=n)}
    cen, halts = b1.build_census(_synthetic_panel(MONTHS, overrides=ov), [], b1.SIGNALS, b1.FAMILY)
    assert halts == [], halts
    assert "volume_anomaly_v1" in cen["auto_excluded_pre_ruled"]
    assert cen["family_counts"]["main"] == 13


def test_a_NON_pre_ruled_signal_tripping_the_bar_still_HALTS():
    """The pre-ruling covers volume_anomaly_v1 only — it is not a general escape hatch."""
    ov = {"overnight_intraday_v1": lambda m, n, rng: np.zeros(n) if m.month % 3 else rng.normal(size=n)}
    _, halts = b1.build_census(_synthetic_panel(MONTHS, overrides=ov), [], b1.SIGNALS, b1.FAMILY)
    assert any(h.startswith("overnight_intraday_v1") for h in halts), halts


def test_family_count_drift_HALTS():
    fam = dict(b1.FAMILY); fam["mom_12_1"] = "sensitivity"
    _, halts = b1.build_census(_synthetic_panel(MONTHS), [], b1.SIGNALS, fam)
    assert any("family counts" in h for h in halts)


# ------------------------------------------------------------------ orientation (§2.2)
def test_orientation_check_passes_a_correct_edge_and_HALTS_an_inverted_one():
    rng = np.random.RandomState(1)
    ref = rng.normal(size=600)
    good = (ref > np.quantile(ref, 0.8)).astype(float)          # longs HIGH momentum
    bad = (ref < np.quantile(ref, 0.2)).astype(float)           # longs LOW momentum
    panel = pd.DataFrame({"mom_12_1": ref, "momentum_12_1_v1": good})
    assert b1.orientation_check(panel, {"momentum_12_1_v1": ("mom_12_1", +1)})["momentum_12_1_v1"]["ok"]
    panel["momentum_12_1_v1"] = bad
    o = b1.orientation_check(panel, {"momentum_12_1_v1": ("mom_12_1", +1)})
    assert o["momentum_12_1_v1"]["ok"] is False
    _, halts = b1.build_census(_synthetic_panel(MONTHS), [], b1.SIGNALS, b1.FAMILY, orientation=o)
    assert any("never flipped" in h for h in halts)


# ------------------------------------------------------------------ guards
def test_disk_floor_REFUSES_below_5gb(monkeypatch, tmp_path):
    monkeypatch.setattr(b1, "disk_free_gb", lambda p: 4.99)
    with pytest.raises(SystemExit) as e:
        b1.assert_disk_floor(tmp_path)
    assert e.value.code == 4


def test_provenance_flags_code_from_another_tree():
    assert b1.provenance_violations({"self": str(ROOT / "scripts" / "x.py")}) == []
    assert b1.provenance_violations({"m": "/Users/someone/other_tree/core/x.py"})


def test_main_REFUSES_outside_the_worktree_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert b1.main(["--start", "2024-01", "--end", "2024-01", "--out", str(tmp_path)]) == 5


def test_canonical_md5_is_order_independent_and_value_sensitive():
    p = _synthetic_panel(MONTHS[:3], n=12)
    assert b1.canonical_md5(p) == b1.canonical_md5(p.sample(frac=1.0, random_state=3))
    q = p.copy(); q.iloc[0, 0] += 1e-6
    assert b1.canonical_md5(p) != b1.canonical_md5(q)


def test_the_pre_ruling_also_covers_the_HERDING_shape_over_half_unusable():
    """> 50% unusable fails the classification check first — the pre-ruling must still apply
    (caught by the test above in the first implementation, which halted instead)."""
    ov = {"volume_anomaly_v1": lambda m, n, rng: np.zeros(n) if m.month % 4 else rng.normal(size=n)}
    cen, halts = b1.build_census(_synthetic_panel(MONTHS, overrides=ov), [], b1.SIGNALS, b1.FAMILY)
    assert halts == [] and "volume_anomaly_v1" in cen["auto_excluded_pre_ruled"]
    assert "NOT-CROSS-SECTIONAL" in cen["auto_excluded_pre_ruled"]["volume_anomaly_v1"]
