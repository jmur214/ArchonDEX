"""HMM production repoint (2026-08-26) — the properties that made it safe,
plus the two defects the verification surfaced.

The repoint swaps config/regime_settings.json's model_path from the superseded
hmm_3state_v1.pkl to the validated hmm_3state_crisis_v1.pkl. These tests lock the
reasons that swap is drop-in, and pin the blindness/coin-flip findings so they
cannot be quietly forgotten.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
MODELS = REPO / "engines/engine_e_regime/models"
OLD, NEW = MODELS / "hmm_3state_v1.pkl", MODELS / "hmm_3state_crisis_v1.pkl"


def _artifact(p):
    with open(p, "rb") as f:
        return pickle.load(f)


# ---- why the swap is drop-in ------------------------------------------------

def test_both_models_carry_byte_identical_feature_names():
    """The reason feature_set='legacy' did NOT need to change. If a future model
    changes its feature contract, this test fails and the repoint must revisit
    the panel wiring rather than silently feeding the wrong columns."""
    assert _artifact(OLD).feature_names == _artifact(NEW).feature_names


def test_state_index_order_DIFFERS_between_the_models():
    """The trap this repoint had to clear: index 0 is 'crisis' in the old model
    and 'stressed' in the new one. Anything reading posteriors by INDEX would
    silently invert crisis/stressed on the swap."""
    assert _artifact(OLD).state_label_for_idx != _artifact(NEW).state_label_for_idx
    assert set(_artifact(OLD).state_label_for_idx) == set(_artifact(NEW).state_label_for_idx)


def test_classifier_returns_LABEL_keyed_posteriors_so_reordering_is_safe():
    """...and the reason it is safe: the classifier keys by label at its own
    boundary, so no consumer ever sees a raw state index."""
    from engines.engine_e_regime.hmm_classifier import HMMRegimeClassifier
    clf = HMMRegimeClassifier.load(NEW)
    import pandas as pd
    row = pd.Series({c: 0.0 for c in clf.feature_names}, name=pd.Timestamp("2024-06-03"))
    proba = clf.predict_proba_at(row)
    assert set(proba) == {"crisis", "stressed", "benign"}


def test_production_config_points_at_the_validated_model():
    cfg = json.loads((REPO / "config/regime_settings.json").read_text())
    assert cfg["hmm"]["model_path"].endswith("hmm_3state_crisis_v1.pkl")
    assert cfg["hmm"]["feature_set"] == "legacy"


# ---- FINDING 1: the HMM is structurally blind before ~2020-05 ---------------

def test_missing_feature_yields_a_uniform_posterior_that_does_NOT_announce_itself():
    """`[NN-FAIL-CLOSED]` defect, pinned. A NaN in any of the 7 features makes
    predict_proba_at return a UNIFORM posterior — indistinguishable from genuine
    maximum uncertainty. Nothing sets degraded=True and the backtest census does
    not count it (census counts macro_regime, not the HMM).

    This test documents CURRENT behavior. When the fail-closed fix lands, this
    test SHOULD fail — that is the point; update it then.
    """
    import pandas as pd
    from engines.engine_e_regime.hmm_classifier import HMMRegimeClassifier
    clf = HMMRegimeClassifier.load(NEW)
    row = pd.Series({c: 0.0 for c in clf.feature_names}, name=pd.Timestamp("2020-03-16"))
    row.iloc[2] = np.nan                      # tlt_ret_20d — the one that is 82% missing
    proba = clf.predict_proba_at(row)
    assert pytest.approx(1 / 3, abs=1e-9) == proba["crisis"]
    assert len(set(round(v, 12) for v in proba.values())) == 1, "uniform == 'no information'"


def test_the_truncated_TLT_source_is_the_cause_and_deep_history_exists_on_disk():
    """The blindness is a REPOINT problem, not a missing-data problem: the panel
    loads data/processed/TLT_1d.csv (starts 2020-04) while a TR-reconciled TLT
    going back to 2005 already sits in the repo."""
    import pandas as pd
    sp = REPO / "data/processed/TLT_1d.csv"
    dp = REPO / "data/processed/tr_reconciled/TLT_1d.csv"
    if not (sp.exists() and dp.exists()):
        pytest.skip("TLT price data not on disk in this env")   # repo convention for data deps
    short = pd.read_csv(sp, index_col=0, parse_dates=True)
    deep = pd.read_csv(dp, index_col=0, parse_dates=True)
    assert short.index.min().year >= 2020
    assert deep.index.min().year <= 2005
    assert len(deep) > 3 * len(short)


# ---- FINDING 2: p_crisis ALONE is a coin flip on the new model --------------

def test_t103_prestated_that_the_repoint_is_justified_on_COMBINED_not_p_crisis():
    """T-103 pre-stated the scope of its own verdict. Shelf entries described as
    '`hmm_p_crisis`-gated' would, on this model, be gated on OOS AUC 0.497 — a
    coin flip. The validated signal is p_crisis + p_stressed (0.914, ci_low 0.880).
    Pinned so the distinction survives into whoever arms the shelf."""
    m = json.loads((REPO / "docs/Measurements/2026-06/hmm_crisis_validation_t103.json").read_text())
    oos = m["auc_by_window"]["oos"]
    p_crisis = oos["horizon_5d_hmm_p_crisis"]["auc_point"]
    combined = oos["horizon_5d_hmm_p_crisis_or_stressed"]["auc_point"]
    assert p_crisis < 0.55, "p_crisis alone is not better than chance OOS"
    assert combined > 0.90 and oos["horizon_5d_hmm_p_crisis_or_stressed"]["auc_ci_low"] > 0.87


# ---- the 2026-08-26 substrate repoint (macro_features) ----------------------

def test_feature_panel_prefers_the_deeper_substrate_per_ticker():
    """The fix for the blindness: `_safe_load_price_csv` takes tr_reconciled ONLY
    when the flat copy is materially shallower, so properly-backfilled tickers
    (SPY: 1993) keep their depth and the trained model's feature distribution
    moves as little as possible."""
    import engines.engine_e_regime.macro_features as mf
    root = REPO
    if not (root / "data/processed/tr_reconciled/TLT_1d.csv").exists():
        pytest.skip("price data not on disk in this env")
    tlt = mf._safe_load_price_csv("TLT", root)
    spy = mf._safe_load_price_csv("SPY", root)
    assert tlt is not None and spy is not None
    assert tlt.index.min().year <= 2006, "TLT must now reach back past the 2020-04 truncation"
    assert spy.index.min().year <= 1995, "SPY must KEEP its deeper flat-copy history"


def test_the_hmm_can_now_see_the_gfc_at_all():
    """The blindness, closed. Before the repoint every pre-2020-05 bar returned a
    uniform posterior; the GFC peak must now produce an actual classification."""
    import engines.engine_e_regime.macro_features as mf
    import pandas as pd
    from engines.engine_e_regime.hmm_classifier import HMMRegimeClassifier
    if not (REPO / "data/processed/tr_reconciled/TLT_1d.csv").exists():
        pytest.skip("price data not on disk in this env")
    panel = mf.build_feature_panel(include_aux=False)
    assert panel["tlt_ret_20d"].isna().mean() < 0.50, "tlt_ret_20d was 82% NaN before the repoint"
    clf = HMMRegimeClassifier.load(NEW)
    row = mf.latest_feature_row(panel, pd.Timestamp("2008-10-15"))
    proba = clf.predict_proba_at(row, history_panel=panel)
    assert max(proba.values()) > 0.5, f"still uniform/blind at the GFC peak: {proba}"
    assert max(proba, key=proba.get) in ("crisis", "stressed")
