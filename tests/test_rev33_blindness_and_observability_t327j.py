# tests/test_rev33_blindness_and_observability_t327j.py
"""T-327j / rev33 — the four fixes from the 2026-09-09 measurement ruling.

1. The agentic price blindness: `query_prices` returned [] on EVERY call in
   production because the lean image ships no data substrate. Staged now — and
   because that substrate is RESEARCH-grade (110 days stale on the day this was
   written), the tool states its own coverage so staleness can never pass as
   currency (the frozen-price defect [NN-FIRST-ARTIFACT] was adopted over).
2. `pull()` could not tell AccessDenied from a first-run missing key — the
   silent-denial shape the T-325 push fix closed, left open on the read side.
3. The kill switch went fleet-wide in rev31; its visibility did not.
"""
import datetime as dt
from pathlib import Path

import pandas as pd

from intelligence.analyst.agentic_readers import build_readers
from paper_trader.cloud_state import _is_denial

ROOT = Path(__file__).resolve().parents[1]
RUNNER = (ROOT / "scripts/run_paper_cloud_day.py").read_text()
BUILD = (ROOT / "scripts/build_paper_image.sh").read_text()


def _price_root(tmp_path, last="2026-05-22"):
    d = tmp_path / "data/processed/tr_reconciled"
    d.mkdir(parents=True)
    pd.DataFrame({"Date": ["2026-05-20", "2026-05-21", last],
                  "Close": [100.0, 101.0, 102.5]}).to_csv(d / "SPY_1d.csv", index=False)
    return tmp_path


# ---------------- 1. the blindness + its honesty ----------------
def test_query_prices_returns_rows_when_the_substrate_is_present(tmp_path):
    r = build_readers(str(_price_root(tmp_path)), "2026-09-09")["query_prices"]({"ticker": "SPY"})
    assert [x for x in r if "close" in x], "the price rows are the whole point"


def test_query_prices_states_its_coverage_and_cannot_be_read_as_a_quote(tmp_path):
    r = build_readers(str(_price_root(tmp_path)), "2026-09-09")["query_prices"]({"ticker": "SPY"})
    marker = r[0]
    assert "close" not in marker, "a coverage marker must never parse as a price"
    assert marker["last_available"] == "2026-05-22" and marker["as_of"] == "2026-09-09"
    assert marker["staleness_days"] == 110
    assert "NOT a live quote feed" in marker["note"]


def test_a_fresh_substrate_reports_zero_staleness(tmp_path):
    r = build_readers(str(_price_root(tmp_path, last="2026-09-09")),
                      "2026-09-09")["query_prices"]({"ticker": "SPY"})
    assert r[0]["staleness_days"] == 0


def test_a_missing_substrate_still_returns_empty_not_a_bare_marker(tmp_path):
    """No data must stay honestly empty — never a marker implying coverage."""
    assert build_readers(str(tmp_path), "2026-09-09")["query_prices"]({"ticker": "SPY"}) == []


def test_the_image_build_refuses_to_ship_the_blindness_again():
    assert "tr_reconciled" in BUILD and "exit 67" in BUILD
    assert "Refusing to build" in BUILD


# ---------------- 2. denied read vs missing key ----------------
def test_denial_is_distinguished_from_a_missing_key():
    assert _is_denial("An error occurred (AccessDenied) when calling GetObject")
    assert _is_denial("fatal error: An error occurred (403) when calling HeadObject")
    assert not _is_denial("An error occurred (404) ... Not Found")   # first run: benign
    assert not _is_denial("")


def test_a_denied_read_flips_canonical_and_says_so():
    assert "pull_denied" in RUNNER
    assert "canonical = bool(v.alive and not v.alert) and not pull_denied" in RUNNER
    assert "DENIED (not a missing key)" in RUNNER


# ---------------- 3. fleet-wide halt visibility ----------------
def test_the_halt_is_resolved_and_recorded_for_every_strategy():
    """Resolved next to the fleet-wide om_halt — NOT inside the llm_analyst branch,
    which is where the only halt read used to live."""
    i_halt = RUNNER.index("_fleet_halt = check_trading_halt")
    i_branch = RUNNER.index('elif args.strategy in ("offense_sso"')
    assert i_halt < i_branch, "the halt must resolve before any per-strategy branch"
    assert "hb.record_halt(_fleet_halt.halted" in RUNNER


def test_recording_the_halt_can_never_break_the_trading_path():
    blk = RUNNER[RUNNER.index("_fleet_halt = check_trading_halt"):][:600]
    assert "except Exception" in blk and "reporting must never break" in blk


def test_heartbeat_exposes_a_top_level_trading_halt_block(tmp_path):
    from paper_trader.heartbeat import PaperHeartbeat
    import json
    hb = PaperHeartbeat(root=str(tmp_path))
    hb.record_halt(True, "halt_file:data/state/TRADING_HALT present")
    blk = json.loads((tmp_path / "data/state/paper_heartbeat.json").read_text())["trading_halt"]
    assert blk["halted"] is True and "halt_file" in blk["reason"] and blk["checked_at"]
