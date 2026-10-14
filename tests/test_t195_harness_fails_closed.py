"""RR-1 §6.6 — the T-195 foundry harness FAILS CLOSED on its feature selection.

Before the fix, an id in T195_FEATURES that matched nothing shrank the sweep silently; a
sweep of zero features printed "VERDICT: H0 — explored, nothing cleared (honest null)" and
exited 0. The RR-1 RE-SCORE asked for `triple_witching` (the id is
`triple_witching_premium`) and got exactly that: a refutation that never ran.

The refusals are driven through the real entrypoint, `main()`; a refused run must not
restore the governor (it writes live files) or write an output row.

DO NOT REMOVE OR "SIMPLIFY" THE FIXTURE'S STUBS. In every agent worktree `data/processed`
is a symlink into main's tree, so a test that falls through to `DataManager` can write
into EVERY agent's price cache. The stubs make the network and the cache unreachable on
every code path, fixed or regressed. This is not hypothetical: the first reversion run,
without them, fell through on the unfixed harness and began fetching from yfinance
(killed after ~5 min, with nothing in the shared cache changed).
"""
from __future__ import annotations

import importlib
from types import SimpleNamespace

import pandas as pd
import pytest


class _OfflineData:
    def load_cached(self, ticker, timeframe):
        return pd.DataFrame({"Close": [1.0, 1.0]}, index=pd.to_datetime(["2012-01-03", "2012-01-04"]))


@pytest.fixture
def harness(monkeypatch, tmp_path):
    import engines.data_manager.data_manager as dmm
    import engines.engine_d_discovery.discovery as disc
    import orchestration.run_backtest_pure as rbp
    monkeypatch.setattr(dmm, "DataManager", _OfflineData)
    monkeypatch.setattr(disc, "DiscoveryEngine", lambda *a, **k: SimpleNamespace())
    monkeypatch.setattr(rbp, "PureBacktestCache", lambda *a, **k: SimpleNamespace())
    mod = importlib.import_module("scripts.run_foundry_eval_t195")
    restores: list[int] = []
    monkeypatch.setattr(mod, "restore_clean_governor", lambda: restores.append(1))
    monkeypatch.setattr(mod, "OUT", str(tmp_path / "rows.jsonl"))
    return mod, restores, tmp_path / "rows.jsonl"


def _feat(fid: str, tier: str = "A") -> SimpleNamespace:
    return SimpleNamespace(feature_id=fid, tier=tier)


@pytest.mark.parametrize("only", [["triple_witching"], ["triple_witching_premium", "january"]])
def test_unknown_feature_id_exits_2_with_no_side_effects(harness, monkeypatch, only):
    mod, restores, out = harness
    monkeypatch.setattr(mod, "ONLY", only)
    assert mod.main() == 2
    assert restores == [] and not out.exists()


def test_zero_feature_sweep_exits_3(harness, monkeypatch):
    mod, restores, out = harness
    import core.feature_foundry as ff
    monkeypatch.setattr(ff, "get_feature_registry",
                        lambda: SimpleNamespace(list_features=lambda: [_feat("x", tier="C")]))
    monkeypatch.setattr(mod, "ONLY", [])
    assert mod.main() == 3
    assert restores == [] and not out.exists()


def test_tier_c_id_is_refused_not_dropped():
    mod = importlib.import_module("scripts.run_foundry_eval_t195")
    feats, code, why = mod.select_features([_feat("a"), _feat("c", tier="C")], ["a", "c"])
    assert (feats, code) == ([], 2) and "['c']" in why


def test_known_ids_select_exactly_those():
    mod = importlib.import_module("scripts.run_foundry_eval_t195")
    pool = [_feat("a"), _feat("b", tier="B"), _feat("c")]
    feats, code, why = mod.select_features(pool, ["b", "a"])
    assert code == 0 and why == "" and [f.feature_id for f in feats] == ["a", "b"]


def test_the_rescore_campaign_ids_resolve_in_the_real_registry():
    """The three ids scripts/run_rr1_rescore_campaign.sh passes must all select."""
    import core.feature_foundry.features  # noqa: F401
    from core.feature_foundry import get_feature_registry
    mod = importlib.import_module("scripts.run_foundry_eval_t195")
    ids = ["triple_witching_premium", "january_effect", "mom_12_1"]
    feats, code, why = mod.select_features(get_feature_registry().list_features(), ids)
    assert code == 0, why
    assert sorted(f.feature_id for f in feats) == sorted(ids)
