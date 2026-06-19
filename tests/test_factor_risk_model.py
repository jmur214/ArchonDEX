"""T-2026-06-18-209 — reusable FactorRiskModel diagnostic.

Synthetic-truth tests: a known-beta series recovers the beta with no alpha;
pure noise shows no significant alpha; an injected drift is flagged as an
edge-candidate. Uses the cached Ken-French factors (offline) via the core API.
"""
import numpy as np
import pandas as pd
import pytest

from engines.engine_b_risk.factor_analysis import FactorRiskModel

core_fd = pytest.importorskip("core.factor_decomposition")


@pytest.fixture(scope="module")
def factors():
    try:
        f = core_fd.load_factor_data(auto_download=False)
    except FileNotFoundError:
        pytest.skip("Ken-French factor cache absent (offline test env)")
    return f


def _series_from(factors, fn):
    """Build a daily return Series aligned to the factor index from fn(row)."""
    idx = factors.index
    vals = [fn(factors.loc[d]) for d in idx]
    return pd.Series(vals, index=idx, name="r")


def test_recovers_known_beta(factors):
    # returns = RF + 1.5*MktRF + tiny noise  → market beta ≈ 1.5, no alpha
    rng = np.random.default_rng(0)
    noise = pd.Series(rng.normal(0, 1e-4, len(factors)), index=factors.index)
    r = factors["RF"] + 1.5 * factors["MktRF"] + noise
    res = FactorRiskModel().decompose(r, edge_name="known_beta")
    assert res is not None
    assert abs(res.betas["market"] - 1.5) < 0.05, res.betas
    assert res.is_it_beta_or_edge() == "beta"           # no injected alpha
    assert res.r2 > 0.9                                  # ~all variance is MktRF
    assert res.beta_tstats["market"] > 10                # strongly significant beta


def test_pure_noise_no_alpha(factors):
    rng = np.random.default_rng(42)
    r = factors["RF"] + pd.Series(rng.normal(0, 0.01, len(factors)), index=factors.index)
    res = FactorRiskModel().decompose(r, edge_name="noise")
    assert res is not None
    assert abs(res.alpha_t_hac) < 2.0                    # no significant alpha
    assert res.is_it_beta_or_edge() == "beta"
    assert abs(res.betas["market"]) < 0.15               # ~no factor loading


def test_true_alpha_detected(factors):
    # RF + market beta 1.0 + a steady +0.0008/day (~20%/yr) drift → real alpha
    rng = np.random.default_rng(7)
    noise = pd.Series(rng.normal(0, 5e-4, len(factors)), index=factors.index)
    r = factors["RF"] + 1.0 * factors["MktRF"] + 0.0008 + noise
    res = FactorRiskModel().decompose(r, edge_name="alpha")
    assert res is not None
    assert res.alpha_annualized > 0.10                   # ~20%/yr injected
    assert res.alpha_t_hac >= 2.0                         # significant
    assert res.is_it_beta_or_edge() == "edge-candidate"


def test_api_shape(factors):
    r = factors["RF"] + factors["MktRF"]
    res = FactorRiskModel().decompose(r)
    assert res is not None
    for f in ("market", "size", "value", "quality", "momentum"):
        assert f in res.betas
    assert res.residual_vol >= 0.0
    assert res.n_obs > 100
    assert res.is_it_beta_or_edge() in ("beta", "edge-candidate")
