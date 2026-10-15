"""The TICKER exclusion kind (ruled 2026-10-15): AZO, MTD and NVR — ÷10 for their whole history in
the canonical cache — are removed at universe RESOLUTION and from PIT membership, recorded under their
own census key by both producers, with the panel allow-list untouched; the exclusion lifts at re-pin #2
only through `lift_verified`."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from core.census import assert_census
from engines.data_manager import exclusions as ex
from engines.data_manager.universe_resolver import resolve_universe

REPO = Path(__file__).resolve().parents[1]
DECLARED = sorted(ex.DECLARED_TICKER_EXCLUSIONS)


@pytest.fixture(autouse=True)
def _fresh_log():
    ex.reset_exclusion_log()
    yield
    ex.reset_exclusion_log()


def _resolution_names() -> set:
    blk = ex.ticker_exclusions_applied().get("scale_defect_div10", {})
    return {t for t, r in blk.get("tickers", {}).items() if "resolution" in r["withheld_at"]}


# ── removed at RESOLUTION, on every path ────────────────────────────────────────

def test_the_declaration_is_the_four_scale_defect_names():
    """AZO, MTD, NVR (R's read) and SLE (the last-bar LEVEL IDENTITY read it at exactly 0.1000)."""
    assert DECLARED == ["AZO", "MTD", "NVR", "SLE"]
    for spec in ex.DECLARED_TICKER_EXCLUSIONS.values():
        assert spec["declared_ratio"] == 10.0 and "÷10" in spec["reason"]
    assert ex.DECLARED_TICKER_EXCLUSIONS["AZO"]["reason"] == "scale defect ÷10 baked at the T-082b merge"
    assert "no PIT interval" in ex.DECLARED_TICKER_EXCLUSIONS["SLE"]["reason"]


def test_a_declared_ticker_is_removed_at_RESOLUTION_on_the_static_path(tmp_path):
    tickers, info = resolve_universe(static_tickers=["AAPL", "AZO", "MTD", "SPY"], start="2021-01-01",
                                     end="2024-12-31", use_historical=False, cache_dir=tmp_path)
    assert tickers == ["AAPL", "SPY"]
    assert info["ticker_exclusions"] == ["AZO", "MTD"] and info["n_after_ticker_exclusions"] == 2
    assert _resolution_names() == {"AZO", "MTD"}


def test_a_declared_ticker_is_removed_at_RESOLUTION_on_the_historical_path(tmp_path):
    uni = tmp_path / "universe"
    uni.mkdir()
    pd.DataFrame([{"ticker": t, "name": None, "sector": None,
                   "included_from": pd.Timestamp("2015-01-01"), "included_until": pd.NaT}
                  for t in ("AAA", "NVR", "AZO")]).to_parquet(uni / "sp500_membership.parquet", index=False)
    tickers, info = resolve_universe(static_tickers=[], start="2021-01-01", end="2024-12-31",
                                     use_historical=True, cache_dir=tmp_path, essential_tickers=["SPY"])
    assert info["mode"] == "historical"
    assert "NVR" not in tickers and "AZO" not in tickers and {"AAA", "SPY"} <= set(tickers)
    assert info["ticker_exclusions"] == ["AZO", "NVR"]


# ── the census: invariant 2 holds with the allow-list at ZERO ───────────────────

def _panel_shrink(n_resolved: int, n_in_panel: int) -> bool:
    v = assert_census({"census": {"n_resolved": n_resolved, "n_in_panel": n_in_panel}}, panel_allowlist=0)
    return any("panel shrank" in f for f in v.failures)


def test_resolution_exclusion_keeps_census_invariant_2_GREEN_with_the_allowlist_at_ZERO(tmp_path):
    """The ruled shape: resolved and panel BOTH exclude the names. The rejected shape (bars withheld
    inside a still-resolved ticker → an empty frame dropped from the panel) shrinks the panel."""
    tickers, _ = resolve_universe(static_tickers=["AAPL", "AZO", "MTD", "NVR", "SPY"], start="2021-01-01",
                                  end="2024-12-31", use_historical=False, cache_dir=tmp_path)
    panel = list(tickers)                                   # every resolved name builds
    assert not _panel_shrink(len(tickers), len(panel))
    assert _panel_shrink(5, 2), "the bars-kind alternative would fail invariant 2 at allow-list 0"


def test_the_census_block_names_the_names_the_reason_and_the_declared_ratio(tmp_path):
    resolve_universe(static_tickers=["MTD", "AAPL"], start="2021-01-01", end="2024-12-31",
                     use_historical=False, cache_dir=tmp_path)
    rec = ex.ticker_exclusions_applied()["scale_defect_div10"]["tickers"]["MTD"]
    assert rec["reason"] == "scale defect ÷10 baked at the T-082b merge" and rec["declared_ratio"] == 10.0
    assert rec["withheld_at"] == ["resolution"] and rec["evidence"]["cache_close"] == 129.63


def test_SLE_and_AZO_withheld_together_KEEP_BOTH_reasons(tmp_path):
    """One census key, two reasons: a key-level reason would keep only the first name's (found
    when SLE was added)."""
    resolve_universe(static_tickers=["AZO", "SLE", "AAPL"], start="2021-01-01", end="2024-12-31",
                     use_historical=False, cache_dir=tmp_path)
    tick = ex.ticker_exclusions_applied()["scale_defect_div10"]["tickers"]
    assert set(tick) == {"AZO", "SLE"}
    assert tick["AZO"]["reason"] != tick["SLE"]["reason"]
    assert "no PIT interval" in tick["SLE"]["reason"]


def test_an_ERRORED_ticker_exclusions_record_fails_the_census():
    v = assert_census({"census": {"n_resolved": 3, "n_in_panel": 3,
                                  "ticker_exclusions": {"error": "RuntimeError('boom')"}}})
    assert any("ticker_exclusions record errored" in f for f in v.failures)


def test_both_census_producers_write_the_key():
    """The two-producer rule, executed for the candidate (the controller is held by AST in
    tests/test_contracts.py's CENSUS_PROVENANCE_KEYS)."""
    from engines.engine_d_discovery.discovery import candidate_census_block

    class _C:
        nonzero_calls, errors = 1, 0
    resolve_universe(static_tickers=["NVR"], start="2021-01-01", end="2024-12-31",
                     use_historical=False, cache_dir=REPO)
    block = candidate_census_block("cand_v1", _C(), n_trades=5)
    assert "NVR" in block["ticker_exclusions"]["scale_defect_div10"]["tickers"]


# ── PIT membership: every interval of a ticker-kind name goes ──────────────────

def test_clip_membership_drops_EVERY_interval_of_a_ticker_kind_name():
    m = pd.DataFrame({"ticker": ["AZO", "AZO", "AAPL", "MTD"],
                      "start": pd.to_datetime(["1997-01-02", "2005-01-01", "2000-01-01", "2016-09-06"]),
                      "end": pd.to_datetime([None, None, None, None])})
    out = ex.clip_membership(m)
    assert set(out["ticker"]) == {"AAPL"}
    blk = ex.ticker_exclusions_applied()["scale_defect_div10"]["tickers"]
    assert blk["AZO"]["membership_intervals_dropped"] == 2 and blk["MTD"]["membership_intervals_dropped"] == 1


# ── the lift at re-pin #2 is exact ──────────────────────────────────────────────

@pytest.mark.parametrize("ticker", DECLARED)
def test_the_lift_is_verified_ONLY_at_the_declared_ratio(ticker):
    cache_close = ex.DECLARED_TICKER_EXCLUSIONS[ticker]["evidence"]["cache_close"]
    assert ex.lift_verified(ticker, cache_close * 10.0)
    assert not ex.lift_verified(ticker, cache_close), "still ÷10: the exclusion stays"
    assert not ex.lift_verified(ticker, cache_close * 10.0 * 1.01), "a different factor: it stays"


# ── the declaration matches today's canonical cache (data-dependent) ───────────

@pytest.mark.parametrize("ticker", DECLARED)
def test_the_declaration_matches_TODAYS_canonical_cache(ticker):
    f = REPO / "data" / "processed" / f"{ticker}_1d.csv"
    if not f.exists():
        pytest.skip("no canonical cache in this tree")
    spec = ex.DECLARED_TICKER_EXCLUSIONS[ticker]["evidence"]
    df = pd.read_csv(f, parse_dates=["Date"]).set_index("Date")
    assert df.loc[pd.Timestamp(spec["date"]), "Close"] == pytest.approx(spec["cache_close"], abs=0.01)
