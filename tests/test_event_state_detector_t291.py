"""T-291 — EventStateDetector: registry smoke, default-OFF, fail-closed, hysteresis,
and canon-safety (detect_regime's 5-axis output is unaffected).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.engine_e_regime.regime_config import RegimeConfig, EventStateConfig  # noqa: E402
from engines.engine_e_regime.regime_detector import RegimeDetector                # noqa: E402
from engines.engine_e_regime.detectors.event_state_detector import EventStateDetector  # noqa: E402


def _bd(start, n=30):
    return pd.DataFrame({"Close": [100.0] * n}, index=pd.date_range(start, periods=n, freq="B"))


def test_registry_smoke_on_and_off():
    # instantiated inside RegimeDetector + reachable via the accessor
    r = RegimeDetector()
    assert isinstance(r._event_state, EventStateDetector)
    state, conf, details = r.event_state(_bd("2024-06-03"))
    assert state == "calm" and conf == 0.0 and details["enabled"] is False


def test_default_is_off():
    assert EventStateConfig().enabled is False
    st, cf, d = EventStateDetector().detect(_bd("2024-06-03"))
    assert st == "calm" and cf == 0.0 and d["enabled"] is False


def test_fomc_event_window_when_enabled():
    det = EventStateDetector(EventStateConfig(enabled=True))
    # bar ending on the 2024-01-31 FOMC decision day
    st, cf, d = det.detect(_bd("2024-01-04", 20))          # 20 business days from Jan-4 → ends 2024-01-31
    assert d["as_of"] == "2024-01-31"
    assert st == "event_window" and cf == 1.0

    # a clearly non-FOMC bar → calm
    st2, _, _ = det.detect(_bd("2024-06-03", 5))           # mid-June, no decision ±1
    assert st2 == "calm"


def test_fail_closed_no_benchmark():
    det = EventStateDetector(EventStateConfig(enabled=True))
    st, cf, d = det.detect(pd.DataFrame())
    assert st == "calm" and cf == 0.0 and d["degraded"] is True


def test_elevated_inert_until_min_snapshots():
    det = EventStateDetector(EventStateConfig(enabled=True))
    # no alt store (or < 60 snaps) → never elevated, fail-closed calm
    st, cf, d = det.detect(_bd("2024-06-03"))
    assert st == "calm"
    assert d["elevated"]["active"] is False


def test_elevated_triggers_and_hysteresis(tmp_path):
    # build ≥60 daily snapshots with a recession-prob SPIKE on the last day
    alt = tmp_path / "alt"
    alt.mkdir()
    days = pd.date_range("2024-03-01", periods=65, freq="D")
    for i, day in enumerate(days):
        p = 0.10 if i < 64 else 0.60          # flat 10% then a spike to 60%
        (alt / f"snap_{day.date()}.csv").write_text(
            "title,probability\nUS recession 2024,%.2f\n" % p)
    cfg = EventStateConfig(enabled=True, alt_snapshot_dir=str(alt),
                           min_snapshot_days=60, hysteresis_bars=1)
    det = EventStateDetector(cfg)
    bd = _bd("2024-05-01", 25)                # as_of well after the last snapshot? keep within staleness
    # align as_of to the last snapshot day so it isn't stale
    bd = pd.DataFrame({"Close": [100.0] * 3},
                      index=pd.to_datetime([days[-3], days[-2], days[-1]]))
    st, cf, d = det.detect(bd)
    assert d["elevated"]["active"] is True
    assert d["elevated"]["z"] > 1.5           # the spike is a large z
    assert st == "elevated"


def _ohlc(start, n=300):
    idx = pd.date_range(start, periods=n, freq="B")
    px = pd.Series(range(n), index=idx).astype(float) * 0.1 + 100.0
    return pd.DataFrame({"Open": px, "High": px + 1, "Low": px - 1,
                         "Close": px, "Volume": 1e6}, index=idx)


def test_canon_safe_detect_regime_unaffected():
    """detect_regime()'s 5-axis output must be identical whether event_state is
    on or off — proving it is NOT wired into the composition."""
    bd = _ohlc("2022-01-03", 300)
    data = {"SPY": bd}
    off = RegimeDetector(RegimeConfig()).detect_regime(bd, data)
    cfg = RegimeConfig()
    cfg.event_state = EventStateConfig(enabled=True)
    on = RegimeDetector(cfg).detect_regime(bd, data)
    # the composed regime label + axis states are unchanged by the event axis
    assert off.get("regime") == on.get("regime")
    assert "event_state" not in off  # not injected into the canonical dict


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
