# tests/test_account3_stage2_integration_t329b.py
"""T-329b — the account-3 stage-2 INTEGRATION pass: coid stream prefixes, the
trading kill switch, and the cross-account note pull.

The through-line of every test here: account-3 gains new safety machinery and
account-1's live path gains NOTHING. Its forward record (the gate-d deploy
candidate) must be byte-identical before and after this pass, so the regression
locks are as load-bearing as the new behaviour.
"""
from __future__ import annotations

import json
import types

import pytest

from paper_trader.order_manager import (
    OrderManager, OrderState, TimeInForce, make_client_order_id,
)
from paper_trader.paper_client import FakePaperClient
from paper_trader.trading_halt import (
    HALT_FILE, HaltStatus, TradingHalted, check_trading_halt,
)

CFG = "cfg-hash"
DATE = "2026-08-17"


def _om(tmp_path, **kw):
    return OrderManager(FakePaperClient(), journal_path=str(tmp_path / "orders.jsonl"),
                        reconcile_on_start=False, **kw)


# ---------------------------------------------------------------- coid stream
def test_no_stream_is_byte_identical_to_the_legacy_id():
    """The account-1 regression lock, pinned to a LITERAL — a golden value computed by
    the same function it guards would move silently with the function."""
    import hashlib
    legacy_digest = hashlib.sha1(
        f"{DATE}|SPY|buy|3|{CFG}".encode()).hexdigest()[:16]
    assert (make_client_order_id(DATE, "SPY", "buy", 3, CFG)
            == f"archondex-{DATE}-SPY-{legacy_digest}")
    assert (make_client_order_id(DATE, "SPY", "buy", 3, CFG, stream=None)
            == f"archondex-{DATE}-SPY-{legacy_digest}")


def test_stream_token_prefixes_the_id_and_is_greppable():
    coid = make_client_order_id(DATE, "SPY", "buy", 3, CFG, stream="analyst-a3")
    assert coid.startswith(f"archondex-analyst-a3-{DATE}-SPY-")
    assert len(coid) <= 128                      # Alpaca's client_order_id limit


def test_two_streams_never_collide_on_the_same_order():
    """The netting guard: if the stream only prefixed the id, two streams wanting the
    same (date,ticker,side,qty) would still share a DIGEST — and an id collision at the
    broker silently merges two independent decisions into one fill."""
    a = make_client_order_id(DATE, "SPY", "buy", 3, CFG, stream="analyst-a3")
    b = make_client_order_id(DATE, "SPY", "buy", 3, CFG, stream="events-a3")
    none = make_client_order_id(DATE, "SPY", "buy", 3, CFG)
    assert a != b != none and a != none
    assert a.split("-")[-1] != b.split("-")[-1]  # the DIGESTS differ, not just the prefix


@pytest.mark.parametrize("bad", ["", "Analyst", "a" * 25, "an_alyst", "-a3", "a3-",
                                 "analyst a3", "analyst/a3"])
def test_a_malformed_stream_token_raises_rather_than_being_dropped(bad):
    """A silently-dropped tag produces an UNATTRIBUTABLE order — worse than no order."""
    with pytest.raises(ValueError):
        make_client_order_id(DATE, "SPY", "buy", 3, CFG, stream=bad)


def test_manager_default_stream_tags_every_staged_order(tmp_path):
    om = _om(tmp_path, stream="analyst-a3")
    o = om.stage(DATE, "SPY", "buy", 3, TimeInForce.DAY, CFG)
    assert o.client_order_id.startswith(f"archondex-analyst-a3-{DATE}-SPY-")


def test_per_order_stream_overrides_the_manager_default(tmp_path):
    """The multi-stream door: one container, two decision-sources, one cycle."""
    om = _om(tmp_path, stream="analyst-a3")
    a = om.stage(DATE, "SPY", "buy", 3, TimeInForce.DAY, CFG)
    b = om.stage(DATE, "SPY", "buy", 3, TimeInForce.DAY, CFG, stream="events-a3")
    assert a.client_order_id != b.client_order_id
    assert len(om.orders) == 2                   # two records, NOT one netted order


def test_streamless_manager_stages_the_legacy_id(tmp_path):
    """Account-1's OrderManager passes no stream and must be unchanged."""
    om = _om(tmp_path)
    o = om.stage(DATE, "SPY", "buy", 3, TimeInForce.DAY, CFG)
    assert o.client_order_id == make_client_order_id(DATE, "SPY", "buy", 3, CFG)


# ------------------------------------------------------- the trading kill switch
def _settings(tmp_path, **llm):
    p = tmp_path / "config"
    p.mkdir(parents=True, exist_ok=True)
    (p / "llm_settings.json").write_text(json.dumps({"llm": llm}))
    return str(p / "llm_settings.json")


def test_clear_when_nothing_is_tripped(tmp_path, monkeypatch):
    monkeypatch.delenv("ARCHONDEX_TRADING_KILL_SWITCH", raising=False)
    s = check_trading_halt(root=str(tmp_path), settings_path=_settings(tmp_path))
    assert s.halted is False and s.reason == ""


def test_halt_file_trips_it(tmp_path, monkeypatch):
    monkeypatch.delenv("ARCHONDEX_TRADING_KILL_SWITCH", raising=False)
    f = tmp_path / HALT_FILE
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("halted by ops")
    s = check_trading_halt(root=str(tmp_path), settings_path=_settings(tmp_path))
    assert s.halted and "halt_file" in s.reason


def test_env_var_trips_it(tmp_path, monkeypatch):
    monkeypatch.setenv("ARCHONDEX_TRADING_KILL_SWITCH", "1")
    s = check_trading_halt(root=str(tmp_path), settings_path=_settings(tmp_path))
    assert s.halted and "env:" in s.reason


def test_spend_kill_switch_implies_the_trading_halt(tmp_path, monkeypatch):
    """THE TIMING HOLE. Halting spend on day D stops day-D's note, but day-D orders come
    from day D-1's note, which is already on disk — so a spend-only halt keeps trading."""
    monkeypatch.delenv("ARCHONDEX_TRADING_KILL_SWITCH", raising=False)
    s = check_trading_halt(root=str(tmp_path),
                           settings_path=_settings(tmp_path, kill_switch=True))
    assert s.halted and "kill_switch" in s.reason


def test_trading_kill_switch_alone_halts_trading(tmp_path, monkeypatch):
    monkeypatch.delenv("ARCHONDEX_TRADING_KILL_SWITCH", raising=False)
    s = check_trading_halt(root=str(tmp_path),
                           settings_path=_settings(tmp_path, trading_kill_switch=True))
    assert s.halted and "trading_kill_switch" in s.reason


def test_unreadable_settings_FAIL_CLOSED_to_halted(tmp_path, monkeypatch):
    monkeypatch.delenv("ARCHONDEX_TRADING_KILL_SWITCH", raising=False)
    p = tmp_path / "config"; p.mkdir()
    (p / "llm_settings.json").write_text("{not json")
    s = check_trading_halt(root=str(tmp_path), settings_path=str(p / "llm_settings.json"))
    assert s.halted and "settings_unreadable" in s.reason


def test_missing_settings_FAIL_CLOSED_to_halted(tmp_path, monkeypatch):
    monkeypatch.delenv("ARCHONDEX_TRADING_KILL_SWITCH", raising=False)
    s = check_trading_halt(root=str(tmp_path), settings_path=str(tmp_path / "nope.json"))
    assert s.halted


# ---------------------------------------- the switch on the real submit() path
def test_submit_refuses_and_the_order_never_reaches_the_broker(tmp_path):
    om = _om(tmp_path, stream="analyst-a3",
             halt_check=lambda: HaltStatus(True, "config:llm.kill_switch"))
    o = om.stage(DATE, "SPY", "buy", 3, TimeInForce.DAY, CFG)
    with pytest.raises(TradingHalted):
        om.submit(o)
    assert o.state == OrderState.REJECTED.value
    assert o.reject_reason.startswith("trading_halt:")
    assert om.client.submitted == []             # nothing was POSTed


def test_a_halt_refuses_SELLS_TOO_it_never_liquidates(tmp_path):
    """A kill switch that let sells through would force-sell the book at exactly the
    moment an operator is most likely to pull it. Halt = stop new actions, never sell."""
    om = _om(tmp_path, stream="analyst-a3",
             halt_check=lambda: HaltStatus(True, "halt_file:present"))
    o = om.stage(DATE, "SPY", "sell", 3, TimeInForce.DAY, CFG)
    with pytest.raises(TradingHalted):
        om.submit(o)
    assert om.client.submitted == []


def test_the_refusal_is_journaled_with_a_typed_reason(tmp_path):
    om = _om(tmp_path, stream="analyst-a3",
             halt_check=lambda: HaltStatus(True, "env:ARCHONDEX_TRADING_KILL_SWITCH=1"))
    o = om.stage(DATE, "SPY", "buy", 3, TimeInForce.DAY, CFG)
    with pytest.raises(TradingHalted):
        om.submit(o)
    events = [r["event"] for r in om.journal.read_all()]
    assert "trading_halt_refused" in events      # a silent refusal is not a refusal


def test_a_RAISING_halt_check_is_itself_a_halt(tmp_path):
    """Fail-closed: we do not trade on a safety control we could not read."""
    def boom():
        raise RuntimeError("s3 unreachable")
    om = _om(tmp_path, stream="analyst-a3", halt_check=boom)
    o = om.stage(DATE, "SPY", "buy", 3, TimeInForce.DAY, CFG)
    with pytest.raises(TradingHalted):
        om.submit(o)
    assert "halt_check_raised" in o.reject_reason
    assert om.client.submitted == []


def test_the_switch_is_resolved_PER_SUBMIT_not_cached(tmp_path):
    """An operator who trips the switch must stop the next ORDER, not the next run."""
    state = {"halted": False}
    om = _om(tmp_path, stream="analyst-a3",
             halt_check=lambda: HaltStatus(state["halted"], "flipped" if state["halted"] else ""))
    a = om.stage(DATE, "SPY", "buy", 3, TimeInForce.DAY, CFG)
    om.submit(a)
    assert a.state != OrderState.REJECTED.value
    state["halted"] = True
    b = om.stage(DATE, "AGG", "buy", 4, TimeInForce.DAY, CFG)
    with pytest.raises(TradingHalted):
        om.submit(b)


def test_account1_path_is_byte_neutral_no_halt_check_consulted(tmp_path):
    """halt_check=None ⇒ submit() must not consult ANYTHING new. Regression lock."""
    om = _om(tmp_path)                            # no stream, no halt_check
    assert om.halt_check is None and om.stream is None
    o = om.stage(DATE, "SPY", "buy", 3, TimeInForce.DAY, CFG)
    om.submit(o)
    assert o.state != OrderState.REJECTED.value
    assert om.client.submitted[0]["client_order_id"] == make_client_order_id(
        DATE, "SPY", "buy", 3, CFG)


# --------------------------------------------- the cross-account note pull
def _cloud(tmp_path, rc=0, prefix="paper_state_ai_trader"):
    from paper_trader.cloud_state import CloudState, CloudStateConfig
    c = CloudState(CloudStateConfig(bucket="b", prefix=prefix), root=str(tmp_path))
    calls = []

    def fake(*args):
        calls.append(args)
        if args[:2] == ("s3", "sync") and rc == 0:
            # simulate a landed note so n_files is real, not asserted into existence
            d = tmp_path / "data/intel/analyst_notes"
            d.mkdir(parents=True, exist_ok=True)
            (d / "2026-08-14.json").write_text("{}")
        return types.SimpleNamespace(returncode=rc, stderr="denied")
    c._aws = fake
    return c, calls


def test_cross_pull_reads_the_SOURCE_prefix_and_writes_locally(tmp_path):
    c, calls = _cloud(tmp_path)
    out = c.pull_readonly_from("paper_state", ["data/intel/analyst_notes"])
    assert out["ok"] is True
    assert out["rels"]["data/intel/analyst_notes"]["n_files"] == 1
    src, dst = calls[0][2], calls[0][3]
    assert src == "s3://b/paper_state/data/intel/analyst_notes"
    assert dst.endswith("data/intel/analyst_notes")


def test_cross_pull_is_READ_ONLY_it_never_writes_the_source(tmp_path):
    """If this ever pushed, account-3 would overwrite account-1's memory."""
    c, calls = _cloud(tmp_path)
    c.pull_readonly_from("paper_state", ["data/intel/analyst_notes"])
    for args in calls:
        # every s3 op must have the SOURCE prefix on the left (download direction)
        assert args[2].startswith("s3://b/paper_state/")
        assert not args[3].startswith("s3://")


def test_a_failed_cross_pull_reports_NOT_OK_so_a_hold_reads_as_degraded(tmp_path):
    """The distinction that matters: 'no note was written' vs 'the pull failed'. A
    fail-closed HOLD is honest evidence only if the note was actually reachable."""
    c, _ = _cloud(tmp_path, rc=1)
    out = c.pull_readonly_from("paper_state", ["data/intel/analyst_notes"])
    assert out["ok"] is False
    assert out["rels"]["data/intel/analyst_notes"]["error"]


def test_same_prefix_is_a_stated_noop_not_a_pointless_self_sync(tmp_path):
    c, calls = _cloud(tmp_path, prefix="paper_state")
    out = c.pull_readonly_from("paper_state", ["data/intel/analyst_notes"])
    assert out["ok"] is True and "own prefix" in out["reason"] and calls == []


def test_notes_dir_is_not_in_this_accounts_push_set():
    """The drift guard: account-3 PULLS the notes but must never PUSH them, or the two
    accounts' note records diverge and neither is authoritative."""
    from paper_trader.cloud_state import DURABLE_PATHS
    assert "data/intel/analyst_notes" not in DURABLE_PATHS


# ------------------------------------------------- note staleness (a stalled feed)
HEX64 = "a" * 64


def _note_on_disk(tmp_path, as_of, sym="SPY", w=0.10, raw_as_of=None):
    """A note that REALLY validates — the constructor independently re-validates on
    load, so a schema-sloppy fixture would prove nothing about the staleness path."""
    from intelligence.analyst.note_schema import validate_note
    d = tmp_path / "data/intel/analyst_notes"
    d.mkdir(parents=True, exist_ok=True)
    payload = {"as_of": as_of, "market_assessment": "test",
               "hypothetical_actions": [{"account": "shadow", "symbol": sym,
                                         "set_weight": w, "target_weight": w}],
               "provenance": {"model_id_requested": "m", "model_id_served": "m",
                              "prompt_version": "daily/v2", "prompt_sha256": HEX64,
                              "input_bundle_sha256": HEX64},
               "usage": {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0}}
    if raw_as_of is None:
        assert validate_note(payload)[0] is not None, "fixture note must validate"
    else:
        payload["as_of"] = raw_as_of      # deliberately unageable, for the fail-closed test
    (d / f"note_{as_of}.json").write_text(json.dumps(payload))
    return d


def _closes(*syms):
    import pandas as pd
    idx = pd.to_datetime(["2026-08-10", "2026-08-11", "2026-08-12"])
    return {s: pd.Series([100.0, 101.0, 100.0], index=idx) for s in syms}


def _ctor(tmp_path, trade_date, **kw):
    from paper_trader.llm_analyst_constructor import LLMAnalystConstructor
    return LLMAnalystConstructor(trade_date=trade_date, root=str(tmp_path), **kw)


def test_a_fresh_note_is_acted_on(tmp_path):
    _note_on_disk(tmp_path, "2026-08-14")
    plan = _ctor(tmp_path, "2026-08-17").construct(10_000.0, {}, _closes("SPY"))
    assert plan.reject_reason is None and plan.note_as_of == "2026-08-14"
    assert plan.target_qty["SPY"] == 10          # floor(10000*0.10/100)


def test_a_STALE_note_HOLDS_rather_than_trading_a_weeks_old_belief(tmp_path):
    """The stalled-feed guard. Without a bound, `as_of < trade_date` keeps the newest
    note on disk eligible FOREVER — the account would go on acting on a belief formed
    before the feed died, and the record would look like a healthy no-change day."""
    _note_on_disk(tmp_path, "2026-07-20")        # 28 days old
    plan = _ctor(tmp_path, "2026-08-17").construct(10_000.0, {}, _closes("SPY"))
    assert plan.orders == [] and plan.degraded is True
    assert "stale_note" in plan.reject_reason and "STALLED" in plan.reject_reason


def test_the_staleness_bound_is_inclusive_at_the_limit(tmp_path):
    _note_on_disk(tmp_path, "2026-08-12")        # exactly 5 days
    plan = _ctor(tmp_path, "2026-08-17", max_note_age_days=5).construct(
        10_000.0, {}, _closes("SPY"))
    assert plan.reject_reason is None


def test_an_unageable_note_date_FAILS_CLOSED(tmp_path):
    """A note we cannot age is a note we cannot trust — never 'assume it's fresh'."""
    _note_on_disk(tmp_path, "2026-08-14", raw_as_of="2026-08-1")
    plan = _ctor(tmp_path, "2026-08-17").construct(10_000.0, {}, _closes("SPY"))
    assert plan.orders == [] and "unparseable_note_date" in plan.reject_reason


# ------------------------------- the family pipeline, end to end (account-3)
def _family(tmp_path, *, halted, positions=None):
    """Drive the SHARED fleet pipeline with the LLM constructor — the same
    _run_family_strategy accounts 2/3 use, which is the point of stage 2: the AI
    supplies target weights and rides the existing deterministic stack unchanged."""
    import datetime as dt
    import numpy as np
    import pandas as pd
    from paper_trader import PaperConfig
    from paper_trader.llm_analyst_constructor import LLMAnalystConstructor
    from scripts.run_paper_cloud_day import _run_family_strategy

    idx = pd.date_range("2026-05-01", periods=70, freq="B")
    closes = {t: pd.Series(np.linspace(100.0, 100.0, 70), index=idx)
              for t in ("SPY", "AGG", "GLD")}
    today = idx[-1].date() + dt.timedelta(days=1)
    # yesterday's note — signal-t / fill-t+1, the look-ahead-impossible contract
    _note_on_disk(tmp_path, (today - dt.timedelta(days=1)).isoformat(),
                  sym="SPY", w=0.10)

    class _Data:
        def fetch_daily_closes(self, tickers, lookback_days=400):
            return {t: closes[t] for t in tickers if t in closes}

        def get_account(self):
            return {"equity": 100_000.0, "cash": 100_000.0}

        def fetch_latest_prices(self, tickers):
            return {t: 100.0 for t in tickers}

    om = OrderManager(FakePaperClient(), journal_path=str(tmp_path / "o.jsonl"),
                      reconcile_on_start=False, stream="analyst-a3",
                      halt_check=lambda: HaltStatus(halted, "test-halt" if halted else ""))
    ctor = LLMAnalystConstructor(trade_date=str(today), root=str(tmp_path), tif="day",
                                 sub_budget=1.0, allowlist=("SPY", "AGG", "GLD"),
                                 max_note_age_days=100_000)   # age is not what's under test
    out = _run_family_strategy(
        constructor=ctor, fetch_universe=("SPY", "AGG", "GLD"),
        tracking_universe=("SPY", "AGG", "GLD"), client=_Data(), om=om,
        cfg=PaperConfig(allocator="mean_variance"), today=today,
        broker_positions=positions or {}, cap=10_000.0,
        stream="analyst-a3", stage_orders=not halted)
    return out, om


def test_the_account3_pipeline_stages_stream_tagged_orders(tmp_path):
    (plan, _, staged, _, _, sizing, equity, _), _om_ = _family(tmp_path, halted=False)
    assert sizing == 10_000.0 and equity == 100_000.0     # the $10k sub-budget, capped
    assert plan.targets["SPY"] == 0.10
    assert [o.ticker for o in staged] == ["SPY"]
    assert staged[0].qty == 10                            # floor(10000*0.10/100)
    assert staged[0].client_order_id.startswith("archondex-analyst-a3-")


def test_a_HALT_constructs_the_plan_but_stages_NOTHING(tmp_path):
    """The record must show what the halt PREVENTED — otherwise 'the switch works' is
    indistinguishable from 'the switch is pointed at a dead stream'."""
    (plan, _, staged, _, _, _, _, _), om = _family(tmp_path, halted=True)
    assert plan.orders and plan.targets["SPY"] == 0.10    # the intent is on the record
    assert staged == []                                   # ...and nothing was staged
    assert om.orders == {}                                # ...nor journaled as an order


def test_a_halted_day_cannot_reach_the_broker_even_if_something_stages(tmp_path):
    """Defence in depth: the driver skips staging, AND submit() refuses independently."""
    (plan, _, _, _, _, _, _, _), om = _family(tmp_path, halted=True)
    sneaked = om.stage("2026-08-17", "SPY", "buy", 10, TimeInForce.DAY, CFG)
    with pytest.raises(TradingHalted):
        om.submit(sneaked)
    assert om.client.submitted == []


def test_sub_budget_of_one_means_the_whole_capped_slice(tmp_path):
    """The answered decision: $10k sub-budget = min(equity, cap) × sub_budget(1.0)."""
    _note_on_disk(tmp_path, "2026-08-14", w=0.20)
    plan = _ctor(tmp_path, "2026-08-17", sub_budget=1.0).construct(
        10_000.0, {}, _closes("SPY"))
    assert plan.target_qty["SPY"] == 20          # floor(10000*0.20/100)
    half = _ctor(tmp_path, "2026-08-17", sub_budget=0.5).construct(
        10_000.0, {}, _closes("SPY"))
    assert half.target_qty["SPY"] == 10          # a second stream takes its OWN slice
