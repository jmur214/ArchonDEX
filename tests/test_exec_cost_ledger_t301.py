"""T-301 / P2.1 — the execution-cost ledger: the single freshness gate, the
no-fabricated-samples doctrine, append-only accrual, and report-only aggregation."""
from __future__ import annotations

import datetime as dt
import json

from paper_trader.exec_cost_ledger import (ExecCostLedger, extract_fresh_fills,
                                           ExecCostRow)
from paper_trader.heartbeat import PaperHeartbeat

ARRIVAL_TS = dt.datetime(2026, 7, 10, 13, 45, 0, tzinfo=dt.timezone.utc)


class _O:
    """A minimal staged-order stand-in (the fields extract_fresh_fills reads)."""
    def __init__(self, ticker, side="buy", filled_qty=10, filled_avg_price=100.0,
                 filled_at="2026-07-10T13:45:30+00:00"):
        self.ticker = ticker
        self.side = side
        self.filled_qty = filled_qty
        self.filled_avg_price = filled_avg_price
        self.filled_at = filled_at


# --- the single freshness gate --------------------------------------------- #
def test_fresh_fill_becomes_a_row_with_slippage_and_latency():
    o = _O("SSO", filled_avg_price=100.05, filled_at="2026-07-10T13:45:30+00:00")
    rows, stale = extract_fresh_fills([o], {"SSO": 100.0}, ARRIVAL_TS,
                                      account="offense-sso", trade_date="2026-07-10")
    assert not stale and len(rows) == 1
    r = rows[0]
    assert r.instrument == "SSO" and r.account == "offense-sso"
    assert r.slippage_bps == 5.0            # |100.05-100|/100 * 1e4
    assert r.fill_latency_s == 30.0
    assert r.notional == round(100.05 * 10, 2)


def test_stale_fill_is_EXCLUDED_never_fabricated():
    # a fill timestamped BEFORE the arrival capture = the 146bps-artifact class
    o = _O("SSO", filled_at="2026-07-10T13:00:00+00:00")   # 45min before arrival
    rows, stale = extract_fresh_fills([o], {"SSO": 100.0}, ARRIVAL_TS,
                                      account="offense-sso", trade_date="2026-07-10")
    assert rows == [] and stale == ["SSO"]


def test_unparseable_filled_at_is_excluded_fail_closed():
    o = _O("SSO", filled_at="not-a-timestamp")
    rows, stale = extract_fresh_fills([o], {"SSO": 100.0}, ARRIVAL_TS,
                                      account="a", trade_date="d")
    assert rows == [] and stale == ["SSO"]


def test_no_arrival_ts_excludes_all():
    rows, stale = extract_fresh_fills([_O("SSO")], {"SSO": 100.0}, None,
                                      account="a", trade_date="d")
    assert rows == [] and stale == ["SSO"]


def test_zero_qty_or_missing_price_is_skipped_not_stale():
    unfilled = _O("SSO", filled_qty=0, filled_avg_price=None)
    no_arrival = _O("AGG")
    rows, stale = extract_fresh_fills([unfilled, no_arrival], {"SSO": 100.0},
                                      ARRIVAL_TS, account="a", trade_date="d")
    # unfilled → skipped silently (not a stale exclusion); AGG has no arrival px
    assert rows == [] and stale == []


# --- append-only accrual + aggregation ------------------------------------- #
def _row(acct, inst, date, bps, lat=30.0, notional=1000.0):
    return ExecCostRow(account=acct, instrument=inst, trade_date=date, side="buy",
                       qty=10, fill_px=100.0, arrival_px=100.0, notional=notional,
                       slippage_bps=bps, fill_latency_s=lat,
                       filled_at="2026-07-10T13:45:30+00:00",
                       arrival_ts=ARRIVAL_TS.isoformat())


def test_append_only_accrues_across_runs(tmp_path):
    p = str(tmp_path / "ecl.jsonl")
    ExecCostLedger(p).append([_row("offense-sso", "SSO", "2026-07-10", 2.2)])
    ExecCostLedger(p).append([_row("offense-sso", "SSO", "2026-07-11", 3.0)])
    rows = ExecCostLedger(p).load()
    assert len(rows) == 2 and rows[0]["trade_date"] == "2026-07-10"


def test_empty_append_is_a_noop(tmp_path):
    p = str(tmp_path / "ecl.jsonl")
    assert ExecCostLedger(p).append([]) == 0
    assert ExecCostLedger(p).load() == []


def test_aggregate_median_and_n_per_instrument(tmp_path):
    p = str(tmp_path / "ecl.jsonl")
    ecl = ExecCostLedger(p)
    ecl.append([_row("offense-sso", "SSO", "2026-07-10", 2.0),
                _row("offense-sso", "SSO", "2026-07-11", 4.0),
                _row("offense-sso", "SSO", "2026-07-12", 6.0),
                _row("account-1", "SPY", "2026-07-10", 0.5)])
    agg = ecl.aggregate()
    assert agg["n_rows"] == 4 and agg["n_instruments"] == 2
    sso = agg["per_instrument"]["offense-sso|SSO"]
    assert sso["n"] == 3 and sso["median_slippage_bps"] == 4.0
    assert sso["first_date"] == "2026-07-10" and sso["last_date"] == "2026-07-12"
    assert agg["per_instrument"]["account-1|SPY"]["median_slippage_bps"] == 0.5


def test_aggregate_notional_weighted_mean(tmp_path):
    p = str(tmp_path / "ecl.jsonl")
    ecl = ExecCostLedger(p)
    # 2bps on $3000 + 10bps on $1000 → wt mean = (2*3000+10*1000)/4000 = 4.0
    ecl.append([_row("a", "X", "2026-07-10", 2.0, notional=3000.0),
                _row("a", "X", "2026-07-11", 10.0, notional=1000.0)])
    assert ecl.aggregate()["per_instrument"]["a|X"]["notional_wt_mean_bps"] == 4.0


def test_torn_last_line_does_not_poison_load(tmp_path):
    p = tmp_path / "ecl.jsonl"
    ExecCostLedger(str(p)).append([_row("a", "X", "2026-07-10", 2.0)])
    with open(p, "a") as fh:
        fh.write('{"partial": ')   # a torn write
    assert len(ExecCostLedger(str(p)).load()) == 1


# --- report-only on the heartbeat ------------------------------------------ #
def test_record_exec_cost_never_touches_canonical(tmp_path):
    hb = PaperHeartbeat(status_path=str(tmp_path / "hb.json"),
                        alert_log=str(tmp_path / "a.log"))
    hb.record_run("2026-07-10", reconcile_clean_cycles=3, reconcile_total_cycles=3,
                  halted=False, submitted=0, fills=0, account_explained=True)
    ecl = ExecCostLedger(str(tmp_path / "ecl.jsonl"))
    ecl.append([_row("offense-sso", "SSO", "2026-07-10", 2.2)])
    hb.record_exec_cost_ledger(ecl.aggregate())
    st = json.loads((tmp_path / "hb.json").read_text())
    assert st["last_run"]["canonical"] is True and st["alert"] is False
    assert st["exec_cost"]["per_instrument"]["offense-sso|SSO"]["median_slippage_bps"] == 2.2
    assert st["exec_cost"]["_schema"] == "exec_cost_agg/v1"
    # exec-cost fires NO alert line (unlike econ-health tripwires)
    assert not (tmp_path / "a.log").exists()


def test_gateb_median_matches_ledger_rows(tmp_path):
    # the SAME extractor feeds both → the gate-b mean equals the mean of the
    # ledger rows' slippage (no path divergence).
    orders = [_O("SPY", filled_avg_price=100.05), _O("AGG", filled_avg_price=100.10)]
    arrival = {"SPY": 100.0, "AGG": 100.0}
    rows, _ = extract_fresh_fills(orders, arrival, ARRIVAL_TS, account="a", trade_date="d")
    mean_from_rows = round(sum(r.slippage_bps for r in rows) / len(rows), 2)
    assert mean_from_rows == 7.5   # (5 + 10)/2
