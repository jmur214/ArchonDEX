"""Ruling C-2 — a run fed by the yfinance fallback is RECORDED and NON-CANONICAL; a canonical
runner REFUSES the fallback outright (Agent R's lock 6).

Why it matters now: with the import-time .env loads gone (Change A), an entry that forgets
`load_local_env()` has no Alpaca keys, and DataManager then fetches every uncached ticker from
yfinance — a different source on a different adjustment basis — with only a print. These locks
make that switch visible in the census and impossible in a canonical run.

No network: `_fetch_yfinance` is replaced by a fake, and the cache lives in tmp_path.
"""
from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core.census import assert_census
from engines.data_manager import data_manager as dmod

REPO = Path(__file__).resolve().parent.parent
KEY_VARS = ("ALPACA_API_KEY", "APCA_API_KEY_ID", "ALPACA_SECRET_KEY", "APCA_API_SECRET_KEY")


def _bars(n: int = 30) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", periods=n)
    px = 100 + np.arange(n, dtype=float)
    return pd.DataFrame({"Open": px, "High": px, "Low": px, "Close": px, "Volume": 1e6}, index=idx)


@pytest.fixture
def offline_dm(tmp_path, monkeypatch):
    """A DataManager with NO Alpaca keys, a tmp cache, and a recording fake yfinance."""
    for k in KEY_VARS:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv(dmod.REFUSE_YFINANCE_ENV, raising=False)
    dmod.reset_feed_log()
    dm = dmod.DataManager(cache_dir=str(tmp_path / "cache"))
    calls = []
    monkeypatch.setattr(dm, "_fetch_yfinance", lambda t, *a, **k: calls.append(t) or _bars())
    yield dm, calls
    dmod.reset_feed_log()


# ── the record ──────────────────────────────────────────────────────────────────

def test_an_offline_fetch_is_RECORDED_as_yfinance(offline_dm):
    dm, calls = offline_dm
    dm.ensure_data(["ZZZT"], "2024-01-01", "2024-03-01")
    assert calls == ["ZZZT"]
    feed = dmod.data_feed_summary()
    assert feed["yfinance_tickers"] == ["ZZZT"]
    assert feed["by_source"] == {"yfinance(offline)": 1}


def test_a_cached_ticker_is_not_a_network_fetch(offline_dm):
    dm, calls = offline_dm
    dm.save_cache("CCHD", "1d", _bars())
    dm.ensure_data(["CCHD"], "2024-01-01", "2024-03-01")
    assert calls == [] and dmod.data_feed_summary()["n_network_fetched"] == 0


# ── the refusal (canonical runs) ────────────────────────────────────────────────

def test_a_canonical_run_REFUSES_the_fallback_and_fetches_nothing(offline_dm, monkeypatch):
    dm, calls = offline_dm
    monkeypatch.setenv(dmod.REFUSE_YFINANCE_ENV, "1")
    with pytest.raises(RuntimeError, match="REFUSES the yfinance fallback"):
        dm.ensure_data(["ZZZT"], "2024-01-01", "2024-03-01")
    assert calls == [], "the fallback must not even be attempted"
    assert dmod.data_feed_summary()["n_network_fetched"] == 0


def test_run_isolated_sets_the_refusal(monkeypatch):
    """setenv(NAME, "") FIRST, so monkeypatch records "previously unset" and teardown deletes
    what the real function writes. Two leaks found here: delenv AFTER the call saved "1" and
    RESTORED it at teardown; delenv(raising=False) on an ABSENT variable records nothing at all,
    so the "1" survived. Either leaked the refusal into every later test in the session."""
    from scripts import run_isolated
    monkeypatch.setenv(dmod.REFUSE_YFINANCE_ENV, "")
    run_isolated.enforce_canonical_data_feed()
    import os
    assert os.environ.get(dmod.REFUSE_YFINANCE_ENV) == "1"


def test_run_isolated_main_CALLS_the_refusal():
    """AST call node in main()'s body — not text (a comment naming it would not count)."""
    tree = ast.parse((REPO / "scripts" / "run_isolated.py").read_text())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    called = {getattr(c.func, "id", getattr(c.func, "attr", "")) for c in ast.walk(main)
              if isinstance(c, ast.Call)}
    assert "enforce_canonical_data_feed" in called


# ── the gate ───────────────────────────────────────────────────────────────────

def _summary(**census_overrides) -> dict:
    """A census that passes invariants 1-6, so only data_feed decides."""
    census = {"edges_blind": [], "edges_errored": {}, "n_resolved": 10, "n_in_panel": 10,
              "n_trades": 5, "trades_canon_md5": "abc", "trades_empty": False,
              "fundamentals_blind": 0, "regime_unknown_frac": 0.0, "regime_total_bars": 100,
              "config_provenance": {}}
    census.update(census_overrides)
    return {"census": census, "bootstrap_ci_skip_reason": "test"}


def test_a_yfinance_fed_run_is_NON_CANONICAL():
    v = assert_census(_summary(data_feed={"n_network_fetched": 2, "by_source": {},
                                          "yfinance_tickers": ["AAA", "BBB"]}))
    assert not v.canonical and any("switched to yfinance" in f for f in v.failures)


def test_an_alpaca_or_cache_only_run_stays_canonical():
    v = assert_census(_summary(data_feed={"n_network_fetched": 1, "by_source": {"alpaca": 1},
                                          "yfinance_tickers": []}))
    assert v.canonical, v.failures


def test_an_errored_feed_record_fails_closed():
    v = assert_census(_summary(data_feed={"error": "ImportError()"}))
    assert not v.canonical and any("data_feed record errored" in f for f in v.failures)


def test_a_legacy_summary_without_the_record_only_warns():
    v = assert_census(_summary())
    assert v.canonical and any("no data_feed record" in w for w in v.warnings)


def test_discoverys_gate1_candidate_census_carries_the_feed_record():
    """validate_candidate builds its own census block; it must carry data_feed, or a candidate
    validated on yfinance-fed data passes Gate 1 unflagged. AST: the dict assigned to
    `_census_block` in discovery.py has a "data_feed" key."""
    tree = ast.parse((REPO / "engines" / "engine_d_discovery" / "discovery.py").read_text())
    blocks = [n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
              and any(getattr(t, "id", "") == "_census_block" for t in n.targets)
              and isinstance(n.value, ast.Dict)]
    assert blocks, "validate_candidate's _census_block literal not found"
    keys = {k.value for b in blocks for k in b.keys if isinstance(k, ast.Constant)}
    assert "data_feed" in keys


def test_each_backtest_run_starts_its_own_feed_record_BEFORE_it_fetches():
    """Agent R's O-1: the log is process-wide, so a long-lived multi-run process would carry run 1's
    yfinance fetch into every later census. The reset sits at the top of run_backtest and BEFORE its
    first ensure_data — at BacktestController.run (after the fetch) it would erase the run's own
    fallback fetches, the opposite of the intent."""
    tree = ast.parse((REPO / "orchestration" / "mode_controller.py").read_text())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "run_backtest")
    def first_line(name):
        lines = [c.lineno for c in ast.walk(fn) if isinstance(c, ast.Call)
                 and (getattr(c.func, "attr", None) or getattr(c.func, "id", None)) == name]
        return min(lines) if lines else None
    reset, fetch = first_line("reset_feed_log"), first_line("ensure_data")
    assert reset is not None, "run_backtest never resets the feed record"
    assert fetch is not None and reset < fetch, f"reset (line {reset}) must precede the fetch (line {fetch})"


def test_reset_clears_a_prior_runs_fallback(offline_dm):
    dm, _ = offline_dm
    dm.ensure_data(["RUNONE"], "2024-01-01", "2024-03-01")
    assert dmod.data_feed_summary()["yfinance_tickers"] == ["RUNONE"]
    dmod.reset_feed_log()
    assert dmod.data_feed_summary()["yfinance_tickers"] == [], "run 2 must not inherit run 1's fetch"
