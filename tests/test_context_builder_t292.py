"""T-292 — context_builder guarantees: deterministic, secret-free, fail-open."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from intelligence.analyst.context_builder import (build_bundle, bundle_sha256,
                                                  canonical_json, _scrub)

AS_OF = dt.date(2026, 7, 8)
PORT = {"sleeve": {"SPY": 0.30, "AGG": 0.10}, "offense-sso": {"SSO": 0.99}}


def _empty_panel(*a, **k):
    return pd.DataFrame(columns=["created_at", "symbols", "headline", "content"])


def test_bundle_is_deterministic_same_inputs_same_hash():
    b1 = build_bundle(AS_OF, portfolios=PORT, watchlist=["QQQ"], load_panel=_empty_panel)
    b2 = build_bundle(AS_OF, portfolios=PORT, watchlist=["QQQ"], load_panel=_empty_panel)
    assert bundle_sha256(b1) == bundle_sha256(b2)
    assert canonical_json(b1) == canonical_json(b2)


def test_dict_order_does_not_change_the_hash():
    a = build_bundle(AS_OF, portfolios={"sleeve": {"AGG": 0.1, "SPY": 0.3}},
                     load_panel=_empty_panel)
    b = build_bundle(AS_OF, portfolios={"sleeve": {"SPY": 0.3, "AGG": 0.1}},
                     load_panel=_empty_panel)
    assert bundle_sha256(a) == bundle_sha256(b)


def test_NO_secrets_ever_reach_the_bundle():
    # a malicious/careless caller passing a creds-laden portfolio dict
    dirty = {"sleeve": {"SPY": 0.3},
             "ALPACA_API_KEY": {"PKLIVEKEY1234567890": 1.0},
             "account_number": {"PA123456789": 1.0}}
    b = build_bundle(AS_OF, portfolios=dirty, load_panel=_empty_panel)
    blob = canonical_json(b)
    for leak in ("ALPACA_API_KEY", "account_number", "PKLIVEKEY1234567890", "PA123456789"):
        assert leak not in blob, leak


def test_scrub_redacts_key_shaped_values_anywhere():
    out = _scrub({"note": "hold", "nested": ["PKABCDEFGH12345678", "fine"]})
    assert out["nested"][0] == "[REDACTED]" and out["nested"][1] == "fine"


def test_scrub_drops_credential_keys():
    out = _scrub({"secret_token": "x", "bearer": "y", "symbol": "SPY"})
    assert out == {"symbol": "SPY"}


def test_fail_open_when_news_panel_raises():
    def boom(*a, **k):
        raise RuntimeError("panel down")
    b = build_bundle(AS_OF, portfolios=PORT, load_panel=boom)
    assert b["news"]["degraded"] is True and b["news"]["items"] == []
    # the rest of the bundle still built
    assert b["portfolios"]["sleeve"]["SPY"] == 0.3


def test_pit_news_only_before_as_of():
    # a panel with one pre and one post article; only the pre one may appear
    df = pd.DataFrame([
        {"created_at": "2026-07-07T10:00:00", "symbols": ["SPY"],
         "headline": "pre", "content": "before"},
        {"created_at": "2026-07-09T10:00:00", "symbols": ["SPY"],
         "headline": "post", "content": "after (leak!)"},
    ])
    # load_panel(as_of=…) is responsible for the PIT cut; simulate it here
    def panel(as_of=None):
        return df[pd.to_datetime(df["created_at"]).dt.date < as_of]
    b = build_bundle(AS_OF, portfolios={"sleeve": {"SPY": 0.3}}, load_panel=panel)
    heads = [i["headline"] for i in b["news"]["items"]]
    assert "pre" in heads and "post" not in heads


def test_portfolio_weights_present_but_only_symbols_and_numbers():
    b = build_bundle(AS_OF, portfolios=PORT, load_panel=_empty_panel)
    assert b["portfolios"] == {"offense-sso": {"SSO": 0.99},
                               "sleeve": {"AGG": 0.1, "SPY": 0.3}}
