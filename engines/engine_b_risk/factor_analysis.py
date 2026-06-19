# -------------------------------------------------------------------
# Engine B (Extension): Factor Risk Model
# -------------------------------------------------------------------
# A proprietary risk model used to decompose portfolio risk into
# systematic factors (Beta, Momentum, Size, Value, Volatility).
# 
# Used by the Optimizer to enforce Factor Neutrality if requested.
# -------------------------------------------------------------------

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional

# T-2026-06-18-209: map the Fama-French/Mom factor codes (the columns
# core/factor_decomposition serves from cached Ken-French data) to the
# intuitive Barra-lite labels the diagnostic reports.
FACTOR_LABELS = {
    "MktRF": "market", "SMB": "size", "HML": "value",
    "RMW": "quality", "CMA": "investment", "Mom": "momentum",
}
# |t| threshold for an intercept to count as "significant" alpha (≈ 2-sigma).
ALPHA_T_SIGNIF = 2.0


@dataclass
class FactorDecompResult:
    """Book/strategy-level factor decomposition (the 'beta or edge?' answer).

    `alpha_t_hac` is sourced from `core.factor_decomposition` so it inherits
    C/T-203's OLS→HAC fix automatically. `beta_tstats` are computed module-side
    via a dependency-free Newey-West HAC (core's FactorDecomp does not expose
    per-coefficient SEs); they are descriptive — the verdict keys off the alpha.
    """
    alpha_annualized: float
    alpha_t_hac: float
    betas: Dict[str, float]            # intuitive-label -> beta
    beta_tstats: Dict[str, float]      # intuitive-label -> t (module-local HAC)
    r2: float
    residual_vol: float                # annualized idiosyncratic vol
    n_obs: int
    raw_sharpe: float

    def is_it_beta_or_edge(self) -> str:
        """One-line verdict. Significant positive HAC alpha ⇒ edge candidate;
        else the result is explained by factor beta (no orthogonal edge)."""
        if self.alpha_t_hac >= ALPHA_T_SIGNIF and self.alpha_annualized > 0:
            return "edge-candidate"
        return "beta"


def _newey_west_tstats(y: np.ndarray, X_design: np.ndarray, lags: int) -> np.ndarray:
    """Newey-West HAC t-stats for every coefficient of OLS y ~ X_design.

    Dependency-free (numpy only) so the diagnostic carries no statsmodels
    requirement and matches core/factor_decomposition's lstsq style. Used only
    for the descriptive per-beta t-stats; the headline alpha t-stat comes from
    the core API (which inherits T-203's HAC fix)."""
    n, k = X_design.shape
    beta, _, _, _ = np.linalg.lstsq(X_design, y, rcond=None)
    resid = y - X_design @ beta
    XtX_inv = np.linalg.pinv(X_design.T @ X_design)
    # NW HAC meat: S0 + sum_{l=1..L} w_l (Γ_l + Γ_l'), Bartlett weights.
    S = (X_design * resid[:, None]).T @ (X_design * resid[:, None])
    for l in range(1, lags + 1):
        w = 1.0 - l / (lags + 1.0)
        u = X_design * resid[:, None]
        G = u[l:].T @ u[:-l]
        S += w * (G + G.T)
    cov = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(se > 0, beta / se, 0.0)
    return t


class FactorRiskModel:
    """
    Computes factor exposures for a universe of assets.
    Factors:
    - Market (SPY Beta)
    - Momentum (12M-1M return)
    - Volatility (IDIO Vol)
    """

    def __init__(self, benchmark_ticker="SPY"):
        self.benchmark = benchmark_ticker

    # ------------------------------------------------------------------ #
    # T-2026-06-18-209: the reusable DIAGNOSTIC — decompose ANY strategy's
    # daily return series into factor exposures + residual alpha (HAC), the
    # "is this beta or genuine edge?" backbone for evaluating Phase-1
    # compositions. CONSUMES core/factor_decomposition (does NOT fork it) so
    # the alpha t-stat inherits C/T-203's OLS→HAC fix the moment it merges.
    # This is MEASUREMENT only — it reads returns, reports exposures; it does
    # NOT touch risk sizing, portfolio_engine, or any Engine-B flag.
    # ------------------------------------------------------------------ #
    def decompose(
        self,
        returns: pd.Series,
        edge_name: str = "?",
        factor_cols: Optional[List[str]] = None,
    ) -> Optional[FactorDecompResult]:
        """Regress a daily return series on FF5+Mom (cached Ken-French) and
        return the factor betas + residual alpha (HAC t) + R² + residual vol.

        Returns None if the overlap with the factor history is too short
        (mirrors the core API's degenerate-regression guard)."""
        from core.factor_decomposition import (
            load_factor_data, regress_returns_on_factors, DEFAULT_FACTOR_COLS,
        )
        factors = load_factor_data()
        decomp = regress_returns_on_factors(
            returns, factors, factor_cols=factor_cols, edge_name=edge_name,
        )
        if decomp is None:
            return None

        # residual (idiosyncratic) vol from R² — no second regression needed:
        # var(resid) = var(returns) · (1 - R²).
        ann_vol = float(returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0
        residual_vol = ann_vol * float(np.sqrt(max(0.0, 1.0 - decomp.r_squared)))

        # per-beta HAC t-stats (module-local; core does not expose them).
        cols = list(decomp.betas.keys())
        beta_t: Dict[str, float] = {}
        try:
            aligned = pd.concat(
                [returns.rename("r"), factors], axis=1, join="inner",
            ).dropna()
            if len(aligned) > len(cols) + 2:
                excess = (aligned["r"] - aligned["RF"]).values
                Xd = np.hstack([np.ones((len(excess), 1)), aligned[cols].values])
                lags = max(1, int(len(excess) ** 0.25))
                ts = _newey_west_tstats(excess, Xd, lags)
                beta_t = {cols[i]: float(ts[i + 1]) for i in range(len(cols))}
        except Exception:
            beta_t = {}

        return FactorDecompResult(
            alpha_annualized=decomp.alpha_annualized,
            alpha_t_hac=decomp.alpha_tstat,  # inherits C/T-203's HAC fix
            betas={FACTOR_LABELS.get(k, k): v for k, v in decomp.betas.items()},
            beta_tstats={FACTOR_LABELS.get(k, k): beta_t.get(k, float("nan")) for k in cols},
            r2=decomp.r_squared,
            residual_vol=residual_vol,
            n_obs=decomp.n_obs,
            raw_sharpe=decomp.raw_sharpe,
        )
        
    # ------------------------------------------------------------------ #
    # SIZING-INTEGRATION HOOK — PROPOSE-FIRST, NOT WIRED (T-206 design §4).
    # The diagnostic above answers "beta or edge?"; the SIZING use of the same
    # exposures (factor-neutrality constraints, per-factor |β| caps, factor-
    # covariance VaR/ES, regime-gated tightening on the validated HMM p_crisis)
    # is a SEPARATE director-gated Engine-B build. It is deliberately NOT
    # implemented here: this module must not change risk sizing / portfolio_engine
    # / any Engine-B flag (it is measurement-only). When that PR is approved, it
    # consumes `compute_exposures` (per-asset β) + the book equity and projects
    # the target book onto the factor caps as a risk OVERLAY (vol-target / kill-
    # switch still bind; vol-target is never a risk override). See
    # docs/Audit/factor_risk_model_design_t206_2026_06_18.md §4 for the contract.
    # ------------------------------------------------------------------ #

    def compute_exposures(self, price_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Returns a DataFrame of factor loadings (Tickers x Factors).
        """
        exposures = {}
        
        spy = price_data.get(self.benchmark)
        if spy is None:
            return pd.DataFrame()
            
        spy_ret = spy["Close"].pct_change().dropna()
        
        for tkr, df in price_data.items():
            if tkr == self.benchmark: continue
            if df.empty or len(df) < 60: continue
            
            ret = df["Close"].pct_change().dropna()
            
            # Align
            common = ret.index.intersection(spy_ret.index)
            if len(common) < 30: continue
            
            y = ret.loc[common]
            X = spy_ret.loc[common]
            
            # 1. Market Beta
            try:
                cov = np.cov(y, X)[0, 1]
                var = np.var(X)
                beta = cov / var
            except:
                beta = 1.0
                
            # 2. Momentum (12-1 Return)
            # Simple proxy: last 126 days return
            mom = (df["Close"].iloc[-1] / df["Close"].iloc[0]) - 1.0
            
            # 3. Size (Log Price as proxy if MarketCap unavailable)
            size = np.log(df["Close"].iloc[-1] * df["Volume"].iloc[-20:].mean())
            
            exposures[tkr] = {
                "beta": beta,
                "momentum": mom,
                "size_proxy": size
            }
            
        df_exp = pd.DataFrame.from_dict(exposures, orient='index')
        
        # Z-Score Normalize
        return (df_exp - df_exp.mean()) / df_exp.std()
