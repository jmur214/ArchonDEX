"""Item (d), steps 1-2 (ruled 2026-10-15): no loader rescue of price LEVELS; DAL's stitched pre-2007
bars withheld by a DECLARED, census-recorded exclusion that fails closed.

Step 1: the loader divided OHLC by 10 whenever the median close exceeded 1000. Across all 730 cached
series it fired on exactly one — DAL, whose 1980-2005 bars are old Delta's cancelled equity stitched
at 3,000-8,000 — so it masked corruption instead of protecting data. A series now loads at its true
stored level. Step 2: DAL's pre-2007 bars are withheld (never deleted, never rescued), recorded, and
emitted by the census; a mismatch between declaration and data raises.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engines.data_manager import data_manager as dmod
from engines.data_manager import exclusions as ex

REPO = Path(__file__).resolve().parent.parent


def _bars(idx, close) -> pd.DataFrame:
    close = pd.Series(close, index=idx, dtype=float)
    return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99,
                         "Close": close, "Volume": 1e6}, index=idx)


@pytest.fixture
def dm(tmp_path):
    ex.reset_exclusion_log()
    yield dmod.DataManager(cache_dir=str(tmp_path / "cache"))
    ex.reset_exclusion_log()


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


# ── step 1: true level ─────────────────────────────────────────────────────────

def test_a_series_priced_above_1000_loads_at_its_TRUE_level(dm):
    idx = pd.bdate_range("2015-01-02", periods=300)
    dm.save_cache("HIGHPX", "1d", _bars(idx, 3000 + np.arange(300.0)))
    got = dm.load_cached("HIGHPX", "1d")
    assert float(got["Close"].median()) == pytest.approx(3149.5), "no ÷10 rescue"


# ── step 2: declared withholding ───────────────────────────────────────────────

def _stitched_dal(dm):
    pre = pd.bdate_range("2000-01-03", "2007-05-02")
    post = pd.bdate_range("2007-05-03", "2010-12-31")
    df = pd.concat([_bars(pre, 5000.0), _bars(post, 17.0)])
    dm.save_cache("DAL", "1d", df)
    return len(pre)


def test_DAL_pre2007_bars_are_withheld_recorded_and_never_deleted(dm):
    n_pre = _stitched_dal(dm)
    pq = dm.parquet_cache_path("DAL", "1d")
    before = _md5(pq)
    got = dm.load_cached("DAL", "1d")
    assert got.index.min() == pd.Timestamp("2007-05-03")
    assert float(got["Close"].max()) == pytest.approx(17.0)
    rec = ex.exclusions_applied()["dal_pre2007_excluded"]
    assert rec["n_bars_withheld"] == n_pre and "stitched identity" in rec["reason"]
    assert _md5(pq) == before, "withholding is in memory — the file is the archived artifact"


def test_an_undeclared_ticker_is_served_whole(dm):
    idx = pd.bdate_range("2000-01-03", periods=50)
    dm.save_cache("XOM", "1d", _bars(idx, 50.0))
    assert len(dm.load_cached("XOM", "1d")) == 50 and ex.exclusions_applied() == {}


def test_a_declaration_that_no_longer_matches_FAILS_CLOSED_and_deletes_nothing(dm):
    """A bar served AFTER the cutoff still carries the corruption signature: the declaration is
    wrong. It must raise — and, because withholding runs outside the read's error handler, the
    file must survive (a handler that unlinks unreadable files must never see this error)."""
    # a SUSTAINED corrupt block after the cutoff (an isolated spike is a bad tick the cleanup
    # rightly drops — that would not be a declaration mismatch)
    idx = pd.bdate_range("2007-05-03", periods=80)
    dm.save_cache("DAL", "1d", _bars(idx, [5000.0] * 60 + [17.0] * 20))
    pq = dm.parquet_cache_path("DAL", "1d")
    before = _md5(pq)
    with pytest.raises(ex.ExclusionMismatchError, match="no longer matches the data"):
        dm.load_cached("DAL", "1d")
    assert pq.exists() and _md5(pq) == before


def test_membership_is_clipped_by_the_declared_rule():
    m = pd.DataFrame({"ticker": ["DAL", "DAL", "XOM"],
                      "start": pd.to_datetime(["1990-01-02", "2000-01-03", "1990-01-02"]),
                      "end": pd.to_datetime(["2005-01-04", None, None])})
    out = ex.clip_membership(m)
    dal = out[out["ticker"] == "DAL"]
    assert len(dal) == 1 and dal["start"].iloc[0] == pd.Timestamp("2007-05-03")
    assert out[out["ticker"] == "XOM"]["start"].iloc[0] == pd.Timestamp("1990-01-02")


def test_a_reset_starts_the_runs_bar_record(dm):
    _stitched_dal(dm)
    dm.load_cached("DAL", "1d")
    assert "dal_pre2007_excluded" in ex.exclusions_applied()
    ex.reset_exclusion_log()
    assert "n_bars_withheld" not in ex.exclusions_applied().get("dal_pre2007_excluded", {})


# ── the real file (skips where the substrate is absent) ────────────────────────

def test_the_real_DAL_file_is_served_from_the_new_listing_at_its_true_level():
    real = REPO / "data" / "processed" / "parquet" / "DAL_1d.parquet"
    if not real.exists():
        pytest.skip("the processed substrate is not on disk here")
    before = _md5(real)
    ex.reset_exclusion_log()
    got = dmod.DataManager(cache_dir=str(REPO / "data" / "processed")).load_cached("DAL", "1d")
    assert got.index.min() >= pd.Timestamp("2007-05-03") and float(got["Close"].max()) < 1000
    assert _md5(real) == before
    ex.reset_exclusion_log()


# ── wiring, by the AST call / assignment ───────────────────────────────────────

def test_the_census_emits_the_declared_exclusions():
    tree = ast.parse((REPO / "backtester" / "backtest_controller.py").read_text())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_build_census")
    keys = {ast.unparse(t.slice) for a in ast.walk(fn) if isinstance(a, ast.Assign)
            for t in a.targets if isinstance(t, ast.Subscript)}
    assert "'data_exclusions'" in keys


def test_each_run_resets_the_exclusion_record_BEFORE_it_fetches():
    tree = ast.parse((REPO / "orchestration" / "mode_controller.py").read_text())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "run_backtest")
    def first(name):
        ls = [c.lineno for c in ast.walk(fn) if isinstance(c, ast.Call)
              and (getattr(c.func, "attr", None) or getattr(c.func, "id", None)) == name]
        return min(ls) if ls else None
    assert first("reset_exclusion_log") is not None
    assert first("reset_exclusion_log") < first("ensure_data")


def test_load_membership_APPLIES_the_declared_clip():
    """Today's membership file lists DAL only from 2013, so the clip is a no-op on this data — the
    rule must exist anyway (a rule that is only a property of the current file is not a rule)."""
    tree = ast.parse((REPO / "engines" / "data_manager" / "membership.py").read_text())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "load_membership")
    called = {getattr(c.func, "id", getattr(c.func, "attr", "")) for c in ast.walk(fn) if isinstance(c, ast.Call)}
    assert "clip_membership" in called
