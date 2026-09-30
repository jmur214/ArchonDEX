"""
Statistical significance testing for edge discovery validation.

Provides three key tests:
1. Monte Carlo permutation test — shuffle returns to build null distribution,
   compare actual Sharpe to determine if performance is statistically significant.
2. Minimum Track Record Length (MinTRL) — Bailey & Lopez de Prado formula to
   determine how many observations are needed before a Sharpe ratio is reliable.
3. Benjamini-Hochberg false-discovery-rate correction — adjusts a batch of
   p-values for multiple testing so that the discovery cycle doesn't pass ~5%
   of candidates on pure noise.

Multiple-testing-correction usage:
    Each candidate's `monte_carlo_permutation_test` returns a raw p-value. The
    caller (the discovery orchestrator) batches all candidate p-values from a
    cycle and calls `apply_bh_fdr` once to compute the BH-corrected gate.
    Per-test API is intentionally unchanged — the correction is a batch step.
"""

from typing import Optional, Sequence
import logging

import numpy as np

logger = logging.getLogger("SIGNIFICANCE")


def _sharpe(x: np.ndarray, annualization: float) -> float:
    sd = x.std()
    if sd is None or sd < 1e-12 or not np.isfinite(sd):     # [NN-FP-GUARDS]
        return 0.0
    return float(x.mean() / sd * annualization)


def _stationary_block_signs(n: int, block_length: float,
                            rng: np.random.RandomState) -> np.ndarray:
    """One random sign per STATIONARY block (geometric block lengths, mean L).

    Blocks are what keep the null honest on autocorrelated returns: an iid sign-flip
    treats every day as independent, understates the null's spread, and so INFLATES
    significance — the iid-resampling error `[NN-SHARPE-CI]` rules out."""
    starts = rng.random_sample(n) < (1.0 / max(block_length, 1.0))
    starts[0] = True
    block_id = np.cumsum(starts) - 1
    eps = rng.choice([-1.0, 1.0], size=int(block_id[-1]) + 1)
    return eps[block_id]


def _block_permute(x: np.ndarray, block_length: int,
                   rng: np.random.RandomState) -> np.ndarray:
    """Permute the ORDER of contiguous blocks, preserving within-block
    autocorrelation of the signal while destroying its alignment to returns."""
    n = len(x)
    L = max(int(block_length), 1)
    blocks = [x[i:i + L] for i in range(0, n, L)]
    order = rng.permutation(len(blocks))
    return np.concatenate([blocks[i] for i in order])[:n]


def _perm_p(null: np.ndarray, actual: float) -> float:
    """Unbiased permutation p-value (Phipson & Smyth 2010): (1 + k) / (1 + n).
    A finite permutation test can never honestly report p = 0."""
    return float((1 + np.sum(null >= actual)) / (1 + len(null)))


def monte_carlo_permutation_test(
    strategy_returns: np.ndarray,
    n_permutations: int = 1000,
    annualization: float = np.sqrt(252),
    random_state: Optional[int] = 42,
    signal: Optional[np.ndarray] = None,
    asset_returns: Optional[np.ndarray] = None,
    block_length: Optional[float] = None,
) -> dict:
    """Gate-4 significance — a null distribution that CAN reject.

    RR-2 (2026-09-30). The previous null permuted the strategy's OWN returns. Mean and
    std are permutation-invariant, so every null Sharpe equalled the actual Sharpe
    (null_std ~ 1e-15) and the p-value was floating-point noise: a Sharpe-5.2 series
    scored p = 0.973. The earlier audit sentence "tests whether temporal ordering
    matters for the Sharpe" WAS the defect — the Sharpe does not depend on ordering.

    Two valid constructions, both preserving autocorrelation:

    * SIGN-FLIP (always computable from `strategy_returns` alone): H0 is "the stream's
      true mean is zero, and its distribution is symmetric". Each STATIONARY block
      (geometric lengths, mean L = n^(1/3)) gets one random sign.
    * SIGNAL-PERMUTATION (only when `signal` AND `asset_returns` are given): block-
      permute the signal against the asset returns and recompute signal x returns.
      Destroys the signal-return alignment while preserving both marginals. Valid ONLY
      where the strategy IS signal x asset_returns — a single signal on one return
      stream. It is NOT a valid null for a PORTFOLIO attribution (with - base), whose
      relation to the candidate's signal runs through the whole allocator.

    When both are computable, `p_value` is the LARGER of the two: a candidate must be
    significant under every valid null we can build, not the friendlier one.

    Returns the original keys (p_value, actual_sharpe, null_mean, null_std, percentile)
    — so callers and `apply_bh_fdr` need no change — plus `null_construction`,
    `p_value_sign_flip`, and `p_value_signal_perm` (None when not computable).
    """
    rng = np.random.RandomState(random_state)
    returns = np.asarray(strategy_returns, dtype=float)
    returns = returns[~np.isnan(returns)]
    n = len(returns)

    if n < 20:
        logger.warning("[SIGNIFICANCE] Too few returns for permutation test.")
        return {"p_value": 1.0, "actual_sharpe": 0.0, "null_mean": 0.0,
                "null_std": 0.0, "percentile": 50.0,
                "null_construction": "insufficient_data",
                "p_value_sign_flip": None, "p_value_signal_perm": None}

    L = float(block_length) if block_length else max(1.0, n ** (1.0 / 3.0))
    actual_sharpe = _sharpe(returns, annualization)

    # ---- sign-flip null (always) ------------------------------------------------
    sf_null = np.empty(n_permutations)
    for i in range(n_permutations):
        sf_null[i] = _sharpe(returns * _stationary_block_signs(n, L, rng), annualization)
    p_sf = _perm_p(sf_null, actual_sharpe)

    # ---- signal-permutation null (only when a signal x returns pair exists) --------
    p_sp, sp_null = None, None
    if signal is not None and asset_returns is not None:
        sig = np.asarray(signal, dtype=float)
        ast = np.asarray(asset_returns, dtype=float)
        if len(sig) == len(ast) and len(sig) >= 20:
            ok = ~(np.isnan(sig) | np.isnan(ast))
            sig, ast = sig[ok], ast[ok]
            actual_sp = _sharpe(sig * ast, annualization)
            sp_null = np.empty(n_permutations)
            for i in range(n_permutations):
                sp_null[i] = _sharpe(_block_permute(sig, int(round(L)), rng) * ast,
                                     annualization)
            p_sp = _perm_p(sp_null, actual_sp)

    # the reported p is the MORE CONSERVATIVE of the valid nulls
    if p_sp is not None and p_sp >= p_sf:
        primary, construction, p = sp_null, "signal_permutation(block)", p_sp
    else:
        primary, construction, p = sf_null, "sign_flip(stationary_block)", p_sf
    if p_sp is not None:
        construction = f"max(sign_flip, signal_permutation) -> {construction}"

    return {
        "p_value": float(p),
        "actual_sharpe": float(actual_sharpe),
        "null_mean": float(primary.mean()),
        "null_std": float(primary.std()),
        "percentile": float((primary < actual_sharpe).mean() * 100),
        "null_construction": construction,
        "p_value_sign_flip": float(p_sf),
        "p_value_signal_perm": None if p_sp is None else float(p_sp),
        "block_length": float(L),
    }

def apply_bh_fdr(
    p_values: Sequence[float],
    alpha: float = 0.05,
) -> dict:
    """
    Benjamini-Hochberg false-discovery-rate correction for a batch of p-values.

    Controls FDR at level `alpha` across the full batch — the expected
    proportion of false positives among rejected nulls is bounded by alpha,
    even when many tests are run together. Less conservative than Bonferroni
    (which controls the family-wise error rate) and closer to the right
    primitive for "we tested 100 candidate edges and want to keep the real
    ones without flooding production with noise."

    Reference: Benjamini & Hochberg (1995), "Controlling the False Discovery
    Rate: A Practical and Powerful Approach to Multiple Testing."

    Procedure:
        1. Sort the p-values ascending: p_(1) <= p_(2) <= ... <= p_(m).
        2. Find the largest k such that p_(k) <= (k / m) * alpha.
        3. Reject H0 for all tests with p <= p_(k) (the "BH threshold").
        4. Adjusted p-values: p_adj_(i) = min_{j>=i}(p_(j) * m / j), capped at 1.

    Parameters
    ----------
    p_values : sequence of float
        Raw p-values from independent (or PRDS-dependent) tests, e.g. one
        per candidate edge from `monte_carlo_permutation_test`.
    alpha : float
        Target false-discovery rate (default 0.05). The expected fraction
        of rejected nulls that are actually true (false positives) is
        bounded by this value.

    Returns
    -------
    dict with keys:
        - adjusted_p_values: list[float] — BH-adjusted p-values aligned to
          the input order. Compare directly to alpha to test rejection.
        - reject_at_alpha: list[bool] — True for tests rejected at the BH
          threshold (i.e., adjusted p <= alpha), aligned to input order.
        - threshold: float — the largest raw p-value that is rejected.
          Returns 0.0 if no test is rejected (no candidate is significant).
        - n_tests: int — batch size (informational).
        - n_rejected: int — number of rejections at this alpha.

    Notes
    -----
    Edge cases:
        - Empty input: returns zero-length lists, threshold 0.0.
        - Single p-value: BH reduces to plain p < alpha (no correction
          since correction factor m/k = 1/1 = 1).
        - All identical p-values: tied, all rejected together if any is.
        - NaN p-values: treated as 1.0 (cannot reject).
    """
    p_arr = np.asarray(list(p_values), dtype=float)
    m = len(p_arr)

    if m == 0:
        return {
            "adjusted_p_values": [],
            "reject_at_alpha": [],
            "threshold": 0.0,
            "n_tests": 0,
            "n_rejected": 0,
        }

    # Coerce NaN to 1.0 (can't reject — most conservative).
    p_arr = np.where(np.isnan(p_arr), 1.0, p_arr)

    # Sort ascending and remember the inverse permutation to map back.
    order = np.argsort(p_arr, kind="mergesort")
    sorted_p = p_arr[order]
    ranks = np.arange(1, m + 1, dtype=float)

    # BH adjusted p-values via standard right-to-left cumulative-min:
    #   p_adj_(i) = min_{j >= i} ( m/j * p_(j) ), then cap at 1.
    raw_adj = sorted_p * m / ranks
    sorted_adj = np.minimum.accumulate(raw_adj[::-1])[::-1]
    sorted_adj = np.minimum(sorted_adj, 1.0)

    # Map adjusted values back to input order.
    adjusted = np.empty_like(sorted_adj)
    adjusted[order] = sorted_adj

    # BH rejection threshold: largest sorted p with sorted_p <= (k/m) * alpha.
    crit_line = ranks / m * alpha
    below = sorted_p <= crit_line
    if np.any(below):
        k = int(np.max(np.where(below)[0])) + 1  # 1-indexed largest passing rank
        threshold = float(sorted_p[k - 1])
    else:
        k = 0
        threshold = 0.0

    reject = adjusted <= alpha

    return {
        "adjusted_p_values": [float(x) for x in adjusted],
        "reject_at_alpha": [bool(x) for x in reject],
        "threshold": threshold,
        "n_tests": m,
        "n_rejected": int(reject.sum()),
    }


def minimum_track_record_length(
    observed_sharpe: float,
    benchmark_sharpe: float = 0.0,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> int:
    """
    Minimum Track Record Length (MinTRL) per Bailey & Lopez de Prado (2012).

    Returns the minimum number of observations needed before the observed
    Sharpe ratio is statistically reliable at the 95% confidence level.

    Parameters
    ----------
    observed_sharpe : float
        Annualized Sharpe ratio observed in backtest.
    benchmark_sharpe : float
        Sharpe ratio of the benchmark (usually 0 for "is this better than nothing?").
    skewness : float
        Skewness of returns (0 for normal).
    kurtosis : float
        Kurtosis of returns (3 for normal).

    Returns
    -------
    int — minimum number of observations (trading days).
    """
    sr_diff = observed_sharpe - benchmark_sharpe
    if abs(sr_diff) < 1e-9:
        return 999999  # infinite — can't distinguish from benchmark

    # Z-score for 95% confidence
    z_alpha = 1.96

    # MinTRL formula (annualized Sharpe, daily observations)
    # MinTRL = 1 + (1 - skew*SR + (kurtosis-1)/4 * SR^2) * (z/SR_diff)^2
    sr = observed_sharpe / np.sqrt(252)  # de-annualize to per-period
    sr_diff_per = sr_diff / np.sqrt(252)

    if abs(sr_diff_per) < 1e-12:
        return 999999

    variance_factor = 1.0 - skewness * sr + ((kurtosis - 1) / 4.0) * sr**2
    min_trl = 1 + variance_factor * (z_alpha / sr_diff_per) ** 2

    return max(int(np.ceil(min_trl)), 1)
