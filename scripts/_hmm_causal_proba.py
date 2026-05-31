"""T-2026-05-31-089 — canonical CAUSAL HMM posterior helper for validators.

`HMMRegimeClassifier.predict_proba_sequence` runs forward-BACKWARD smoothing
(non-causal — each row's posterior is conditioned on FUTURE observations).
That's appropriate for offline labeling but invalid for predictive-validity
diagnostics (AUC of `signal_t` vs forward drawdown `dd_{t→t+k}` would be
contaminated by lookahead).

T-087 (`scripts/validate_regime_signals_t087.py`) established the correct
pattern: call `_hmm.predict_proba` on growing prefixes ending at the current
bar and keep only the LAST row. This file extracts that pattern into a
single canonical helper so all three sibling validators
([4] validate_regime_signals.py, [5] validate_regime_signals_vix_term.py,
[6] backtest_transition_warning.py) can call the same code path.

Per the T-089 dispatch hard constraint, this helper lives in scripts/ —
NOT in `engines/engine_e_regime/hmm_classifier.py` — to avoid modifying
Engine E production code.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def causal_proba_sequence(
    hmm,
    panel: pd.DataFrame,
    window: int = 252,
    feature_names: Optional[list] = None,
    fill_nan_with_uniform: bool = True,
) -> pd.DataFrame:
    """Compute CAUSAL (filtered) HMM posteriors over a panel.

    For each row t in the panel, runs `hmm._hmm.predict_proba` on the
    trailing `window` bars ending at-and-including t (or all available
    history if fewer than `window` bars), and takes the LAST row of the
    output. The result is a per-bar posterior conditioned ONLY on
    observations at-or-before t — no lookahead.

    Args:
        hmm: An HMMRegimeClassifier (or compatible) with attributes
             `feature_names`, `_feature_means`, `_feature_stds`, `n_states`,
             `_state_label_for_idx`, `_hmm.predict_proba`.
        panel: A pandas DataFrame whose columns include the HMM's
               feature_names. Will be filtered to dropna() before
               normalization.
        window: Max trailing bars to use per filter step. Default 252
                (matches the T-087 convention; prevents distant burn-in
                from dominating recent dynamics).
        feature_names: Override the HMM's feature_names. Default uses
                       `list(hmm.feature_names)`.
        fill_nan_with_uniform: When True (default), the returned
                               DataFrame is reindexed to the FULL
                               `panel.index`. Rows missing in `valid`
                               (because the input had NaN in any feature)
                               get a uniform distribution `1/n_states`
                               per state — same fallback the per-bar
                               classifier uses.

    Returns:
        DataFrame indexed by `panel.index` (full) or `valid.index`
        (if fill_nan_with_uniform=False), columns = state labels in
        `hmm._state_label_for_idx` order. Values sum to ~1.0 per row.
    """
    if feature_names is None:
        feature_names = list(hmm.feature_names)
    valid = panel[feature_names].dropna()
    if valid.empty:
        # Edge case: no rows have all features. Return uniform over panel
        # (or empty if no fill requested).
        state_cols = list(hmm._state_label_for_idx)
        if fill_nan_with_uniform:
            uniform = 1.0 / len(state_cols)
            df = pd.DataFrame(uniform, index=panel.index, columns=state_cols)
            return df
        return pd.DataFrame(columns=state_cols)

    Z = (valid.values - hmm._feature_means) / hmm._feature_stds
    n_rows = len(Z)
    state_cols = list(hmm._state_label_for_idx)
    proba_arr = np.empty((n_rows, hmm.n_states), dtype=np.float64)
    for t in range(n_rows):
        # `start_t` ensures each filter step uses up to `window` trailing
        # rows (inclusive of t) — never more, so distant pre-window
        # burn-in can't dominate, and never fewer than `t+1` when t < window.
        start_t = max(0, t - window + 1)
        proba_arr[t] = hmm._hmm.predict_proba(Z[start_t:t + 1])[-1]

    proba_df_valid = pd.DataFrame(proba_arr, index=valid.index, columns=state_cols)
    if not fill_nan_with_uniform:
        return proba_df_valid

    # Reindex to the full panel; uniform-distribute over NaN-row positions.
    proba_df = proba_df_valid.reindex(panel.index)
    uniform_val = 1.0 / hmm.n_states
    for c in state_cols:
        proba_df[c] = proba_df[c].fillna(uniform_val)
    return proba_df


__all__ = ["causal_proba_sequence"]
