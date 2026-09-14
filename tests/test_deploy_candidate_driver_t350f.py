# tests/test_deploy_candidate_driver_t350f.py
"""T-350f — EXECUTE the deploy_candidate branch of main(), end to end.

Why this file exists: the arrival event failed closed on 2026-09-14 with

    NameError: name 'sleeve_cap' is not defined

— a leftover from the constructor's dollars-based design that survived the
refactor to the fleet's FRACTION idiom. 53 tests were green: they exercised the
constructor directly, and the wiring tests read main() as TEXT. Nothing ever RAN
this branch, so the first scheduled firing found the seam ([NN-FIRST-ARTIFACT]
doing exactly what it exists for). Text assertions cannot catch an undefined
name; only execution can.
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import types

import pandas as pd
import pytest

import scripts.run_paper_cloud_day as drv
from paper_trader.paper_client import FakePaperClient


class _Cloud:
    def __init__(self):
        self.metrics = []
        self.cfg = types.SimpleNamespace(enabled=False, s3_root="LOCAL", prefix="x")

    def pull(self):
        return False

    def push(self):
        return True

    def emit_metrics(self, *, happened, canonical):
        self.metrics.append((happened, canonical))

    def pull_readonly_from(self, source_prefix, rels):
        pass


def _drive(tmp_path, cap="10000", positions=None):
    today = dt.date(2026, 9, 15)
    now = dt.datetime(2026, 9, 15, 9, 50, tzinfo=dt.timezone.utc)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config/deploy_candidate.json").write_text(json.dumps({
        "core": {"ticker": "VOO", "weight": 0.85},
        "satellite": {"ticker": "MTUM", "weight": 0.15},
        "cash_ticker": "SGOV",
        "bands": {"buy_quanta": 1.5, "sell_quanta": 1.0, "max_drift": 0.10},
        "contributions": {"enabled": True, "monthly_usd": 583.0,
                          "start_date": "2026-09-11"}}))
    # the ENFORCING wash guard needs its equivalence classes or it refuses to
    # trade (fail-closed by design) — copy the real ones so the test exercises
    # the production classes, not a stand-in
    shutil.copy("config/substantially_identical.json",
                tmp_path / "config/substantially_identical.json")
    # the fleet halt check reads this and FAILS CLOSED when unreadable (an
    # unreadable control IS a halt) — the fixture must supply it or the run
    # correctly halts before reaching the branch under test
    (tmp_path / "config/llm_settings.json").write_text(json.dumps(
        {"llm": {"kill_switch": False, "trading_kill_switch": False,
                 "monthly_budget_usd": 30.0, "max_output_tokens": 1500}}))
    idx = pd.bdate_range(end=pd.Timestamp(today) - pd.Timedelta(days=1), periods=80)
    px = {"VOO": 600.0, "MTUM": 230.0, "SGOV": 100.0,
          "SPY": 600.0, "AGG": 98.0, "GLD": 420.0}
    series = {t: pd.Series([v] * len(idx), index=idx) for t, v in px.items()}

    class _C(FakePaperClient):
        def get_account(self):
            return {"equity": 100_000.0, "cash": 100_000.0, "status": "ACTIVE"}

        def list_positions(self):
            return [{"symbol": s, "qty": q} for s, q in (positions or {}).items()]

        def fetch_daily_closes(self, tickers, lookback_days=400):
            return {t: series[t] for t in tickers if t in series}

        def fetch_latest_prices(self, tickers):
            return {t: px[t] for t in tickers if t in px}

        def trading_days(self, start, end):
            return {today}

    argv = ["--allocator", "mean_variance", "--strategy", "deploy_candidate"]
    if cap is not None:
        argv += ["--sleeve-notional-cap", cap]
    cloud = _Cloud()
    rc = drv.main(argv, now=now, client=_C(), cloud=cloud, root=str(tmp_path))
    return rc, cloud


def test_the_branch_RUNS_this_is_the_test_that_was_missing(tmp_path, capsys):
    """THE REGRESSION. Before the fix this raised NameError('sleeve_cap')."""
    rc, cloud = _drive(tmp_path)
    out = capsys.readouterr().out
    assert "DEPLOY-CAND" in out, "the branch never executed"
    assert rc == 0, f"deploy_candidate run did not complete cleanly (rc={rc})"


def test_the_arrival_shape_holds_three_buys_no_sells(tmp_path, capsys):
    """The pre-stated SHAPE (docs/Measurements/2026-09/act2_arrival_event_t350.md):
    from flat, every leg is an add, both rounded DOWN, SGOV takes the residue."""
    _drive(tmp_path)
    out = capsys.readouterr().out
    assert "'VOO', 'buy', 14" in out or "('VOO', 'buy', 14)" in out, out[-1500:]
    assert "('MTUM', 'buy', 6)" in out
    assert "sell" not in out.split("DEPLOY-CAND")[-1].split("3. CYCLE")[0].lower()


def test_the_CONTRIBUTED_cap_is_what_sizes_the_book(tmp_path, capsys):
    """Item 4's whole point: the budget grows with Rule-B. Month 0 adds $0, and
    the uplift is stated every run so it can never grow silently."""
    _drive(tmp_path)
    out = capsys.readouterr().out
    assert "contributions:" in out and "no broker money moves" in out


def test_an_uncapped_deploy_candidate_REFUSES_to_size_off_full_equity(tmp_path):
    """[NN-FAIL-CLOSED]: the tier IS the rehearsal. Without a cap this account
    would size off ~$100k equity and call it a $10k arrival — the notional-cap
    bypass class, refused loudly instead."""
    rc, cloud = _drive(tmp_path, cap=None)
    assert rc == 69
    assert cloud.metrics and cloud.metrics[-1] == (True, False)
