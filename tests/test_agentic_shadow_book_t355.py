# tests/test_agentic_shadow_book_t355.py
"""T-355 — the agentic arm gets the book that fits its output.

D's T-356 finding #5: `analyst_desk_book.json` was DURABLE while its source
`data/intel/agentic_analyst_calls.jsonl` had NO WRITER anywhere — the inverse of
C's T-351 defect. Both read "too early to say" forever; only a liveness check can
see this one.

The verdict was RETIRE, not wire. Evidence from the live artifact: 36 durable
sessions with `open: 0, closed: 0` and not one day carrying a call, because the
agentic analyst emits `hypothetical_actions` — continuous TARGET WEIGHTS — and
never event-style calls with horizons. Writing a feed the arm does not produce,
purely to make a check go green, would have manufactured a live channel to
satisfy a metric.

What the arm needed was the machinery that already fits weights: LlmShadowBook,
which books the constrained arm. It was already parameterized, so this is a
second instantiation — REPOINT over REBUILD.
"""
from __future__ import annotations

import json
from pathlib import Path

from paper_trader.llm_shadow_book import LlmShadowBook

AGENTIC_DIR = "data/intel/analyst_notes_agentic"
AGENTIC_BOOK = "data/state/llm_shadow_book_agentic.json"

# THE REAL 2026-09-15 agentic note, vendored from
# s3://…/paper_state/data/intel/analyst_notes_agentic/note_2026-09-15.json.
#
# It is the real one on purpose. The first draft of this test used a synthetic
# note that looked right and failed `validate_note` with 10 errors — the shadow
# book re-validates before booking, so a hand-written fixture would have "proved"
# the arm worked while the live note took a different path. Locking from the
# artifact is the house pattern for exactly this reason.
#
# Note its `hypothetical_actions`: set_weight/target_weight entries with no
# horizon anywhere. That is why the retired call-driven desk could never have
# consumed this feed, no matter where its source_path pointed.
FIXTURE = Path(__file__).parent / "fixtures" / "agentic_note_2026-09-15.json"


def _agentic_note(as_of: str) -> dict:
    note = json.loads(FIXTURE.read_text())
    note["as_of"] = as_of
    return note


def _seed(tmp_path, directory, as_of="2026-09-15"):
    d = tmp_path / directory
    d.mkdir(parents=True, exist_ok=True)
    (d / f"note_{as_of}.json").write_text(json.dumps(_agentic_note(as_of)))


def test_the_agentic_arm_books_its_weights(tmp_path):
    """THE FIRST ARTIFACT, at unit level: the arm's own book accrues a point."""
    _seed(tmp_path, AGENTIC_DIR)
    b = LlmShadowBook(root=str(tmp_path), path=AGENTIC_BOOK, notes_dir=AGENTIC_DIR)
    note, reason = b._load_yesterday_note("2026-09-16")
    assert note is not None, f"the agentic note was not picked up: {reason}"
    s = b.record("2026-09-16", closes={"SPY": 600.0, "AGG": 98.0}, note=note,
                 note_reason=reason)
    assert s["n_days"] >= 1
    assert (tmp_path / AGENTIC_BOOK).exists(), "the agentic book was never written"


def test_the_two_arms_never_share_a_book(tmp_path):
    """The A/B is only a comparison if each arm has its OWN record. A shared file
    would blend the treatment into the control — the laboratory's never-blend rule
    applied to information cohorts."""
    _seed(tmp_path, AGENTIC_DIR)
    _seed(tmp_path, "data/intel/analyst_notes")
    con = LlmShadowBook(root=str(tmp_path))
    agn = LlmShadowBook(root=str(tmp_path), path=AGENTIC_BOOK, notes_dir=AGENTIC_DIR)
    assert con._file() != agn._file()
    assert con.notes_dir != agn.notes_dir
    agn.record("2026-09-16", closes={"SPY": 600.0, "AGG": 98.0},
               note=agn._load_yesterday_note("2026-09-16")[0], note_reason="ok")
    assert con._state()["points"] == [], "the constrained book moved on agentic input"


def test_an_absent_agentic_feed_is_DORMANT_not_an_error(tmp_path):
    """Before the first note, the arm must say 'armed, waiting' — never fabricate
    a point, and never crash the pulse."""
    b = LlmShadowBook(root=str(tmp_path), path=AGENTIC_BOOK, notes_dir=AGENTIC_DIR)
    note, reason = b._load_yesterday_note("2026-09-16")
    assert note is None and "dormant" in (reason or "").lower()


def test_the_agentic_book_is_DURABLE_and_clock_covered():
    """The retired desk's one real virtue was durability; the replacement keeps it.
    Positions carry across sessions, so an ephemeral disk would drop live ones."""
    from paper_trader.cloud_state import DURABLE_PATHS
    from paper_trader.clock_census import EXEMPT
    assert AGENTIC_BOOK in DURABLE_PATHS
    import paper_trader.clock_census as cc
    src = __import__("inspect").getsource(cc)
    assert "llm_shadow_agentic_rolled" in src, "not covered by a clock"
    assert "data/state/analyst_desk_book.json" not in DURABLE_PATHS
    assert "data/state/analyst_desk_book.json" not in EXEMPT, (
        "the retired book should be OUT of the durable set entirely, not exempted "
        "into it — its S3 object is frozen as the historical record")


# --------------------------------------------------------------------------- #
# The EXECUTION lock. T-350f's lesson, applied to my own change: the two-arm
# loop lives inline in main()'s trend_sleeve branch, and NO existing driver test
# reaches that block — so without this, "both arms run" would be a claim about
# source text, which is the exact genre that let `sleeve_cap` through.
# --------------------------------------------------------------------------- #
import datetime as _dt
import shutil as _shutil
import types as _types

import pandas as _pd
import pytest as _pytest

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


def _drive_pulse(tmp_path):
    today = _dt.date(2026, 9, 16)
    now = _dt.datetime(2026, 9, 16, 9, 45, tzinfo=_dt.timezone.utc)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    _shutil.copy("config/substantially_identical.json",
                 tmp_path / "config/substantially_identical.json")
    (tmp_path / "config/llm_settings.json").write_text(json.dumps(
        {"llm": {"kill_switch": False, "trading_kill_switch": False,
                 "monthly_budget_usd": 30.0, "max_output_tokens": 1500}}))
    # BOTH arms get a note, so a run that books only one is visibly wrong
    _seed(tmp_path, AGENTIC_DIR, as_of="2026-09-15")
    _seed(tmp_path, "data/intel/analyst_notes", as_of="2026-09-15")

    # 400 bars: the {2,5,10}-month trend overlay fails CLOSED on short history
    # ([NN-FAIL-CLOSED] in sleeve_constructor), so a short fixture never reaches
    # the pulse. A gentle ramp rather than a flat line so the overlay has signal.
    idx = _pd.bdate_range(end=_pd.Timestamp(today) - _pd.Timedelta(days=1), periods=400)
    px = {"SPY": 600.0, "AGG": 98.0, "GLD": 420.0}
    series = {t: _pd.Series([v * (1 + 0.0004 * i) for i in range(len(idx))], index=idx)
              for t, v in px.items()}

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
              now=now, client=_C(), cloud=_Cloud(), root=str(tmp_path))


def test_the_pulse_RUNS_BOTH_ARMS_not_just_the_constrained_one(tmp_path, capsys):
    """THE REGRESSION. Before T-355 only the constrained arm was instantiated;
    the agentic arm's 29 notes were booked nowhere while a phantom desk burned
    36 sessions recording zeros."""
    _drive_pulse(tmp_path)
    out = capsys.readouterr().out
    assert "LLM-SHADOW[agentic]" in out, (
        "the agentic arm never ran — this is the defect, restated\n" + out[-2000:])
    assert "LLM-SHADOW " in out or "LLM-SHADOW n_days" in out, "constrained arm lost"


def test_the_retired_desk_no_longer_runs_in_the_pulse(tmp_path, capsys):
    """The phantom must be gone from the live path, not merely unreferenced."""
    _drive_pulse(tmp_path)
    out = capsys.readouterr().out
    assert "analyst_desk" not in out, "the retired desk is still being recorded"
    assert not (tmp_path / "data/state/analyst_desk_book.json").exists()
