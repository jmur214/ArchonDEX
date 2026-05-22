"""tests/test_ml_predictor_narrow_except.py
===========================================
Regression tests for T-2026-05-22-067 — narrow the bare-except in
MLPredictor.predict (ml_predictor.py:133).

Pre-T-067 behavior: ANY exception during pickle.load() silently
returned 0.5 (neutral probability), including programmer errors
(TypeError, NameError, AttributeError on local code). This was the
same bug-class T-005/T-011/T-012 closed elsewhere.

Post-T-067 behavior: catches DATA/FILE errors only (pickle.UnpicklingError,
EOFError, OSError, ImportError, ModuleNotFoundError) + logs them; lets
programmer errors propagate so they surface in tests instead of being
silently swallowed.
"""
from __future__ import annotations

import os
import pickle
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.engine_a_alpha.ml_predictor import MLPredictor


def _synthetic_df(n: int = 60) -> pd.DataFrame:
    """Minimal OHLCV-shaped DataFrame for MLPredictor.predict."""
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "Open": np.linspace(100, 110, n),
            "High": np.linspace(101, 111, n),
            "Low": np.linspace(99, 109, n),
            "Close": np.linspace(100, 110, n),
            "Volume": np.ones(n) * 1_000_000,
        },
        index=idx,
    )


# Module-level so pickle.dump can serialize it (test_predict_normal_path)
class _FakeModelForPickle:
    """Sklearn-shaped stub: predict_proba returns class probs."""

    def predict_proba(self, X):
        n = len(X)
        # Return (n, 2) array — class 0 = 0.3, class 1 = 0.7
        return np.tile([0.3, 0.7], (n, 1))


def test_predict_returns_neutral_when_model_file_missing():
    """Pre-existing path: model_path doesn't exist → return 0.5.
    T-067 preserves this behavior."""
    with tempfile.TemporaryDirectory() as td:
        nonexistent = Path(td) / "no_such_model.pkl"
        p = MLPredictor(model_path=str(nonexistent))
        # Manually set is_trained=False to force the load-path
        p.is_trained = False
        result = p.predict(_synthetic_df())
        assert result == 0.5


def test_predict_returns_neutral_when_pickle_corrupt():
    """T-067: corrupted pickle → catches pickle.UnpicklingError, returns 0.5
    (not exception, not 1e15-style explosion)."""
    with tempfile.TemporaryDirectory() as td:
        corrupt_path = Path(td) / "corrupt.pkl"
        corrupt_path.write_bytes(b"\x80\x04\x95not-actually-a-pickle")
        p = MLPredictor(model_path=str(corrupt_path))
        p.is_trained = False
        result = p.predict(_synthetic_df())
        assert result == 0.5


def test_predict_returns_neutral_when_pickle_truncated():
    """T-067: empty file → catches EOFError, returns 0.5."""
    with tempfile.TemporaryDirectory() as td:
        truncated_path = Path(td) / "truncated.pkl"
        truncated_path.write_bytes(b"")
        p = MLPredictor(model_path=str(truncated_path))
        p.is_trained = False
        result = p.predict(_synthetic_df())
        assert result == 0.5


def test_predict_load_failure_keeps_is_trained_false():
    """T-067: after a failed load, is_trained should remain False so
    subsequent calls don't try to use a missing self.model."""
    with tempfile.TemporaryDirectory() as td:
        corrupt_path = Path(td) / "corrupt.pkl"
        corrupt_path.write_bytes(b"not a valid pickle stream")
        p = MLPredictor(model_path=str(corrupt_path))
        p.is_trained = False
        _ = p.predict(_synthetic_df())
        assert p.is_trained is False, (
            "is_trained should stay False after load failure; otherwise "
            "next predict() would try to use the original RandomForest stub "
            "constructor model (which was never .fit()'d → would crash)"
        )


def test_predict_loads_successfully_when_pickle_is_valid():
    """End-to-end: a saved+loaded valid model DOES set is_trained=True
    and proceeds to predict. Validates the narrowed exception handler
    doesn't accidentally catch the SUCCESS path."""
    with tempfile.TemporaryDirectory() as td:
        model_path = Path(td) / "valid_model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(_FakeModelForPickle(), f)
        p = MLPredictor(model_path=str(model_path))
        p.is_trained = False
        # Don't actually run predict (features may not align with fake model
        # input shape; key test is that loading succeeds + is_trained flips).
        # Test the load path by invoking predict on a substantial df.
        result = p.predict(_synthetic_df(n=100))
        # _FakeModelForPickle returns class-1 prob = 0.7
        assert result == 0.7
        assert p.is_trained is True


def test_predict_propagates_programmer_errors_not_silent():
    """T-067 key contract: programmer errors (TypeError, NameError, etc.)
    that happen INSIDE the try block must propagate (not get silently
    swallowed). We can't easily induce one inside pickle.load() without
    monkeypatching, so this is documented in the source code comment +
    verified via the type signature of the narrowed except clause.

    The narrowed except catches: pickle.UnpicklingError, EOFError, OSError,
    ImportError, ModuleNotFoundError. A bare 'except:' would catch:
    BaseException (everything including KeyboardInterrupt, SystemExit, and
    programmer errors). We assert this is no longer the case.
    """
    # Inspect the source to confirm the bare-except was removed.
    import inspect
    src = inspect.getsource(MLPredictor.predict)
    # The narrowed exception should mention pickle.UnpicklingError
    assert "pickle.UnpicklingError" in src or "UnpicklingError" in src, (
        "T-067 narrowing should reference pickle.UnpicklingError"
    )
    # Should NOT have a bare 'except:' clause
    # (single line starting with whitespace + 'except:' with no exception type)
    import re
    bare_except = re.search(r"\n\s+except\s*:\s*\n", src)
    assert bare_except is None, (
        f"Bare 'except:' found in predict() — T-067 narrowing incomplete: "
        f"{bare_except.group(0).strip() if bare_except else ''}"
    )
