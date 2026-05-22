
import numpy as np
import pandas as pd
from scipy import stats as _stats
from typing import Dict, Any, Optional

# Euler-Mascheroni constant (used by DSR)
_EULER_GAMMA = 0.5772156649015329

class MetricsEngine:
    """
    Tier 2 Metrics: Institutional Grade Scorecard.
    
    Centralized logic for calculating performance metrics across Research,
    Backtesting, and Live Trading.
    """
    
    @staticmethod
    def calculate_all(equity_curve: pd.Series, benchmark_curve: Optional[pd.Series] = None) -> Dict[str, float]:
        """
        Compute comprehensive metrics from an equity curve (daily or intraday).
        """
        if equity_curve.empty or len(equity_curve) < 2:
            return MetricsEngine._empty_metrics()
            
        returns = equity_curve.pct_change().dropna()
        if len(returns) < 2 or returns.std() == 0:
             return MetricsEngine._empty_metrics()
        
        # 1. Basic Risk/Return
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1.0
        cagr = MetricsEngine.cagr(equity_curve)
        sharpe = MetricsEngine.sharpe_ratio(returns)
        sortino = MetricsEngine.sortino_ratio(returns)
        max_dd = MetricsEngine.max_drawdown(equity_curve)
        calmar = cagr / abs(max_dd) if max_dd != 0 else 0.0
        volatility = returns.std() * np.sqrt(252)
        
        # 2. Trade Statistics (Implied from curve)
        # Note: True trade stats require a trade log, but we can estimate from curve
        # Win Rate etc. requires distinct periods or trade list.
        # Here we only compute Time-Series metrics.
        
        # 3. Advanced Risk
        var_95 = MetricsEngine.value_at_risk(returns, 0.95)
        ulcer = MetricsEngine.ulcer_index(equity_curve)
        skew = MetricsEngine.skewness(returns)
        ex_kurt = MetricsEngine.excess_kurtosis(returns)
        tail = MetricsEngine.tail_ratio(returns)

        # 4. Statistical Sharpe — sample-size + skew + kurtosis aware
        # PSR > benchmark Sharpe is the right "is this Sharpe real" gate
        psr_above_zero = MetricsEngine.probabilistic_sharpe_ratio(returns, 0.0)

        # 5. Benchmark Relative
        beta = 0.0
        alpha = 0.0
        info_ratio = 0.0
        if benchmark_curve is not None and not benchmark_curve.empty:
            # Align
            bench_returns = benchmark_curve.pct_change().dropna()
            aligned = pd.concat([returns, bench_returns], axis=1, join="inner").dropna()
            if not aligned.empty:
                beta = MetricsEngine.beta(aligned.iloc[:, 0], aligned.iloc[:, 1])
                # Alpha approx
                alpha = total_return - (beta * ((benchmark_curve.iloc[-1]/benchmark_curve.iloc[0]) - 1.0))
                info_ratio = MetricsEngine.information_ratio(aligned.iloc[:, 0], aligned.iloc[:, 1])

        return {
            "Total Return %": total_return * 100,
            "CAGR %": cagr * 100,
            "Sharpe": sharpe,
            "Sortino": sortino,
            "PSR": psr_above_zero,
            "Max Drawdown %": max_dd * 100,
            "Calmar": calmar,
            "Ulcer Index": ulcer,
            "Volatility %": volatility * 100,
            "VaR 95%": var_95 * 100,
            "Skewness": skew,
            "Excess Kurtosis": ex_kurt,
            "Tail Ratio": tail,
            "Beta": beta,
            "Alpha": alpha,
            "Information Ratio": info_ratio,
        }

    @staticmethod
    def _empty_metrics():
        return {k: 0.0 for k in [
            "Total Return %", "CAGR %", "Sharpe", "Sortino", "PSR",
            "Max Drawdown %", "Calmar", "Ulcer Index", "Volatility %",
            "VaR 95%", "Skewness", "Excess Kurtosis", "Tail Ratio",
            "Beta", "Alpha", "Information Ratio",
        ]}

    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods: int = 252) -> float:
        # T-061 (2026-05-22, user-approved): tolerance (not == 0) — pandas
        # std on identical floats can return tiny-but-nonzero (e.g., 2e-19
        # for pd.Series([0.001]*100)) which previously produced an exploding
        # ~1e15 Sharpe. The legacy test
        # `test_sharpe_known_floating_point_edge_case_for_constant_positive_returns`
        # documented this as "behavior change requiring user approval";
        # approval granted 2026-05-22.
        std = returns.std()
        if std is None or std < 1e-12 or not np.isfinite(std):
            return 0.0
        return (returns.mean() - risk_free_rate) / std * np.sqrt(periods)

    @staticmethod
    def lo_eta(returns: pd.Series, q: int = 252, max_lag: Optional[int] = None) -> float:
        """Lo (FAJ 2002, eq. 14) autocorrelation-corrected annualization factor.

        Naive Sharpe annualization multiplies by √q (q=252 for daily). When
        returns are autocorrelated, the true q-period volatility is NOT
        σ_period · √q — positive autocorrelation inflates aggregate variance;
        negative autocorrelation deflates it. The naive annualization
        OVERSTATES Sharpe when ρ₁ > 0.

        Lo derives the correct factor:
            η(q) = q / √[q + 2 · Σ_{k=1}^{q-1} (q − k) · ρ_k]

        When ρ_k = 0 for all k ≥ 1, η(q) = q/√q = √q (matches naive).
        When ρ_k > 0, η(q) < √q (correction REDUCES annualized Sharpe).
        When ρ_k < 0, η(q) > √q (correction INCREASES annualized Sharpe).

        Lo's empirical finding on hedge-fund returns: naive Sharpes are
        overstated ~65% when ρ₁ ≈ 0.34 is ignored. For daily equity returns
        with mild autocorrelation (ρ₁ ≈ 0.05-0.10), expect a 5-15%
        correction. Per CLAUDE.md 6th non-negotiable, Sharpe reporting should
        carry CI; this correction also affects the annualized point estimate.

        Args:
            returns: per-period (e.g., daily) excess returns
            q: annualization periods (252 for daily, 12 for monthly, etc.)
            max_lag: cap on the autocorrelation sum. Default min(q-1, n-1).
                     For q=252 and typical 1-year samples this can be slow;
                     limiting to ~60-120 captures the bulk of equity
                     autocorrelation decay (returns decorrelate within
                     1-2 trading months).

        Returns:
            η(q) — the autocorrelation-corrected annualization factor.
            Multiply (returns.mean() / returns.std()) by η(q) to get the
            corrected annualized Sharpe.

        Reference: Lo, A. W. (2002). "The Statistics of Sharpe Ratios."
        Financial Analysts Journal 58(4): 36-52.
        """
        n = len(returns)
        if n < 2:
            return float(np.sqrt(q))
        if max_lag is None:
            max_lag = min(q - 1, n - 1)
        max_lag = max(0, min(max_lag, n - 1, q - 1))
        if max_lag == 0:
            return float(np.sqrt(q))
        # Sample autocorrelations at lags 1..max_lag
        x = returns.values
        x_centered = x - x.mean()
        denom = float((x_centered ** 2).sum())
        if denom == 0:
            return float(np.sqrt(q))
        # Lo's sum: 2 · Σ (q − k) · ρ_k for k=1..min(q-1, max_lag)
        weight_sum = 0.0
        for k in range(1, max_lag + 1):
            rho_k = float((x_centered[:-k] * x_centered[k:]).sum() / denom)
            weight_sum += (q - k) * rho_k
        variance_inflator = q + 2.0 * weight_sum
        if variance_inflator <= 0:
            # Pathological case (extreme negative autocorrelation); fall back
            # to naive √q with a sentinel that the caller can detect via |η|
            # > √q being unusual.
            return float(np.sqrt(q))
        return float(q / np.sqrt(variance_inflator))

    @staticmethod
    def sharpe_ratio_lo_corrected(
        returns: pd.Series,
        risk_free_rate: float = 0.0,
        periods: int = 252,
        max_lag: Optional[int] = None,
    ) -> float:
        """Sharpe with Lo autocorrelation correction (returns the corrected
        annualized Sharpe instead of √periods naive annualization).

        See `lo_eta` for the math + reference. Always opt-in (the naive
        `sharpe_ratio` method is unchanged for backwards compat). Per the
        2026-05-16 metrics research dive: mandatory for any sub-daily or
        illiquid / hedge-fund-style monthly series; advisory for daily
        equity strategies where ρ₁ is typically small.
        """
        std = returns.std()
        # Use tolerance (not == 0) because pandas std on identical floats
        # can return tiny-but-nonzero values (e.g., 2e-19 for [0.001]*100).
        if std is None or std < 1e-12 or not np.isfinite(std):
            return 0.0
        per_period = (returns.mean() - risk_free_rate) / std
        eta = MetricsEngine.lo_eta(returns, q=periods, max_lag=max_lag)
        return float(per_period * eta)

    @staticmethod
    def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods: int = 252) -> float:
        downside = returns[returns < 0]
        if downside.empty or downside.std() == 0: return 10.0 # Capped max
        return (returns.mean() - risk_free_rate) / downside.std() * np.sqrt(periods)

    @staticmethod
    def max_drawdown(equity_curve: pd.Series) -> float:
        """Returns positive number 0.15 for 15% drawdown, or strictly negative? Convention: Negative."""
        roll_max = equity_curve.cummax()
        drawdown = (equity_curve - roll_max) / roll_max
        return float(drawdown.min())

    @staticmethod
    def cagr(equity_curve: pd.Series) -> float:
        if len(equity_curve) < 2: return 0.0
        start = equity_curve.index[0]
        end = equity_curve.index[-1]
        years = (end - start).days / 365.25
        if years < 0.1: return 0.0 # Too short
        total_ret = equity_curve.iloc[-1] / equity_curve.iloc[0]
        if total_ret <= 0: return -1.0
        return float(total_ret ** (1 / years) - 1)

    @staticmethod
    def beta(strategy_rets: pd.Series, benchmark_rets: pd.Series) -> float:
        cov = strategy_rets.cov(benchmark_rets)
        var = benchmark_rets.var()
        if var == 0: return 0.0
        return float(cov / var)
        
    @staticmethod
    def value_at_risk(returns: pd.Series, confidence: float = 0.95) -> float:
        """
        Historical VaR.

        NOTE (post-2026-05-16 metrics dive): VaR is NOT coherent — violates
        subadditivity (Artzner-Delbaen-Eber-Heath 1999); tail-blind. Basel III
        FRTB (BCBS d352, 2016) replaced 99% VaR with 97.5% Expected Shortfall.
        Prefer `MetricsEngine.expected_shortfall()` for new code.
        """
        return float(np.percentile(returns, 100 * (1 - confidence)))

    @staticmethod
    def expected_shortfall(returns: pd.Series, confidence: float = 0.975) -> float:
        """Expected Shortfall (a.k.a. CVaR / TVaR) at the given confidence.

        ES_α is the average of the worst (1−α)·100% losses. Mathematically:
            ES_α = E[R | R ≤ VaR_α]

        Per the 2026-05-16 metrics research dive: coherent (Acerbi-Tasche
        2002), tail-aware, and Basel III FRTB standard. The dive
        explicitly recommends `ES_97.5 replacing VaR` everywhere in the
        Layer 2 portfolio-health dashboard.

        Convention: returned value is NEGATIVE for typical loss-tail input.
        ES_0.975 ≈ -3% means "in the worst 2.5% of periods, average loss is 3%."

        Args:
            returns: per-period (typically daily) return series
            confidence: confidence level; standard FRTB choice is 0.975

        Returns:
            Float; negative for typical loss-tail returns. Returns 0.0 for
            empty input or fully-clean (no losses below threshold) data.

        Reference: Acerbi, C., & Tasche, D. (2002). "On the Coherence of
        Expected Shortfall." Journal of Banking & Finance 26(7): 1487-1503.
        BCBS d352 (2016). "Minimum capital requirements for market risk."
        """
        if returns is None or len(returns) == 0:
            return 0.0
        threshold = float(np.percentile(returns, 100 * (1 - confidence)))
        tail = returns[returns <= threshold]
        if tail.empty:
            return float(threshold)
        return float(tail.mean())

    @staticmethod
    def conditional_drawdown_at_risk(
        equity_curve: pd.Series, alpha: float = 0.95
    ) -> float:
        """Conditional Drawdown at Risk (CDaR) — the average of the worst
        (1−α)·100% drawdowns.

        Per Chekhlov-Uryasev-Zabarankin (2005, IJTAF 8(1):13-58): unlike
        raw Max Drawdown (a single-realization point estimate of a sup-
        statistic), CDaR is **LP-tractable and convex in portfolio weights**.
        Per the 2026-05-16 metrics dive: "the right drawdown constraint for
        optimization" — replaces raw MDD when Engine C / portfolio optimizer
        needs a drawdown-aware objective.

        Convention: returned value is NEGATIVE (e.g., -0.18 = "average of
        worst 5% of drawdowns is 18%").

        Args:
            equity_curve: equity over time (any starting value)
            alpha: confidence; 0.95 means "worst 5% of drawdowns"

        Returns:
            Float; negative. Returns 0.0 for non-decreasing curves.

        Reference: Chekhlov, A., Uryasev, S., Zabarankin, M. (2005).
        "Drawdown Measure in Portfolio Optimization." International Journal
        of Theoretical and Applied Finance 8(1): 13-58.
        """
        if equity_curve is None or len(equity_curve) < 2:
            return 0.0
        roll_max = equity_curve.cummax()
        drawdowns = (equity_curve - roll_max) / roll_max
        # All drawdowns are ≤ 0; worst (most negative) is the tail
        threshold = float(np.percentile(drawdowns, 100 * (1 - alpha)))
        tail = drawdowns[drawdowns <= threshold]
        if tail.empty:
            return 0.0
        return float(tail.mean())

    @staticmethod
    def effective_number_of_bets(
        weights: pd.Series,
        cov_matrix: pd.DataFrame,
    ) -> float:
        """Meucci's Effective Number of Bets (N_Ent).

        Per Meucci (2009, Risk 22(7):74-79): given a portfolio's weights
        and an asset covariance matrix, decompose total risk into
        principal-portfolio variance contributions, then compute the
        entropy-based diversification statistic:
            p_i = (PC variance contribution of i) / total variance
            N_Ent = exp(− Σ p_i · ln p_i)

        N_Ent = N when every PC contributes equally (perfectly diversified
        risk allocation). N_Ent → 1 when one PC dominates (concentrated
        risk). Per the 2026-05-16 metrics dive: "the right portfolio
        diversification statistic" — rebalance trigger when N_Ent drops
        50% from rolling-12-month median.

        Args:
            weights: pd.Series of portfolio weights, indexed by asset
            cov_matrix: pd.DataFrame of asset covariances; index/columns
                        must match weights.index

        Returns:
            Float in [1, N] where N = len(weights). Returns 0.0 for
            degenerate input (zero total variance, missing alignment).

        Reference: Meucci, A. (2009). "Managing Diversification."
        Risk 22(7): 74-79.
        """
        if weights is None or cov_matrix is None or len(weights) < 2:
            return 0.0
        # Align weights to covariance index
        aligned_weights = weights.reindex(cov_matrix.index).fillna(0.0)
        w = aligned_weights.values.astype(float)
        cov = cov_matrix.values.astype(float)
        # Principal-component decomposition of covariance
        eigvals, eigvecs = np.linalg.eigh(cov)
        # Filter near-zero eigenvalues (numerical noise)
        positive_mask = eigvals > 1e-12
        if not positive_mask.any():
            return 0.0
        eigvals = eigvals[positive_mask]
        eigvecs = eigvecs[:, positive_mask]
        # Project weights into PC space: tilt_i = (eigvec_i^T · w)
        tilt = eigvecs.T @ w
        # PC variance contribution: tilt_i^2 · eigval_i
        pc_var = (tilt ** 2) * eigvals
        total_var = pc_var.sum()
        if total_var <= 0:
            return 0.0
        # Normalize to probabilities
        p = pc_var / total_var
        # Entropy (avoid log(0); zero-probability terms contribute 0 to entropy)
        p_nonzero = p[p > 1e-15]
        entropy = -np.sum(p_nonzero * np.log(p_nonzero))
        return float(np.exp(entropy))
    
    @staticmethod
    def sqn(trades_pnl: pd.Series) -> float:
        """
        System Quality Number (Tharp).
        Expectancy / StdDev * sqrt(N)
        """
        if len(trades_pnl) < 2 or trades_pnl.std() == 0: return 0.0
        return (trades_pnl.mean() / trades_pnl.std()) * np.sqrt(len(trades_pnl))

    @staticmethod
    def kelly_fraction(win_rate: float, win_loss_ratio: float) -> float:
        """
        Kelly = W - (1-W)/R
        """
        if win_loss_ratio == 0: return 0.0
        return win_rate - (1 - win_rate) / win_loss_ratio

    @staticmethod
    def probabilistic_sharpe_ratio(
        returns: pd.Series,
        sr_benchmark_annualized: float = 0.0,
        periods: int = 252,
    ) -> float:
        """
        Probabilistic Sharpe Ratio (Bailey & Lopez de Prado 2012).

        Probability that the true (population) annualized Sharpe ratio
        exceeds ``sr_benchmark_annualized``, accounting for sample size,
        skewness, and excess kurtosis. Output in [0, 1].

        Reference: Bailey, D. and Lopez de Prado, M. (2012),
        "The Sharpe Ratio Efficient Frontier", Journal of Risk 15(2).
        """
        if returns is None or len(returns) < 4:
            return 0.0
        std = float(returns.std(ddof=1))
        if std == 0.0:
            return 0.0
        n = int(len(returns))
        # Non-annualized (per-period) sample Sharpe — formula is on this scale
        sr_hat = float(returns.mean()) / std
        # Convert annualized benchmark to per-period scale
        sr_bench = float(sr_benchmark_annualized) / np.sqrt(periods)
        skew = float(_stats.skew(returns, bias=False))
        # Pearson kurtosis (not excess) — formula uses (γ4 - 1)/4 with γ4 = E[(x-μ)^4/σ^4]
        kurt_pearson = float(_stats.kurtosis(returns, fisher=False, bias=False))
        denom_inner = 1.0 - skew * sr_hat + ((kurt_pearson - 1.0) / 4.0) * (sr_hat ** 2)
        if denom_inner <= 0.0:
            return 0.0
        sigma_sr = np.sqrt(denom_inner / (n - 1))
        if sigma_sr == 0.0:
            return 1.0 if sr_hat > sr_bench else 0.0
        z = (sr_hat - sr_bench) / sigma_sr
        return float(_stats.norm.cdf(z))

    @staticmethod
    def rolling_psr(
        returns: pd.Series,
        window: int = 252,
        sr_benchmark_annualized: float = 0.0,
        periods: int = 252,
    ) -> pd.Series:
        """Rolling Probabilistic Sharpe Ratio over a trailing window.

        Per the 2026-05-16 metrics research dive: rolling-252 PSR is the
        right LIVE-monitoring signal for edge decay. As fresh returns
        arrive, the trailing-N-day PSR-vs-zero (or PSR-vs-deployed-SR)
        gives a continuous probability that the strategy's true Sharpe
        still exceeds the benchmark.

        Combine with CUSUM (below) for a pre-registered decay-kill
        protocol: "kill if rolling-252 PSR drops below 0.5 for ≥60
        consecutive days" (i.e., > 50% chance true Sharpe is now BELOW
        benchmark, sustained).

        Args:
            returns: per-period returns time series with DatetimeIndex
            window: rolling window in periods (252 standard = 1 trading year)
            sr_benchmark_annualized: PSR benchmark (typically 0 for
                "is the true SR above zero", or the deployed SR for
                "is the strategy still beating its in-sample claim")
            periods: annualization factor (252 daily, 12 monthly)

        Returns:
            pd.Series indexed like `returns`, with rolling PSR values.
            First (window-1) entries are NaN.
        """
        if returns is None or len(returns) < window:
            return pd.Series(dtype=float, index=returns.index if returns is not None else None)

        out = pd.Series(np.nan, index=returns.index, dtype=float)
        rets_values = returns.values
        # Iterate windows efficiently — single PSR per window
        for i in range(window - 1, len(returns)):
            window_rets = pd.Series(rets_values[i - window + 1 : i + 1])
            out.iloc[i] = MetricsEngine.probabilistic_sharpe_ratio(
                window_rets,
                sr_benchmark_annualized=sr_benchmark_annualized,
                periods=periods,
            )
        return out

    @staticmethod
    def cusum_decay_monitor(
        returns: pd.Series,
        reference_mean: float,
        reference_std: float,
        k: float = 0.5,
        h: float = 10.0,
    ) -> Dict[str, Any]:
        """CUSUM (Cumulative Sum) decay monitor for edge alpha decay.

        Per the 2026-05-16 metrics research dive: pre-registered decay
        monitor is THE retire-the-edge decision driver. CUSUM is the
        standard sequential-analysis tool from Page (1954); for trading-
        strategy decay use the Page-Hinkley variant. Implementation
        per López de Prado AFML Ch. 17.

        Method:
            standardized r_t = (r_t - μ_ref) / σ_ref
            CUSUM⁺_t = max(0, CUSUM⁺_{t-1} + standardized_r_t - k)
            CUSUM⁻_t = min(0, CUSUM⁻_{t-1} + standardized_r_t + k)

        ``h`` is the alarm threshold. Larger h → fewer false positives,
        slower detection. Per the metrics dive: calibrate h such that
        in-sample produces ~1 false-alarm-per-year. The dive's specific
        rule: "kill if rolling-252 SR drops >2σ below in-sample for
        ≥60 consecutive days" — this CUSUM is the leading-indicator
        complement.

        Args:
            returns: live/OOS per-period returns to monitor
            reference_mean: in-sample mean (pre-registered)
            reference_std: in-sample std (pre-registered)
            k: drift tolerance per standardized observation (default 0.5;
               Page's classic choice)
            h: alarm threshold (default 10; calibrate via in-sample
               false-alarm rate)

        Returns:
            Dict with:
              - "cusum_plus": pd.Series of upward CUSUM (signals positive drift)
              - "cusum_minus": pd.Series of downward CUSUM (signals decay)
              - "decay_alarm_fired": bool, True if CUSUM⁻ ever crossed -h
              - "first_alarm_at": index of first alarm or None
              - "max_cusum_minus": deepest decay accumulated

        Reference:
            - Page, E. S. (1954). "Continuous Inspection Schemes." Biometrika 41.
            - Hinkley, D. V. (1971). "Inference about the change-point..."
            - López de Prado AFML Ch. 17.
        """
        if returns is None or len(returns) == 0:
            return {
                "cusum_plus": pd.Series(dtype=float),
                "cusum_minus": pd.Series(dtype=float),
                "decay_alarm_fired": False,
                "first_alarm_at": None,
                "max_cusum_minus": 0.0,
            }
        if reference_std is None or reference_std <= 1e-12:
            raise ValueError(
                f"reference_std must be > 0 (got {reference_std}); "
                f"in-sample std should be pre-registered"
            )

        standardized = (returns - reference_mean) / reference_std
        cusum_plus = pd.Series(0.0, index=returns.index, dtype=float)
        cusum_minus = pd.Series(0.0, index=returns.index, dtype=float)
        first_alarm = None
        cp = 0.0
        cm = 0.0
        for i, r in enumerate(standardized.values):
            cp = max(0.0, cp + float(r) - k)
            cm = min(0.0, cm + float(r) + k)
            cusum_plus.iloc[i] = cp
            cusum_minus.iloc[i] = cm
            if first_alarm is None and cm <= -h:
                first_alarm = returns.index[i]

        return {
            "cusum_plus": cusum_plus,
            "cusum_minus": cusum_minus,
            "decay_alarm_fired": first_alarm is not None,
            "first_alarm_at": first_alarm,
            "max_cusum_minus": float(cusum_minus.min()),
        }

    @staticmethod
    def deflated_sharpe_ratio(
        returns: pd.Series,
        n_trials: int,
        periods: int = 252,
    ) -> float:
        """
        Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014).

        PSR with the benchmark set to ``E[max SR_i]`` under the null of
        ``n_trials`` independent strategies, correcting for selection bias
        from multiple testing. Output in [0, 1].

        Variance of trial Sharpes is approximated from the observed series'
        standard error of SR (per Bailey-Lopez de Prado closed-form).

        Reference: Bailey, D. and Lopez de Prado, M. (2014), "The Deflated
        Sharpe Ratio", Journal of Portfolio Management 40(5).
        """
        if returns is None or len(returns) < 4 or n_trials < 1:
            return 0.0
        n = int(len(returns))
        # Variance of SR across the trials, approximated by the per-period
        # SR standard error of the observed series
        std = float(returns.std(ddof=1))
        if std == 0.0:
            return 0.0
        sr_hat = float(returns.mean()) / std
        skew = float(_stats.skew(returns, bias=False))
        kurt_pearson = float(_stats.kurtosis(returns, fisher=False, bias=False))
        denom_inner = 1.0 - skew * sr_hat + ((kurt_pearson - 1.0) / 4.0) * (sr_hat ** 2)
        if denom_inner <= 0.0:
            return 0.0
        v_sr = denom_inner / (n - 1)
        sigma_sr = np.sqrt(v_sr)
        if n_trials == 1:
            sr_zero = 0.0  # No selection bias to correct for
        else:
            # Expected max of n_trials i.i.d. standard normals (per BLdP):
            # E[max] ≈ (1 - γ) Φ⁻¹(1 - 1/N) + γ Φ⁻¹(1 - 1/(N e))
            phi_inv_a = float(_stats.norm.ppf(1.0 - 1.0 / n_trials))
            phi_inv_b = float(_stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e)))
            sr_zero_per_period = sigma_sr * (
                (1.0 - _EULER_GAMMA) * phi_inv_a + _EULER_GAMMA * phi_inv_b
            )
            sr_zero = sr_zero_per_period * np.sqrt(periods)  # annualize
        return MetricsEngine.probabilistic_sharpe_ratio(
            returns, sr_benchmark_annualized=sr_zero, periods=periods
        )

    @staticmethod
    def probability_of_backtest_overfitting(
        trial_matrix: pd.DataFrame,
        n_partitions: int = 16,
        rank_metric: str = "sharpe",
    ) -> Dict[str, float]:
        """Probability of Backtest Overfitting via Combinatorially Symmetric
        Cross-Validation (CSCV).

        Bailey, D., Borwein, J., López de Prado, M., Zhu, Q. (2017).
        "The Probability of Backtest Overfitting." Journal of Computational
        Finance 20(4): 39-69.

        Model-free overfitting check, complementary to the parametric DSR.
        Where DSR asks "is this Sharpe surprising given N trials and the
        observed series' moments?", PBO asks "in how many IS/OOS partitions
        does the in-sample-best strategy under-perform the OOS median?"

        Method:
          1. Partition T observations into S submatrices (rows).
          2. For each combination of S/2 submatrices chosen IS (the other
             S/2 are OOS): compute per-trial ranking metric IS + OOS.
          3. Identify the IS-optimal trial. Look up its OOS rank.
          4. PBO = fraction of partitions where the IS-optimal trial's OOS
             rank is BELOW the median.

        Interpretation:
          PBO ≈ 0.5 → IS-best is random on OOS (no edge, just noise)
          PBO < 0.5 → IS-best tends to beat OOS median (sign of real edge)
          PBO > 0.5 → IS-best tends to UNDER-perform OOS (overfit)
          Deploy threshold: PBO < 0.5, preferably < 0.3.

        Args:
            trial_matrix: T×N pandas DataFrame where T=time periods (rows),
                          N=trial configurations (columns). Cell value =
                          per-period return of trial N at time T.
            n_partitions: S, must be EVEN. Default 16 (canonical).
            rank_metric: "sharpe" (default; mean/std × √periods proxy) or
                         "mean" (simple mean return).

        Returns:
            Dict with:
              - "pbo": the PBO value in [0, 1]
              - "n_combinations": number of IS/OOS partitions evaluated
              - "n_trials": number of trial configurations (columns)
              - "logit_mean": mean of logit(rank_oos / (N+1)) across combos
                             (López de Prado's secondary diagnostic)

        Caveats:
          - Sensitive to S; report it. S=16 standard; S=4 unstable; S=32
            may need more data.
          - Gameable by adding dilutive trial columns. Honest N matters.
          - Doesn't catch look-ahead bias / regime mismatch / wrong universe.

        Reference: Bailey, Borwein, López de Prado, Zhu (2017) JoCF 20(4).
        Python implementation guidance: https://github.com/esvhd/pypbo
        (Stable but not used directly — this implementation is self-contained.)
        """
        from itertools import combinations
        if not isinstance(trial_matrix, pd.DataFrame):
            raise TypeError("trial_matrix must be a pandas DataFrame")
        if n_partitions < 4 or n_partitions % 2 != 0:
            raise ValueError(f"n_partitions must be EVEN and >= 4 (got {n_partitions})")
        T, N = trial_matrix.shape
        if T < n_partitions * 2:
            # Not enough observations per partition for stable metric estimation
            return {"pbo": float("nan"), "n_combinations": 0, "n_trials": N,
                    "logit_mean": float("nan"),
                    "error": f"T={T} too small for S={n_partitions} (need T >= 2S)"}
        if N < 2:
            return {"pbo": float("nan"), "n_combinations": 0, "n_trials": N,
                    "logit_mean": float("nan"),
                    "error": "need >= 2 trials to rank"}

        # Step 1: partition T into S submatrices of (nearly) equal length
        rows_per_partition = T // n_partitions
        partitions: list[pd.DataFrame] = []
        for s in range(n_partitions):
            start = s * rows_per_partition
            end = (s + 1) * rows_per_partition if s < n_partitions - 1 else T
            partitions.append(trial_matrix.iloc[start:end].copy())

        def _metric(submatrix: pd.DataFrame) -> pd.Series:
            """Per-trial ranking metric across a submatrix's rows."""
            if rank_metric == "sharpe":
                mean = submatrix.mean(axis=0)
                std = submatrix.std(axis=0, ddof=1)
                # Use tolerance, not == 0, to handle near-flat columns
                std = std.where(std > 1e-12, 1e-12)
                return mean / std
            elif rank_metric == "mean":
                return submatrix.mean(axis=0)
            else:
                raise ValueError(f"Unknown rank_metric: {rank_metric}")

        # Step 2: enumerate all C(S, S/2) combinations of IS submatrix indices
        all_indices = list(range(n_partitions))
        is_combinations = list(combinations(all_indices, n_partitions // 2))

        n_below_median = 0
        logits: list[float] = []
        for is_indices in is_combinations:
            oos_indices = [i for i in all_indices if i not in is_indices]
            is_submatrix = pd.concat([partitions[i] for i in is_indices], axis=0)
            oos_submatrix = pd.concat([partitions[i] for i in oos_indices], axis=0)

            is_scores = _metric(is_submatrix)
            oos_scores = _metric(oos_submatrix)

            # IS-optimal trial
            is_optimal_trial = is_scores.idxmax()

            # OOS rank of that trial (1 = best, N = worst); rank descending
            oos_ranks = oos_scores.rank(ascending=False, method="average")
            rank_of_is_optimal = oos_ranks.loc[is_optimal_trial]
            median_rank = (N + 1) / 2.0
            if rank_of_is_optimal > median_rank:
                n_below_median += 1

            # López de Prado's secondary diagnostic: logit(rank / (N+1))
            normalized_rank = rank_of_is_optimal / (N + 1.0)
            # Clip to (epsilon, 1 - epsilon) to keep logit finite
            eps = 1e-9
            normalized_rank = float(min(max(normalized_rank, eps), 1.0 - eps))
            logits.append(float(np.log(normalized_rank / (1.0 - normalized_rank))))

        n_combos = len(is_combinations)
        pbo = n_below_median / n_combos
        logit_mean = float(np.mean(logits)) if logits else float("nan")

        return {
            "pbo": float(pbo),
            "n_combinations": int(n_combos),
            "n_trials": int(N),
            "logit_mean": logit_mean,
            "n_partitions": int(n_partitions),
            "deploy_threshold_met": bool(pbo < 0.5),
            "deploy_threshold_strict": bool(pbo < 0.3),
        }

    @staticmethod
    def information_ratio(
        strategy_rets: pd.Series,
        benchmark_rets: pd.Series,
        periods: int = 252,
    ) -> float:
        """
        Information Ratio: annualized active-return / tracking error.

        IR = mean(strat_ret - bench_ret) / std(strat_ret - bench_ret) * sqrt(periods)

        The right metric for "beat the benchmark significantly" — Sharpe
        confounds market exposure with skill; IR isolates the active component.
        """
        if strategy_rets is None or benchmark_rets is None:
            return 0.0
        active = (strategy_rets - benchmark_rets).dropna()
        if len(active) < 2 or active.std(ddof=1) == 0.0:
            return 0.0
        return float(active.mean() / active.std(ddof=1) * np.sqrt(periods))

    @staticmethod
    def tail_ratio(returns: pd.Series, percentile: float = 0.05) -> float:
        """
        Tail Ratio: |avg of top tail| / |avg of bottom tail|.

        > 1.0 means right tail is fatter than left (good for asymmetric-upside).
        < 1.0 means left tail is fatter (negative skew; common in momentum strategies).

        ``percentile`` is each tail's mass (default 5%, so top 5% vs bottom 5%).
        """
        if returns is None or len(returns) < int(1 / max(percentile, 1e-9)):
            return 0.0
        upper = returns.quantile(1.0 - percentile)
        lower = returns.quantile(percentile)
        top_tail = returns[returns >= upper]
        bot_tail = returns[returns <= lower]
        if bot_tail.empty or top_tail.empty:
            return 0.0
        bot_mean = bot_tail.mean()
        if bot_mean == 0.0:
            return 0.0
        return float(abs(top_tail.mean()) / abs(bot_mean))

    @staticmethod
    def skewness(returns: pd.Series) -> float:
        """Sample skewness (γ_3) — flags asymmetric return distributions."""
        if returns is None or len(returns) < 3:
            return 0.0
        return float(_stats.skew(returns, bias=False))

    @staticmethod
    def excess_kurtosis(returns: pd.Series) -> float:
        """
        Excess kurtosis (Fisher; normal distribution → 0).

        Positive = fat tails, negative = thin tails. Important for any
        strategy whose Sharpe assumes Gaussian returns.
        """
        if returns is None or len(returns) < 4:
            return 0.0
        return float(_stats.kurtosis(returns, fisher=True, bias=False))

    @staticmethod
    def ulcer_index(equity_curve: pd.Series) -> float:
        """
        Ulcer Index (Martin & McCann): RMS of percent drawdowns.

        Captures both depth AND duration of drawdowns, unlike max_drawdown
        which is depth-only. Better aligned with the psychological pain of
        being underwater for extended periods.
        """
        if equity_curve is None or len(equity_curve) < 2:
            return 0.0
        roll_max = equity_curve.cummax()
        drawdown_pct = (equity_curve - roll_max) / roll_max * 100.0
        return float(np.sqrt((drawdown_pct ** 2).mean()))

    @staticmethod
    def bootstrap_distribution(
        returns: pd.Series,
        metric_fn,
        n_iterations: int = 1000,
        block_length: Optional[int] = None,
        seed: int = 0,
        confidence: float = 0.95,
    ) -> Dict[str, float]:
        """Stationary block-bootstrap distribution of an arbitrary metric.

        Parameters
        ----------
        returns : pd.Series
            Per-period returns (daily, weekly, etc.). Must contain at least
            ``2 * block_length`` observations.
        metric_fn : callable
            ``returns -> float``. Examples: ``MetricsEngine.sharpe_ratio``,
            ``lambda r: MetricsEngine.sortino_ratio(r)``,
            ``lambda r: MetricsEngine.tail_ratio(r)``.
        n_iterations : int
            Bootstrap resamples (default 1000).
        block_length : int, optional
            Block length for the moving-block bootstrap. None → automatic
            ``max(5, int(n ** (1/3)))`` per Politis-White rule of thumb.
        seed : int
            RNG seed for reproducibility.
        confidence : float
            Two-sided confidence level (default 0.95).

        Returns
        -------
        dict
            Keys: ``point_estimate`` (metric on full series),
            ``mean`` / ``std`` / ``median`` (bootstrap distribution moments),
            ``ci_low`` / ``ci_high`` (two-sided percentile CI),
            ``p_above_zero`` (fraction of bootstrap samples > 0),
            ``n_iterations`` / ``block_length`` (bookkeeping).

        Why block bootstrap vs iid: financial returns exhibit serial
        correlation (volatility clustering, momentum auto-correlation).
        Iid resampling breaks that structure → CI widths are
        underestimated. Block bootstrap preserves short-range dependence
        within each block.
        """
        if returns is None or len(returns) < 4:
            return {
                "point_estimate": 0.0,
                "mean": 0.0,
                "std": 0.0,
                "median": 0.0,
                "ci_low": 0.0,
                "ci_high": 0.0,
                "p_above_zero": 0.0,
                "n_iterations": 0,
                "block_length": 0,
            }

        n = len(returns)
        if block_length is None:
            block_length = max(5, int(round(n ** (1.0 / 3.0))))
        block_length = max(1, min(block_length, n))

        rng = np.random.default_rng(seed)
        # Number of blocks per resample so the resampled series is at least
        # as long as the original. Excess is trimmed back to n.
        n_blocks = int(np.ceil(n / block_length))

        ret_arr = np.asarray(returns, dtype=float)
        # Cache the index for converting bootstrap arrays back to Series so
        # metric_fn can use any index-aware operations (e.g. cagr looks at
        # the time delta).
        idx = returns.index

        samples = np.empty(n_iterations, dtype=float)
        for i in range(n_iterations):
            # Random block start positions in [0, n - block_length].
            # Wrap-around is intentionally NOT used; this is the classic
            # moving-block bootstrap of Künsch (1989).
            max_start = max(0, n - block_length)
            starts = rng.integers(0, max_start + 1, size=n_blocks)
            chunks = [ret_arr[s:s + block_length] for s in starts]
            boot = np.concatenate(chunks)[:n]
            samples[i] = float(metric_fn(pd.Series(boot, index=idx)))

        point = float(metric_fn(returns))
        alpha = (1.0 - confidence) / 2.0
        ci_low = float(np.percentile(samples, 100.0 * alpha))
        ci_high = float(np.percentile(samples, 100.0 * (1.0 - alpha)))
        # Robust to non-finite values produced by a degenerate metric_fn
        finite = samples[np.isfinite(samples)]
        if finite.size == 0:
            mean = std = median = 0.0
            p_above = 0.0
        else:
            mean = float(np.mean(finite))
            std = float(np.std(finite, ddof=1)) if finite.size > 1 else 0.0
            median = float(np.median(finite))
            p_above = float((finite > 0).mean())

        return {
            "point_estimate": point,
            "mean": mean,
            "std": std,
            "median": median,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "p_above_zero": p_above,
            "n_iterations": int(n_iterations),
            "block_length": int(block_length),
        }
