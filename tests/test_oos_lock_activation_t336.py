# tests/test_oos_lock_activation_t336.py
"""T-336(c) — the OOS lock is ACTIVE (it had zero callers and no config before)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.oos_lock import (
    load_oos_lock, assert_not_tuning_in_oos, OOSLockViolation, DEFAULT_LOCK_PATH,
)

ROOT = Path(__file__).resolve().parents[1]


def test_config_exists_and_is_active():
    """The module was complete but inert — no config meant every helper no-op'd."""
    assert DEFAULT_LOCK_PATH.exists(), "config/oos_window.json must exist"
    cfg = json.loads(DEFAULT_LOCK_PATH.read_text())
    assert cfg["active"] is True
    assert cfg["frozen_parameters"], "an active lock with no frozen params is inert"


def test_frozen_params_cover_the_precommitted_spec():
    """T-260-deep pre-committed that {42,105,210} would not be re-selected; the lock
    is what makes that enforceable rather than remembered."""
    frozen = set(json.loads(DEFAULT_LOCK_PATH.read_text())["frozen_parameters"])
    assert "ensemble_speeds" in frozen
    assert "damping_band_B" in frozen


def test_violation_is_refused():
    with pytest.raises(OOSLockViolation):
        assert_not_tuning_in_oos(parameter="ensemble_speeds",
                                 sweep_start="2026-01-01", sweep_end="2026-12-31",
                                 lock=load_oos_lock())


def test_no_false_positive_on_unfrozen_parameter():
    assert_not_tuning_in_oos(parameter="not_a_frozen_param",
                             sweep_start="2026-01-01", sweep_end="2026-12-31",
                             lock=load_oos_lock())


def test_no_false_positive_before_the_window():
    assert_not_tuning_in_oos(parameter="ensemble_speeds",
                             sweep_start="2020-01-01", sweep_end="2021-12-31",
                             lock=load_oos_lock())


def test_registry_backfill_is_idempotent_and_raises_n():
    """T-336(a): compute_n_effective must reflect the refreshed registry."""
    from core.measurement.mbl_gate import compute_n_effective
    assert compute_n_effective() > 125, "registry still frozen at the 2026-05-08 count"


def test_gate8_default_now_resolves_to_honest_n():
    """T-336(b): Gate 8's default was a hardcoded 1 — i.e. the multiple-testing
    correction was SILENTLY OFF in every default run. It must now resolve to the
    project's honest N, and that N must actually bite on a plausible candidate."""
    import inspect
    import numpy as np, pandas as pd
    from engines.engine_d_discovery.discovery import DiscoveryEngine  # noqa
    from core.measurement.mbl_gate import compute_n_effective
    from core.metrics_engine import MetricsEngine

    sig = inspect.signature(DiscoveryEngine.validate_candidate)
    assert sig.parameters["n_trials_for_dsr"].default is None, \
        "default must be the None sentinel that resolves to compute_n_effective()"

    n = compute_n_effective()
    att = pd.Series(np.random.default_rng(0).normal(0.0012, 0.010, 900))
    assert MetricsEngine.deflated_sharpe_ratio(att, n_trials=1) >= 0.95      # legacy: PASS
    assert MetricsEngine.deflated_sharpe_ratio(att, n_trials=n) < 0.95       # honest N: FAIL
