# tests/test_crisis_replay_t143.py
"""T-143 — fixture tests for the T-118b crisis-replay harness.

Every scenario is SYNTHETIC with the right answer known by construction
(T-143 hard constraint: zero contact with real campaign artifacts):

  * HELPS    — overlay halves episode losses, zero calm drag → PASS.
  * BLEEDS   — heavy calm drag, no episode benefit → FAIL.
  * V1-HOLE  — MaxDD improves in every episode (v1 (i)-(iv) all pass)
               but the overlay bleeds the in-window recoveries so the
               window returns and terminal wealth are NET NEGATIVE.
               Under v1 this PASSED; under the addendum v2 it must
               FAIL. This is the key regression proving v2 bites.
  * PARTIAL  — (i)+(iii)+v2 hold, only the trigger-tunable shape
               criteria ((ii) sign test) fail → PARTIAL.

Plus mechanical-derivation unit tests (both rules), month-pinning
tests, determinism, and the primary-config multiplicity rule.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.crisis_replay_t118b import (
    ACTIONABLE_IDS,
    Episode,
    check_mechanical_derivation,
    derive_episodes_mechanical,
    evaluate_crisis_replay,
    format_report,
    pin_locked_episodes,
)

# ----------------------------------------------------------------------
# Synthetic fixture machinery
# ----------------------------------------------------------------------
CAL = pd.bdate_range("2006-01-02", "2024-12-31")

# Locked-id episode windows on the synthetic calendar (dates mirror the
# locked months; exact days are arbitrary within them — fixtures define
# their own windows, the evaluator only consumes Episode objects).
_EP_SPECS = [
    ("gfc",    "2007-10-09", "2009-03-09", False, False),
    ("us2011", "2011-04-29", "2011-10-03", False, False),
    ("q42018", "2018-09-20", "2018-12-24", False, False),
    ("covid",  "2020-02-19", "2020-03-23", True,  False),
    ("y2022",  "2022-01-03", "2022-10-12", True,  False),
]


def _mk_episodes() -> list[Episode]:
    eps = []
    for eid, peak, trough, oos, blind in _EP_SPECS:
        peak_ts = CAL[CAL.searchsorted(pd.Timestamp(peak))]
        trough_ts = CAL[CAL.searchsorted(pd.Timestamp(trough))]
        end_ts = CAL[min(CAL.searchsorted(trough_ts) + 20, len(CAL) - 1)]
        eps.append(Episode(
            episode_id=eid, label=eid, peak=peak_ts, trough=trough_ts,
            end=end_ts, actionable=True, oos=oos, blind=blind, max_dd=-0.2,
        ))
    return eps


EPISODES = _mk_episodes()


def _build_artifacts(
    calm_daily: float,
    decline_daily: float,
    recovery_daily: float,
    degross_in_episode: bool,
    per_episode_overrides: dict | None = None,
) -> pd.DataFrame:
    """Deterministic per-bar artifact frame from phase-wise daily returns.

    per_episode_overrides: {episode_id: (decline_daily, recovery_daily)}
    """
    overrides = per_episode_overrides or {}
    rets = np.full(len(CAL), calm_daily)
    gross = np.ones(len(CAL))
    for ep in EPISODES:
        dec, rec = overrides.get(ep.episode_id, (decline_daily, recovery_daily))
        decline_mask = (CAL >= ep.peak) & (CAL <= ep.trough)
        recovery_mask = (CAL > ep.trough) & (CAL <= ep.end)
        rets[decline_mask] = dec
        rets[recovery_mask] = rec
        if degross_in_episode:
            gross[decline_mask | recovery_mask] = 0.5
    equity = 100_000.0 * np.cumprod(1.0 + rets)
    return pd.DataFrame(
        {"equity": equity, "gross_notional": gross}, index=CAL
    )


def _result(on, off, primary=True, label="primary"):
    return evaluate_crisis_replay(
        on, off, EPISODES, config_label=label, is_primary_config=primary
    )


def _crit(result, key):
    return next(c for c in result.criteria if c.key == key)


# Baseline OFF arm shared by scenarios: +4bp calm, −60bp declines,
# strong +300bp/day V-recoveries (the sharp rebound is what makes the
# v1-hole constructible: an overlay can hold its MaxDD margin while
# forgoing the recovery), fully grossed.
OFF = _build_artifacts(0.0004, -0.0060, 0.0300, degross_in_episode=False)


# ----------------------------------------------------------------------
# Scenario: overlay obviously HELPS → PASS
# ----------------------------------------------------------------------
class TestScenarioHelps:
    ON = _build_artifacts(0.0004, -0.0030, 0.0300, degross_in_episode=True)

    def test_verdict_pass_all_criteria(self):
        res = _result(self.ON, OFF)
        assert res.verdict == "PASS"
        assert all(c.passed for c in res.criteria), [
            (c.key, c.value) for c in res.criteria if not c.passed
        ]

    def test_every_episode_improves_and_degross_detected(self):
        res = _result(self.ON, OFF)
        for r in res.episode_results:
            assert r.d_maxdd_pp > 0.5
            assert r.days_to_degross is not None
        assert res.splits["oos"]["n"] == 2
        assert res.splits["in_sample"]["n"] == 3

    def test_calm_drag_zero(self):
        res = _result(self.ON, OFF)
        assert abs(res.calm["cagr_diff_bps"]) < 1.0  # identical calm days

    def test_verdict_line_shows_every_gating_criterion(self):
        res = _result(self.ON, OFF)
        line = res.verdict_line()
        assert "VERDICT: PASS" in line
        for c in res.criteria:
            assert c.key in line


# ----------------------------------------------------------------------
# Scenario: overlay obviously BLEEDS → FAIL
# ----------------------------------------------------------------------
class TestScenarioBleeds:
    ON = _build_artifacts(-0.0003, -0.0060, 0.0300, degross_in_episode=True)

    def test_verdict_fail(self):
        res = _result(self.ON, OFF)
        assert res.verdict == "FAIL"

    def test_calm_drag_criteria_fail(self):
        res = _result(self.ON, OFF)
        assert not _crit(res, "calm_drag_bps").passed
        assert not _crit(res, "calm_drag_ci90_low_bps").passed
        # ~ -17bp/day gap → far below the -40bps floor
        assert res.calm["cagr_diff_bps"] < -100.0

    def test_no_episode_benefit(self):
        res = _result(self.ON, OFF)
        assert not _crit(res, "median_dmaxdd_pp").passed
        assert not _crit(res, "gfc_floor_pp").passed


# ----------------------------------------------------------------------
# Scenario: the V1 HOLE — MaxDD passes, returns net-negative → must FAIL
# ----------------------------------------------------------------------
class TestScenarioV1Hole:
    # Declines only SLIGHTLY shallower (−48bp vs −60bp/day → ΔMaxDD
    # margins of ~+1 to +8pp, GFC ≈ +6pp) and the overlay then sits OUT
    # the entire +300bp/day V-recovery, bleeding −10bp/day instead. The
    # gentle tail bleed never breaches the OFF trough, so every v1
    # criterion (median/sign/calm/single-episode) PASSES — but the
    # overlay forgoes every recovery, so window returns and terminal
    # wealth are NET NEGATIVE. Under v1 this PASSED; v2 must FAIL it.
    # Calm days identical → v1 calm-drag criterion is clean.
    ON = _build_artifacts(0.0004, -0.0048, -0.0010, degross_in_episode=True)

    def test_v1_criteria_all_pass(self):
        res = _result(self.ON, OFF)
        for key in ("median_dmaxdd_pp", "sign_test",
                    "calm_drag_bps", "calm_drag_ci90_low_bps",
                    "single_episode_share"):
            assert _crit(res, key).passed, key

    def test_v2_return_units_criteria_fail(self):
        res = _result(self.ON, OFF)
        assert not _crit(res, "terminal_wealth").passed
        assert not _crit(res, "benefit_drag_ratio").passed

    def test_verdict_fail_not_partial(self):
        # Under v1 this configuration PASSED (all four v1 criteria
        # green). The addendum's return-units criteria must force FAIL —
        # and explicitly NOT the trigger-iteration PARTIAL verdict.
        res = _result(self.ON, OFF)
        assert res.verdict == "FAIL"


# ----------------------------------------------------------------------
# Scenario: PARTIAL — only trigger-tunable criteria fail
# ----------------------------------------------------------------------
class TestScenarioPartial:
    # GFC + both OOS episodes improve strongly; the two other in-sample
    # episodes are left untreated (≈0 ΔMaxDD) → sign test 3/5 fails, but
    # median (8pp-ish), calm, and every v2 criterion hold → PARTIAL.
    ON = _build_artifacts(
        0.0004, -0.0060, 0.0300, degross_in_episode=True,
        per_episode_overrides={
            "gfc": (-0.0030, 0.0300),
            "covid": (-0.0030, 0.0300),
            "y2022": (-0.0030, 0.0300),
        },
    )

    def test_verdict_partial(self):
        res = _result(self.ON, OFF)
        assert not _crit(res, "sign_test").passed
        assert _crit(res, "median_dmaxdd_pp").passed
        assert _crit(res, "terminal_wealth").passed
        assert _crit(res, "oos_both_improve").passed
        assert res.verdict == "PARTIAL"


# ----------------------------------------------------------------------
# Primary-config multiplicity rule (addendum v2 §4)
# ----------------------------------------------------------------------
class TestPrimaryConfigGating:
    def test_sensitivity_config_gets_no_gate(self):
        on = _build_artifacts(0.0004, -0.0030, 0.0300, degross_in_episode=True)
        res = _result(on, OFF, primary=False, label="0.7x_k3")
        assert res.verdict == "SENSITIVITY"
        assert any("multiplicity" in n for n in res.notes)
        # metrics still reported
        assert len(res.episode_results) == 5


# ----------------------------------------------------------------------
# Mechanical derivation + month-pinning units
# ----------------------------------------------------------------------
def _synthetic_index_with_dips() -> pd.Series:
    """Grow +5bp/day; one −20% dip (2010), one −13% dip (2014, must NOT
    qualify), one −16% dip (2018). Full recovery between dips."""
    cal = pd.bdate_range("2008-01-02", "2020-12-31")
    rets = np.full(len(cal), 0.0005)

    def carve(start, days_down, dd_total):
        pos = cal.searchsorted(pd.Timestamp(start))
        daily = 1.0 - (1.0 - dd_total) ** (1.0 / days_down)
        rets[pos:pos + days_down] = -daily

    carve("2010-04-01", 60, 0.20)
    carve("2014-06-02", 40, 0.13)
    carve("2018-09-04", 50, 0.16)
    return pd.Series(100.0 * np.cumprod(1.0 + rets), index=cal)


class TestMechanicalDerivation:
    @pytest.mark.parametrize("rule", ["alltime_high", "local_peak"])
    def test_finds_exactly_the_qualifying_dips(self, rule):
        tr = _synthetic_index_with_dips()
        eps = derive_episodes_mechanical(tr, rule=rule)
        assert len(eps) == 2, [(str(e["peak"].date()), e["max_dd"]) for e in eps]
        assert str(eps[0]["peak"].date()).startswith("2010-0")
        assert str(eps[1]["peak"].date()).startswith("2018-0")
        for e in eps:
            assert e["max_dd"] <= -0.15

    @pytest.mark.parametrize("rule", ["alltime_high", "local_peak"])
    def test_open_drawdown_at_end_of_data_is_emitted(self, rule):
        cal = pd.bdate_range("2020-01-02", "2021-06-30")
        rets = np.full(len(cal), 0.0004)
        rets[-90:] = -0.0030  # in-progress ~-23% slide, never recovers
        tr = pd.Series(100.0 * np.cumprod(1.0 + rets), index=cal)
        eps = derive_episodes_mechanical(tr, rule=rule)
        assert len(eps) == 1
        assert eps[0]["trough"] == cal[-1]

    def test_window_extension_is_20_trading_days(self):
        tr = _synthetic_index_with_dips()
        eps = derive_episodes_mechanical(tr, rule="alltime_high")
        idx = tr.index
        for e in eps:
            assert idx.get_loc(e["end"]) - idx.get_loc(e["trough"]) == 20


class TestMonthPinning:
    def test_pins_all_locked_episodes_on_covering_series(self):
        cal = pd.bdate_range("1999-01-04", "2024-12-31")
        rng = np.random.default_rng(0)
        tr = pd.Series(
            100.0 * np.cumprod(1.0 + rng.normal(0.0003, 0.01, len(cal))),
            index=cal,
        )
        eps, uncov = pin_locked_episodes(tr)
        assert uncov == []
        assert [e.episode_id for e in eps] == [
            "dotcom", "gfc", "us2011", "q42018", "covid", "y2022"
        ]
        for e in eps:
            # peak day = month max; trough day = month min — mechanical.
            pm = tr.loc[tr.index.strftime("%Y-%m") == e.peak.strftime("%Y-%m")]
            tm = tr.loc[tr.index.strftime("%Y-%m") == e.trough.strftime("%Y-%m")]
            assert e.peak == pm.idxmax() and e.trough == tm.idxmin()

    def test_dotcom_uncoverable_on_2005_start_series(self):
        cal = pd.bdate_range("2005-02-25", "2024-12-31")
        tr = pd.Series(np.linspace(100, 300, len(cal)), index=cal)
        eps, uncov = pin_locked_episodes(tr)
        assert uncov == ["dotcom"]
        assert len(eps) == 5

    def test_actionable_set_is_the_locked_five(self):
        assert ACTIONABLE_IDS == ["gfc", "us2011", "q42018", "covid", "y2022"]


class TestDerivationCheckReportsDivergence:
    def test_extra_episode_is_reported_never_patched(self):
        # A series whose only ≥15% event is OUTSIDE the locked months →
        # the check must list every locked id as missing and the event
        # as an extra (the STOP-report pathway the brief mandates).
        cal = pd.bdate_range("2012-01-02", "2014-12-31")
        rets = np.full(len(cal), 0.0005)
        pos = cal.searchsorted(pd.Timestamp("2013-05-01"))
        rets[pos:pos + 50] = -0.004
        tr = pd.Series(100.0 * np.cumprod(1.0 + rets), index=cal)
        chk = check_mechanical_derivation(tr, rule="alltime_high")
        assert chk["matched"] == []
        assert len(chk["extras"]) == 1
        assert len(chk["missing"]) == 6


# ----------------------------------------------------------------------
# Determinism + report formatting
# ----------------------------------------------------------------------
class TestDeterminismAndReport:
    def test_repeat_evaluation_identical(self):
        on = _build_artifacts(0.0004, -0.0030, 0.0300, degross_in_episode=True)
        r1, r2 = _result(on, OFF), _result(on, OFF)
        assert r1.verdict == r2.verdict
        for c1, c2 in zip(r1.criteria, r2.criteria):
            assert (c1.key, str(c1.value), c1.passed) == (c2.key, str(c2.value), c2.passed)
        assert r1.calm == r2.calm
        assert r1.bayes_cri_90 == r2.bayes_cri_90

    def test_format_report_contains_all_sections(self):
        on = _build_artifacts(0.0004, -0.0030, 0.0300, degross_in_episode=True)
        report = format_report(_result(on, OFF))
        for token in ("VERDICT", "splits:", "calm:", "bayes 90% CrI",
                      "criterion", "gfc", "covid"):
            assert token in report, token
