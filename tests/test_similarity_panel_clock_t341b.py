# tests/test_similarity_panel_clock_t341b.py
"""T-341b — the similarity panel had NO clock and went 8 weeks stale.

The design point under test: the clock ages the refresh RECEIPT, not the panel's
newest decision_date, because that date cannot distinguish "no new 10-Ks were filed"
(healthy — filings are sharply seasonal) from "the refresh never ran" (a dead clock).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from paper_trader.clock_census import _similarity_panel_refreshed, REGISTRY, ADVANCED, MISS

REL = "data/edgar/similarity_panel_refresh.json"


def _receipt(root, days_ago=0, budget=45, **kw):
    p = root / REL
    p.parent.mkdir(parents=True, exist_ok=True)
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    p.write_text(json.dumps({"refreshed_at": ts, "budget_days": budget,
                             "newest_decision_date": "2026-06-23",
                             "rows_added": kw.get("rows_added", 0)}))
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def test_missing_receipt_is_a_MISS_not_a_skip(tmp_path):
    """FAIL-CLOSED: you cannot census what you cannot read."""
    r = _similarity_panel_refreshed(tmp_path, "2026-08-15")
    assert r.status == MISS and "no refresh receipt" in r.detail


def test_unparseable_receipt_is_a_MISS(tmp_path):
    p = tmp_path / REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ not json")
    assert _similarity_panel_refreshed(tmp_path, "2026-08-15").status == MISS


def test_fresh_refresh_advances(tmp_path):
    as_of = _receipt(tmp_path, days_ago=0)
    assert _similarity_panel_refreshed(tmp_path, as_of).status == ADVANCED


def test_refresh_that_found_NOTHING_still_advances(tmp_path):
    """THE POINT: a refresh that ran and added zero rows is HEALTHY. Aging the
    panel's decision_date instead would call this a stall during a filing lull."""
    as_of = _receipt(tmp_path, days_ago=3, rows_added=0)
    r = _similarity_panel_refreshed(tmp_path, as_of)
    assert r.status == ADVANCED, "a ran-and-found-nothing refresh must not be a MISS"


def test_stale_refresh_is_a_MISS_with_the_age(tmp_path):
    as_of = _receipt(tmp_path, days_ago=60)
    r = _similarity_panel_refreshed(tmp_path, as_of)
    assert r.status == MISS
    assert "EXCEEDS" in r.detail and "60d" in r.detail


def test_budget_boundary_is_inclusive(tmp_path):
    assert _similarity_panel_refreshed(tmp_path, _receipt(tmp_path, 45)).status == ADVANCED
    assert _similarity_panel_refreshed(tmp_path, _receipt(tmp_path, 46)).status == MISS


def test_clock_is_registered(tmp_path):
    """The panel must be COVERED, not merely fixable — the T-338 one-registry rule."""
    names = {c.name for c in REGISTRY}
    assert "similarity_panel_refreshed" in names
    covered = {p for c in REGISTRY for p in c.covers}
    assert REL in covered, "the receipt must be a declared covered path"
