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

from intelligence.analyst.agentic_readers import build_coverage, build_readers
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


def test_query_prices_keeps_its_pure_row_contract(tmp_path):
    """The coverage rides as PRESENTATION, not inside the reader's rows — the
    homogeneous-row contract predates this fix and its PIT test stays untouched."""
    r = build_readers(str(_price_root(tmp_path)), "2026-09-09")["query_prices"]({"ticker": "SPY"})
    assert all(set(x) == {"date", "close"} for x in r)


def test_the_model_is_told_the_substrate_is_stale_not_current(tmp_path):
    from intelligence.analyst.agentic_tools import AgenticTools
    root = str(_price_root(tmp_path))
    tools = AgenticTools(readers=build_readers(root, "2026-09-09"),
                         coverage=build_coverage(root, "2026-09-09"))
    text, is_err = tools.execute("query_prices", {"ticker": "SPY"})
    assert is_err is False
    assert '"close": 102.5' in text                      # the data still arrives
    assert "[coverage]" in text and '"staleness_days": 110' in text
    assert "NOT a live quote feed" in text


def test_coverage_is_never_offered_as_a_tool_and_readers_stay_six(tmp_path):
    """Both pre-existing guards hold UNMODIFIED: build_readers' exact six-key
    allowlist, and the tool surface the model is offered."""
    from intelligence.analyst.agentic_tools import AgenticTools
    root = str(_price_root(tmp_path))
    assert len(build_readers(root, "2026-09-09")) == 6
    tools = AgenticTools(readers=build_readers(root, "2026-09-09"),
                         coverage=build_coverage(root, "2026-09-09"))
    assert "query_prices" in {s["name"] for s in tools.specs()}
    assert len(tools.specs()) == 6


def test_a_fresh_substrate_reports_zero_staleness(tmp_path):
    from intelligence.analyst.agentic_tools import AgenticTools
    root = str(_price_root(tmp_path, last="2026-09-09"))
    tools = AgenticTools(readers=build_readers(root, "2026-09-09"),
                         coverage=build_coverage(root, "2026-09-09"))
    text, _ = tools.execute("query_prices", {"ticker": "SPY"})
    assert '"staleness_days": 0' in text


def test_a_missing_substrate_claims_NO_coverage_rather_than_going_silent(tmp_path):
    """The intent here has always been 'never imply coverage you do not have'.
    Originally that was enforced as SILENCE; T-350e showed silence is the worse
    failure — an unexplained empty is what made the first price_fed note conclude
    it had no prices. So the rule is now enforced positively: say there is no
    store, which claims less than silence did and tells the reader more."""
    from intelligence.analyst.agentic_tools import AgenticTools
    assert build_readers(str(tmp_path), "2026-09-09")["query_prices"]({"ticker": "SPY"}) == []
    tools = AgenticTools(readers=build_readers(str(tmp_path), "2026-09-09"),
                         coverage=build_coverage(str(tmp_path), "2026-09-09"))
    text, _ = tools.execute("query_prices", {"ticker": "SPY"})
    assert "no price store for this ticker at all" in text
    assert "UNAVAILABLE" in text and "do not infer a level" in text


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


# ---------------- T-350e: the EMPTY case, from the real first price_fed note ----
def test_an_out_of_coverage_window_EXPLAINS_ITSELF(tmp_path):
    """THE REGRESSION, reproduced from the live artifact.

    The first price_fed note (2026-09-11) asked for SPY 2026-08-01→2026-09-11 — a
    sensible "recent prices" window — and got n_results: 0, because the RESEARCH
    substrate ends 2026-05-22. Coverage returned None on an empty result, so no
    explanation was attached, and the arm concluded "no live price history" in its
    note. A full store, an empty answer, and nothing saying why: the silent-zero
    shape reproduced inside the fix meant to end it.
    """
    from intelligence.analyst.agentic_readers import build_coverage
    from intelligence.analyst.agentic_tools import AgenticTools
    root = str(_price_root(tmp_path))          # store ends 2026-05-22
    tools = AgenticTools(readers=build_readers(root, "2026-09-11"),
                         coverage=build_coverage(root, "2026-09-11"))
    text, is_err = tools.execute(
        "query_prices", {"ticker": "SPY", "date_from": "2026-08-01",
                         "date_to": "2026-09-11"})
    assert is_err is False
    assert "[coverage]" in text, "an empty answer must never be silent"
    assert '"store_covers": "2026-05-20' in text and '2026-05-22"' in text
    assert "outside the store's coverage" in text
    assert "NOT because prices do not exist" in text


def test_an_unknown_ticker_says_UNAVAILABLE_not_out_of_window(tmp_path):
    """The two empties are different facts and must not read the same."""
    from intelligence.analyst.agentic_readers import build_coverage
    from intelligence.analyst.agentic_tools import AgenticTools
    root = str(_price_root(tmp_path))
    tools = AgenticTools(readers=build_readers(root, "2026-09-11"),
                         coverage=build_coverage(root, "2026-09-11"))
    text, _ = tools.execute("query_prices", {"ticker": "NOSUCH"})
    assert "no price store for this ticker at all" in text
    assert "do not infer a level" in text
