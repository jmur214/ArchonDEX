"""T-2026-05-31-089 regression tests — guard against re-introduction
of `predict_proba_sequence` (forward-BACKWARD smoothing) in the
regime-validation scripts.

The bug class: HMMRegimeClassifier.predict_proba_sequence runs
forward-backward smoothed posteriors where each row's value is
conditioned on FUTURE observations. That's appropriate for offline
labeling but invalid for predictive-validity diagnostics (AUC of
signal_t vs forward dd_{t→t+k}) — it injects lookahead.

The 3 fixed scripts ([4][5][6] per the T-089 dispatch) must use the
shared `scripts._hmm_causal_proba.causal_proba_sequence` helper
instead. This test enforces that contract by static-text inspection
plus a behavioral check that the helper exists and is callable.
"""
from __future__ import annotations

from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]

# The 3 scripts T-089 fixed; if any future edit re-introduces
# `predict_proba_sequence` to one of these, this test fires.
T089_VALIDATOR_SCRIPTS = [
    "scripts/validate_regime_signals.py",
    "scripts/validate_regime_signals_vix_term.py",
    "scripts/backtest_transition_warning.py",
]

# The T-087 validator is the gold-standard causal pattern; it must
# remain causal.
T087_CAUSAL_REFERENCE = "scripts/validate_regime_signals_t087.py"


def _read(rel_path: str) -> str:
    return (REPO / rel_path).read_text()


def _strip_comments(source: str) -> str:
    """Drop full-line and inline `#`-style comments so test only inspects
    EXECUTABLE Python. Otherwise legitimate explanatory comments
    referencing `predict_proba_sequence` (which we ADDED in T-089 to
    explain the fix) would trigger the regression."""
    out_lines = []
    for line in source.splitlines():
        # Drop everything after the first `#` on the line — coarse but
        # sufficient for this guard. Triple-quoted-string content
        # remains, but those are also documentation, not call paths.
        idx = line.find("#")
        if idx >= 0:
            line = line[:idx]
        out_lines.append(line)
    return "\n".join(out_lines)


@pytest.mark.parametrize("script_path", T089_VALIDATOR_SCRIPTS)
def test_no_predict_proba_sequence_in_validator_code(script_path):
    """Each T-089-fixed validator must NOT invoke `predict_proba_sequence`
    in executable code. Docstrings and comments referencing it are
    allowed (we explain the historical bug + fix there)."""
    source = _read(script_path)
    code = _strip_comments(source)
    # After stripping comments, no executable line should contain the
    # method call. We check for the open-paren form to allow free
    # mentions in remaining triple-quoted docstrings — but the simplest
    # test is to assert no `.predict_proba_sequence(` substring in code.
    assert ".predict_proba_sequence(" not in code, (
        f"{script_path} contains an executable call to "
        f"`.predict_proba_sequence(` — this is the forward-backward "
        f"smoothed (non-causal) path. Use "
        f"`scripts._hmm_causal_proba.causal_proba_sequence` instead "
        f"(T-089 dispatch fix)."
    )


@pytest.mark.parametrize("script_path", T089_VALIDATOR_SCRIPTS)
def test_validator_imports_causal_helper(script_path):
    """Each T-089-fixed validator must import the canonical causal
    helper. Catches refactor-regressions where the call gets replaced
    with a private inline path that might drift from the T-087 pattern."""
    source = _read(script_path)
    assert "causal_proba_sequence" in source, (
        f"{script_path} must reference `causal_proba_sequence` (from "
        f"`scripts._hmm_causal_proba`) — the canonical T-087 causal "
        f"per-bar growing-prefix labeling pattern."
    )


def test_t087_reference_validator_uses_causal_path():
    """T-087's `validate_regime_signals_t087.py` is the reference
    implementation. It established the AUC 0.887 / 0.804 headline
    causally and must not regress to the leaky path."""
    source = _read(T087_CAUSAL_REFERENCE)
    code = _strip_comments(source)
    assert ".predict_proba_sequence(" not in code, (
        f"{T087_CAUSAL_REFERENCE} regressed to predict_proba_sequence — "
        f"this would invalidate the AUC 0.887 reversal of the "
        f"2026-05-06 regime-refuted verdict."
    )
    # Also positively assert the growing-prefix loop signature is
    # present. Pre-fix the script did `hmm._hmm.predict_proba(Z[start_t:t + 1])[-1]`
    # in a `for t in range(n_rows):` body — that's the load-bearing
    # pattern.
    assert "predict_proba(Z[start_t:t" in code or "predict_proba(Z[start_t : t" in code, (
        f"{T087_CAUSAL_REFERENCE} no longer contains the growing-prefix "
        f"call `predict_proba(Z[start_t:t + 1])`. T-087's causal "
        f"diagnostic is at risk."
    )


def test_causal_helper_module_importable_and_exports():
    """The shared helper must be importable and expose the public
    function."""
    from scripts import _hmm_causal_proba as helper
    assert hasattr(helper, "causal_proba_sequence"), (
        "scripts/_hmm_causal_proba.py must export causal_proba_sequence"
    )
    assert callable(helper.causal_proba_sequence)


def test_causal_helper_signature_matches_dispatch_contract():
    """Helper signature: `causal_proba_sequence(hmm, panel, window=252, ...)`.
    Required positional args + the `window=252` default that mirrors
    T-087's convention."""
    import inspect
    from scripts._hmm_causal_proba import causal_proba_sequence
    sig = inspect.signature(causal_proba_sequence)
    params = list(sig.parameters.keys())
    assert params[0] == "hmm"
    assert params[1] == "panel"
    assert "window" in sig.parameters
    assert sig.parameters["window"].default == 252


def test_causal_helper_growing_prefix_with_synthetic_hmm():
    """Behavioral test: feed a synthetic HMM-shaped fake and confirm
    the helper iterates a growing prefix capped at `window`. The fake
    records each call's Z.shape so we can assert it never exceeds
    window rows."""
    import numpy as np
    import pandas as pd
    from scripts._hmm_causal_proba import causal_proba_sequence

    class _FakeInnerHMM:
        def __init__(self):
            self.call_shapes = []

        def predict_proba(self, Z):
            self.call_shapes.append(Z.shape)
            # Return uniform 2-state posterior for each row.
            n = Z.shape[0]
            return np.full((n, 2), 0.5)

    class _FakeHMM:
        feature_names = ["f0", "f1"]
        _feature_means = np.zeros(2)
        _feature_stds = np.ones(2)
        n_states = 2
        _state_label_for_idx = ("benign", "crisis")

        def __init__(self):
            self._hmm = _FakeInnerHMM()

    fake = _FakeHMM()
    # 10-row panel, window=4.
    idx = pd.date_range("2024-01-02", periods=10, freq="B")
    panel = pd.DataFrame(
        {"f0": np.arange(10, dtype=float), "f1": np.arange(10, dtype=float) * 0.5},
        index=idx,
    )
    out = causal_proba_sequence(fake, panel, window=4)
    # Should have 10 rows of output (one per panel row, no NaNs).
    assert len(out) == 10
    # Should have made 10 predict_proba calls.
    assert len(fake._hmm.call_shapes) == 10
    # The t-th call (0-indexed) must use exactly min(t+1, window) rows.
    for t, (n_rows, n_cols) in enumerate(fake._hmm.call_shapes):
        assert n_rows == min(t + 1, 4), (
            f"call {t} used {n_rows} rows, expected min({t}+1, 4)"
        )
        assert n_cols == 2  # 2 features


def test_causal_helper_uniform_fill_on_nan_rows():
    """Rows with NaN features must get uniform `1/n_states` fill when
    `fill_nan_with_uniform=True` (default), matching the per-bar
    classifier's fallback."""
    import numpy as np
    import pandas as pd
    from scripts._hmm_causal_proba import causal_proba_sequence

    class _FakeInnerHMM:
        def predict_proba(self, Z):
            n = Z.shape[0]
            return np.full((n, 3), 1.0 / 3.0)

    class _FakeHMM:
        feature_names = ["f0"]
        _feature_means = np.zeros(1)
        _feature_stds = np.ones(1)
        n_states = 3
        _state_label_for_idx = ("benign", "cautious", "crisis")

        def __init__(self):
            self._hmm = _FakeInnerHMM()

    fake = _FakeHMM()
    idx = pd.date_range("2024-01-02", periods=5, freq="B")
    panel = pd.DataFrame({"f0": [1.0, np.nan, 2.0, np.nan, 3.0]}, index=idx)
    out = causal_proba_sequence(fake, panel, window=10)
    assert len(out) == 5
    # NaN rows should be 1/3 across all states.
    for nan_t in (1, 3):
        for col in ("benign", "cautious", "crisis"):
            assert abs(out.iloc[nan_t][col] - 1.0 / 3.0) < 1e-12
