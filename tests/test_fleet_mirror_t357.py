# tests/test_fleet_mirror_t357.py
"""T-357 — the fleet mirror's numbers, including the two the smoke run caught.

The mirror replaces the broker's ~$100k with the number the machine actually
acts on. That makes every arithmetic error here a wrong number in the user's
pocket, shown with the authority of "the honest one".
"""
from __future__ import annotations

from paper_trader.fleet_mirror import SCHEMA, assemble, build_slice

# the real account-2 book: the 2026-09-15 arrival fills, priced at the 09-14 closes
REAL = dict(account_id="offense-sso", strategy="deploy_candidate",
            run_date="2026-09-17", as_of="2026-09-17T13:52:00+00:00",
            canonical=True, positions={"VOO": 12, "MTUM": 5, "SGOV": 1},
            closes={"VOO": 699.30, "MTUM": 299.097, "SGOV": 100.53},
            tier_cap=10_000.0, basis_dollars=9_978.42)


def test_tier_equity_is_NOT_pinned_to_the_cap():
    """BUG 1, caught in the first smoke run. Deriving cash as `cap - invested`
    makes tier_equity == cap identically — the headline number frozen at the
    tier forever, always exactly right and never true."""
    s = build_slice(**REAL)
    assert s["tier_equity"] != s["tier_cap"], "tier_equity is pinned to the cap"
    assert s["cash"] == 21.58, "tier cash is cap minus BASIS (what was not spent)"
    # and it must actually move with prices
    up = build_slice(**{**REAL, "closes": {"VOO": 710.0, "MTUM": 299.097,
                                           "SGOV": 100.53}})
    assert up["tier_equity"] > s["tier_equity"]


def test_total_change_is_measured_against_CONTRIBUTED_CAPITAL():
    """BUG 2, same run. Measuring vs the positions' basis double-counts the
    undeployed residue: it read +30.79 on a day the book was +9.21."""
    s = build_slice(**REAL)
    assert s["total_change"] == round(s["tier_equity"] - s["tier_cap"], 2)
    assert s["total_change"] != round(s["tier_equity"] - 9_978.42, 2)


def test_a_missing_price_makes_tier_equity_UNKNOWN_not_a_subtotal():
    """[NN-FAIL-CLOSED]. A partial sum shown as a total is a wrong number that
    looks right — and on a phone it looks authoritative."""
    s = build_slice(**{**REAL, "closes": {"MTUM": 299.097, "SGOV": 100.53}})
    assert s["tier_equity"] is None
    assert "VOO" in s["tier_equity_unknown_reason"]
    assert s["total_change"] is None and s["day_change"] is None


def test_tier_cash_is_never_INVENTED_when_nothing_says_what_it_is():
    """With positions held but neither tier_cash nor basis supplied, the tier's
    cash is genuinely unknown — deriving it would resurrect bug 1."""
    args = {k: v for k, v in REAL.items() if k != "basis_dollars"}
    s = build_slice(**args)
    assert s["tier_equity"] is None and s["cash"] is None


def test_a_flat_account_is_all_tier_cash_not_unknown():
    """The fail-closed rule must not swallow the legitimate pre-arrival state.

    A flat account has no basis — passing one alongside zero positions is
    contradictory input, which is how the first draft of this test failed. The
    honest model of 'before the arrival event' is no positions and no basis."""
    flat = {k: v for k, v in REAL.items() if k != "basis_dollars"}
    s = build_slice(**{**flat, "positions": {}, "closes": {}})
    assert s["cash"] == 10_000.0 and s["tier_equity"] == 10_000.0
    assert s["positions"] == []


def test_vs_spy_is_null_until_evaluable_never_a_fake_zero():
    """0.0 reads as 'dead even' — a claim a one-day record cannot make."""
    s = build_slice(**REAL)
    assert s["vs_spy_at_tier"] is None


def test_the_envelope_matches_the_PINNED_contract():
    """The Swift app is being built against exactly this shape."""
    s = build_slice(**REAL)
    for k in ("id", "display_name", "tier_equity", "tier_cap", "cash",
              "day_change", "total_change", "vs_spy_at_tier", "positions",
              "canonical", "run_date"):
        assert k in s, f"pinned per-account key missing: {k}"
    for k in ("ticker", "qty", "last", "value"):
        assert k in s["positions"][0], f"pinned position key missing: {k}"
    env = assemble([s], "2026-09-17T13:52:00+00:00")
    assert env["schema"] == SCHEMA == "fleet_mirror/v1"
    assert set(env) == {"schema", "as_of", "accounts"}
    assert isinstance(env["accounts"], list)


def test_a_non_canonical_day_is_flagged_so_the_app_can_gray_it():
    """The silent-wrongness rule in the user's pocket: stale must not render as
    fresh."""
    s = build_slice(**{**REAL, "canonical": False})
    assert s["canonical"] is False and s["run_date"] == "2026-09-17"


def test_the_broker_equity_is_NOWHERE_in_the_slice():
    """The whole reason this surface exists. ~$100k must not appear."""
    s = build_slice(**REAL)
    assert 100_000 not in [s["tier_equity"], s["tier_cap"], s["cash"]]
    assert all((p["value"] or 0) < 50_000 for p in s["positions"])


# --------------------------------------------------------------------------- #
# The EXECUTION lock. Same doctrine as T-350f/T-355: a display surface that is
# only text-verified is exactly the phantom this program keeps building — and a
# mirror nobody writes is a mirror the app renders as blank forever.
# --------------------------------------------------------------------------- #
import datetime as _dt
import json as _json
import shutil as _shutil
import types as _types

import pandas as _pd

import scripts.run_paper_cloud_day as _drv
from paper_trader.paper_client import FakePaperClient as _FPC


class _Cloud:
    def __init__(self):
        self.cfg = _types.SimpleNamespace(enabled=False, s3_root="LOCAL", prefix="x")

    def pull(self):
        return False

    def push(self):
        return True

    def emit_metrics(self, **kw):
        pass

    def pull_readonly_from(self, *a, **k):
        pass


def _drive(tmp_path):
    today = _dt.date(2026, 9, 17)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    _shutil.copy("config/substantially_identical.json",
                 tmp_path / "config/substantially_identical.json")
    (tmp_path / "config/llm_settings.json").write_text(_json.dumps(
        {"llm": {"kill_switch": False, "trading_kill_switch": False,
                 "monthly_budget_usd": 30.0, "max_output_tokens": 1500}}))
    idx = _pd.bdate_range(end=_pd.Timestamp(today) - _pd.Timedelta(days=1), periods=400)
    base = {"SPY": 600.0, "AGG": 98.0, "GLD": 420.0}
    series = {t: _pd.Series([v * (1 + 0.0004 * i) for i in range(len(idx))], index=idx)
              for t, v in base.items()}

    class _C(_FPC):
        def get_account(self):
            return {"equity": 100_000.0, "cash": 100_000.0, "status": "ACTIVE"}

        def list_positions(self):
            return []

        def fetch_daily_closes(self, tickers, lookback_days=400):
            return {t: series.get(t, _pd.Series(
                [100.0 * (1 + 0.0004 * i) for i in range(len(idx))], index=idx))
                for t in tickers}

        def fetch_latest_prices(self, tickers):
            return {t: float(series[t].iloc[-1]) if t in series else 100.0
                    for t in tickers}

        def trading_days(self, start, end):
            return {today}

    _drv.main(["--allocator", "mean_variance", "--strategy", "trend_sleeve",
               "--sleeve-notional-cap", "10000"],
              now=_dt.datetime(2026, 9, 17, 9, 45, tzinfo=_dt.timezone.utc),
              client=_C(), cloud=_Cloud(), root=str(tmp_path))
    return tmp_path / "data/state/fleet_mirror_slice.json"


def test_a_real_run_WRITES_the_slice(tmp_path, capsys):
    """THE FIRST ARTIFACT at driver level. Before this wiring the file was never
    written by anything — the shape the retired analyst desk held for 36
    sessions."""
    path = _drive(tmp_path)
    out = capsys.readouterr().out
    assert "11. MIRROR" in out, f"the mirror step never ran\n{out[-1500:]}"
    assert path.exists(), "the slice was not written"
    slice_ = _json.loads(path.read_text())
    assert slice_["schema"] == "fleet_mirror/v1"
    assert slice_["run_date"] == "2026-09-17"
    assert slice_["tier_cap"] == 10_000.0


def test_the_written_slice_never_shows_the_brokers_hundred_thousand(tmp_path):
    """The reason the surface exists, asserted against a REAL run rather than a
    constructed dict: the account holds $100k at the broker and the slice must
    show the tier."""
    slice_ = _json.loads(_drive(tmp_path).read_text())
    assert slice_["tier_cap"] == 10_000.0
    assert (slice_["tier_equity"] or 0) < 20_000, slice_
    assert (slice_["cash"] or 0) <= 10_000
