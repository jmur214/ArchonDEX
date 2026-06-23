"""T-227 — runtime dead-gate guard for StrategyGovernor._regime_weights.

The static Layer-4 contract suite (tests/test_contracts.py, T-223) checks
module-level gate dicts' keys ⊆ their emitter vocabulary. `_regime_weights` is
a RUNTIME-BUILT per-instance dict, so the static guard can't introspect it —
the one gate it flagged as out of reach. This closes that gap with a targeted
runtime assertion at the build site.

Contract: `get_edge_weights()` looks regime weights up ONLY by
`macro_regime['label']`, so every key in `_regime_weights` must be a member of
the macro_regime vocabulary (`MACRO_RULES` keys ∪ {"transitional"}). A foreign
key is an UNREACHABLE dead-gate entry (the T-216 class).

Severity by path (CLAUDE.md [NN-FAIL-CLOSED]): measured runs HALT, the
live/local/paper path WARNs. And it must NOT false-fire when the gate is
disabled/empty (prod default: regime_conditional_enabled=False).
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.engine_f_governance.governor import StrategyGovernor
from engines.engine_e_regime.advisory import MACRO_RULES
from core.measured import MeasurementHalt


def _make_governor(tmp_path: Path) -> StrategyGovernor:
    state = tmp_path / "edge_weights.json"
    state.write_text(json.dumps({"weights": {"momentum_edge_v1": 0.5}}))
    cfg_path = tmp_path / "governor_settings.json"
    # regime gate OFF (prod default) so __init__ does not build the dict.
    cfg_path.write_text(json.dumps({
        "ema_halflife_days": 30,
        "lifecycle_enabled": False,
        "regime_conditional_enabled": False,
    }))
    return StrategyGovernor(config_path=str(cfg_path), state_path=str(state))


@pytest.fixture(autouse=True)
def _force_not_measured(monkeypatch):
    """Default every test to NOT-measured; the measured test opts back in.
    Prevents ambient ARCHONDEX_* env from flipping the severity path."""
    monkeypatch.setenv("ARCHONDEX_MEASURED", "0")
    monkeypatch.delenv("ARCHONDEX_HERMETIC", raising=False)


# ----------------------------------------------------------------------
# (a) FIRES on a key-mismatch
# ----------------------------------------------------------------------

def test_measured_run_HALTS_on_foreign_regime_key(tmp_path, monkeypatch):
    """A key no macro_regime label emits (e.g. a forward_stress 'stressed'
    state) is unreachable by the consumer's macro lookup → in a MEASURED run
    that mismatch IS the dead-gate bug and must HALT (NN-FAIL-CLOSED)."""
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    gov = _make_governor(tmp_path)
    # Forge the runtime dict with a foreign key (forward_stress vocab, NOT
    # macro_regime vocab). 'stressed' is not a MACRO_RULES label.
    gov._regime_weights = {"stressed": {"momentum_edge_v1": 0.8}}
    with pytest.raises(MeasurementHalt) as exc:
        gov._assert_regime_weight_keys_reachable()
    assert "stressed" in str(exc.value)
    assert "UNREACHABLE" in str(exc.value)


def test_live_path_WARNS_not_halts_on_foreign_regime_key(tmp_path, caplog):
    """The same mismatch on the live/local path WARNs (a defensive check must
    not break the live governor) — no exception, but a logged warning."""
    gov = _make_governor(tmp_path)
    gov._regime_weights = {"stressed": {"momentum_edge_v1": 0.8}}
    with caplog.at_level(logging.WARNING, logger="governor"):
        gov._assert_regime_weight_keys_reachable()  # must NOT raise
    assert any("stressed" in r.message and "UNREACHABLE" in r.message
               for r in caplog.records)


# ----------------------------------------------------------------------
# (b) does NOT false-fire when disabled/empty or when keys are valid
# ----------------------------------------------------------------------

def test_empty_gate_does_not_fire(tmp_path, caplog, monkeypatch):
    """Gate disabled/empty (prod default) → no HALT, no WARN, even measured."""
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    gov = _make_governor(tmp_path)
    assert gov._regime_weights == {}
    with caplog.at_level(logging.WARNING, logger="governor"):
        gov._assert_regime_weight_keys_reachable()  # must NOT raise
    assert not caplog.records


def test_valid_macro_keys_do_not_fire(tmp_path, caplog, monkeypatch):
    """Keys drawn from the macro_regime vocabulary (incl. the 'transitional'
    fallback) are reachable → no HALT, no WARN, even measured."""
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    gov = _make_governor(tmp_path)
    valid = sorted(set(MACRO_RULES.keys()) | {"transitional"})
    gov._regime_weights = {k: {"momentum_edge_v1": 0.8} for k in valid}
    with caplog.at_level(logging.WARNING, logger="governor"):
        gov._assert_regime_weight_keys_reachable()  # must NOT raise
    assert not caplog.records


def test_consumer_vocab_matches_macro_rules(tmp_path):
    """Guard-the-guard: the vocab the assert checks against is exactly the
    macro_regime label set the consumer (get_edge_weights) can look up. If
    MACRO_RULES grows a regime, a macro key for it must NOT be flagged."""
    gov = _make_governor(tmp_path)
    for label in MACRO_RULES.keys():
        gov._regime_weights = {label: {"momentum_edge_v1": 0.8}}
        gov._assert_regime_weight_keys_reachable()  # no raise for any macro label
