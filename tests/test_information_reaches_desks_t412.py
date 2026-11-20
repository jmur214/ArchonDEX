# tests/test_information_reaches_desks_t412.py
"""T-412 (T-411 Phase 1): the information the daily run collects reaches the desks it built,
and every run proves it.

THE DEFECTS (docs/Audit/trade_desk_gap_analysis_t411_2026-11-20.md Parts 3 and 7; health
row "Information the system collects never reaches its decision paths", 2026-11-20):
  1. the eval harness and the intel pulse read data/macro_data/alt/ BEFORE the run's first
     alt-data pull, so in a fresh container they read an empty directory;
  2. nothing recorded, per run, whether a reader ran after its input arrived;
  3. the event desk's 8-K panel exists in no container (and, found here, the desk's loader
     read a call shape the ledger never writes, and its price fetch priced the wrong day);
  4. thesis falsifiers were never resolved — positions closed on deadlines only.

THE LOCKS drive the REAL daily main() twice on one tmp root (Thu 2026-09-17, Fri 09-18) the
way tests/test_daily_run_writes_under_its_root_2026_11_19.py does: fake broker, every socket
refused, S3 stubbed by a directory (the alt-data hoard is SEEDED there and arrives only via
pull_altdata), news_panel's credential loader stubbed, the SEC endpoints faked at the
archiver's and the body fetcher's transport, and a fake model that answers only the event
interpreter. Each lock was proven by reversion (2026-11-20; see the T-412 report).
"""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import shutil
import socket
import subprocess
import types
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

CHECKOUT = Path(__file__).resolve().parents[1]
DAY1, DAY2 = dt.date(2026, 9, 17), dt.date(2026, 9, 18)          # Thu, Fri
NOW = {DAY1: dt.datetime(2026, 9, 17, 13, 45, tzinfo=dt.timezone.utc),
       DAY2: dt.datetime(2026, 9, 18, 13, 45, tzinfo=dt.timezone.utc)}
NOTE_AS_OF = "2026-09-16"
KX_TICKER = "KXFED-26SEP-T4.00"
ACME_CIK, ACME_ACC = 1234, "0000001234-26-000777"
ACME_DOC = "acme-20260916.htm"
_LIVE_ENV = ("ANTHROPIC_API_KEY", "ALPACA_API_KEY", "ALPACA_SECRET_KEY", "PAPER_NOTIFY_WEBHOOK",
             "ARCHONDEX_PAPER_STATE_BUCKET", "ARCHONDEX_RESULTS_BUCKET", "AWS_PROFILE")


# --------------------------------------------------------------------------- #
# Hermetic stand-ins
# --------------------------------------------------------------------------- #
def _refuse(*_a: Any, **_k: Any) -> Any:
    raise OSError("network refused by the T-412 lock — a step tried to connect")


class _S3Dir:
    """CloudState stand-in. S3 is a DIRECTORY: pull_altdata copies the seeded hoard into the
    run's root and push_altdata copies it back, so alt-data exists in the run ONLY after the
    pull — the property the step-order lock is about."""

    def __init__(self, s3: Path, root: Path) -> None:
        self.s3, self.root = s3, root
        self.cfg = types.SimpleNamespace(enabled=False, s3_root="LOCAL", prefix="t412-lock")
        self.altdata_pulls = 0

    def pull(self) -> bool:
        return False

    def push(self) -> bool:
        return True

    def emit_metrics(self, **_kw: Any) -> None:
        return None

    def pull_readonly_from(self, *_a: Any, **_k: Any) -> dict:
        return {"ok": False, "rels": {}, "reason": "stub"}

    def pull_news_recent(self, *_a: Any, **_k: Any) -> int:
        return 0

    def pull_news_month(self, *_a: Any, **_k: Any) -> None:
        return None

    def push_news_month(self, *_a: Any, **_k: Any) -> bool:
        return True

    def pull_altdata(self, timeout_s: float | None = None) -> bool:
        self.altdata_pulls += 1
        src, dst = self.s3 / "altdata/data/macro_data/alt", self.root / "data/macro_data/alt"
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.glob("*"):
            shutil.copy2(f, dst / f.name)
        return True

    def push_altdata(self) -> bool:
        src, dst = self.root / "data/macro_data/alt", self.s3 / "altdata/data/macro_data/alt"
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.glob("*"):
            if f.is_file():
                shutil.copy2(f, dst / f.name)
        return True


def _client() -> Any:
    from paper_trader.paper_client import FakePaperClient
    idx = pd.bdate_range(end=pd.Timestamp(DAY2) - pd.Timedelta(days=1), periods=400)
    base = {"SPY": 600.0, "AGG": 98.0, "GLD": 420.0}

    class _C(FakePaperClient):
        def get_account(self) -> dict:
            return {"equity": 100_000.0, "cash": 100_000.0, "status": "ACTIVE"}

        def list_positions(self) -> list:
            return []

        def fetch_daily_closes(self, tickers, lookback_days=400) -> dict:
            # every symbol prices (ACME, QQQ included): an unpriceable symbol in these locks
            # would be a fault of the fake, not of the code under test
            return {t: pd.Series([base.get(t, 100.0) * (1 + 0.0004 * i) for i in range(len(idx))],
                                 index=idx) for t in tickers}

        def fetch_latest_prices(self, tickers) -> dict:
            return {t: base.get(t, 100.0) for t in tickers}

        def trading_days(self, start, end) -> set:
            return {DAY1, DAY2}

    return _C()


_FORM_IDX = (
    "Description:           Daily Index of EDGAR Dissemination Feed by Form Type\n"
    "Form Type   Company Name                         CIK         Date Filed  File Name\n"
    + "-" * 120 + "\n"
    f"4           SOMEONE JOHN                         5555        20260916    "
    f"edgar/data/5555/0000005555-26-000001.txt\n"
    f"8-K         ACME CORP                            {ACME_CIK}        20260916    "
    f"edgar/data/{ACME_CIK}/{ACME_ACC}.txt\n"
    f"8-K/A       ACME CORP                            {ACME_CIK}        20260916    "
    f"edgar/data/{ACME_CIK}/0000001234-26-000778.txt\n"
    "8-K         NOT TRACKED INC                      9999        20260916    "
    "edgar/data/9999/0000009999-26-000001.txt\n")


def _fake_sec_get(url: str, timeout: int = 90) -> bytes:
    """The archiver's transport, faked: SEC endpoints only — any other host is a defect."""
    assert "sec.gov" in url, f"the 8-K feed asked a non-SEC host: {url}"
    if url.endswith("/files/company_tickers.json"):
        return json.dumps({"0": {"cik_str": ACME_CIK, "ticker": "ACME", "title": "ACME CORP"},
                           "1": {"cik_str": 9999, "ticker": "NOPE", "title": "NOT TRACKED"}}
                          ).encode()
    if url.endswith("form.20260916.idx"):
        return _FORM_IDX.encode("latin-1")
    if url.endswith(f"CIK{ACME_CIK:010d}.json"):
        return json.dumps({"filings": {"recent": {
            "accessionNumber": [ACME_ACC, "0000001234-26-000778"],
            "filingDate": ["2026-09-16", "2026-09-16"],
            "acceptanceDateTime": ["2026-09-16T16:05:00.000Z", "2026-09-16T17:00:00.000Z"],
            "form": ["8-K", "8-K/A"], "items": ["2.02,9.01", "2.02"],
            "primaryDocument": [ACME_DOC, "acme-a.htm"]}}}).encode()
    raise OSError(f"not posted / not faked: {url}")


_BODY = ("ACME CORP reported third-quarter revenue of $1.2 billion, up 18% from a year "
         "earlier, and raised its full-year guidance above the consensus range.")


def _fake_body_get(url: str, *, json_: bool = False, session: Any = None):
    assert "sec.gov" in url, f"the body fetch asked a non-SEC host: {url}"
    if url.endswith(f"/{ACME_DOC}"):
        return f"<html><body><p>{_BODY}</p></body></html>"
    return None


_EVENT_JSON = json.dumps({
    "event_type": "earnings_result", "materiality": 0.8, "direction": "bullish",
    "rationale": "Synthetic: results and guidance above the company's prior range.",
    "predictions": [{"statement": "ACME outperforms SPY over 5 sessions", "probability": 0.6,
                     "horizon": "5 trading days",
                     "resolver": {"type": "relative_return", "symbol_a": "ACME",
                                  "symbol_b": "SPY", "op": "gt", "start_date": "2026-09-17",
                                  "end_date": "2026-09-30"}}],
    "suspected_prompt_injection": False})


def _fake_model(prompt_text: str, bundle_json: str, max_out: int) -> dict:
    """Answers ONLY the event interpreter; every other step gets an invalid reply and
    fails open, exactly as a broken model reply does in production."""
    text = _EVENT_JSON if "securities-event interpreter" in prompt_text else "not json"
    return {"text": text, "model_id_served": "fake-model",
            "usage": {"input_tokens": 10, "output_tokens": 10, "cost_usd": 0.0}}


_ALT_STUBBED = ("pull_gpr", "pull_epu", "snapshot_polymarket", "snapshot_kalshi",
                "snapshot_kxfed", "pull_fred_rate_path", "snapshot_cef", "pull_form4_index",
                "pull_usaspending")
_POS_STUBBED = ("pull_regsho_short_volume", "pull_sec_ftd", "pull_naaim", "pull_finra_margin",
                "pull_finra_short_interest")


def _one_article(client, universe, start, end, run_id, ingest_ts) -> pd.DataFrame:
    from intelligence import news_panel
    return pd.DataFrame([{
        "article_id": f"t412-{start}", "created_at": pd.Timestamp(start, tz="UTC") + pd.Timedelta(hours=14),
        "updated_at": pd.Timestamp(start, tz="UTC") + pd.Timedelta(hours=14), "symbols": ["SPY"],
        "headline": "t412 lock article", "summary": "", "content": "c", "source": "lock",
        "url": "", "author": "", "ingest_ts": ingest_ts, "ingest_run_id": run_id}],
        columns=news_panel.SCHEMA)


def _dotenv_names() -> tuple[str, ...]:
    p = CHECKOUT / ".env"
    if not p.exists():
        return ()
    from dotenv import dotenv_values
    return tuple(dotenv_values(p).keys())


def _hermetic(mp: pytest.MonkeyPatch) -> None:
    for name in (*_LIVE_ENV, *_dotenv_names()):
        mp.delenv(name, raising=False)
    mp.setattr(socket.socket, "connect", _refuse)
    mp.setattr(socket.socket, "connect_ex", _refuse)
    mp.setattr(socket, "create_connection", _refuse)
    mp.setattr(socket, "getaddrinfo", _refuse)
    from intelligence import news_panel
    mp.setattr(news_panel, "_creds", lambda: (_ for _ in ()).throw(
        AssertionError("the lock must never read credentials")))
    mp.setattr(news_panel, "_client", lambda: object())
    mp.setattr(news_panel, "_fetch_universe", _one_article)
    import scripts.archive_altdata_t136 as ad
    import scripts.archive_positioning_t136 as ap
    for name in _ALT_STUBBED:
        mp.setattr(ad, name, lambda *_a, **_k: "stubbed (no network in this lock)")
    for name in _POS_STUBBED:
        mp.setattr(ap, name, lambda *_a, **_k: "stubbed (no network in this lock)")
    mp.setattr(ad, "_get", _fake_sec_get)
    mp.setattr(ad, "EDGAR_8K_RATE_SLEEP_S", 0.0)
    import intelligence.event_call.eightk_body as eb
    mp.setattr(eb, "_get", _fake_body_get)
    import paper_trader.intel_pulse as ip
    mp.setattr(ip, "_model_call_or_none", lambda tier, settings: _fake_model)
    mp.setattr(ip, "_scan_model_call_or_none", lambda settings: None)
    import intelligence.analyst.anthropic_adapter as aa

    def _no_agentic(*_a: Any, **_k: Any):
        def _raise(*_a2: Any, **_k2: Any):
            raise RuntimeError("no agentic model in this lock")
        return _raise
    mp.setattr(aa, "make_agentic_call", _no_agentic)


# --------------------------------------------------------------------------- #
# Seeds
# --------------------------------------------------------------------------- #
def _seed_s3_altdata(s3: Path) -> None:
    alt = s3 / "altdata/data/macro_data/alt"
    alt.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"snap_date": d, "series": "KXFED", "event_ticker": "KXFED-26SEP",
                   "ticker": KX_TICKER, "floor_strike": 4.0, "strike_type": "greater",
                   "yes_bid": 0.60, "yes_ask": 0.64, "last_price": 0.62,
                   "expiration_time": "2026-09-16T18:00:00Z"}
                  for d in ("2026-09-15", "2026-09-16")]
                 ).to_parquet(alt / "kalshi_kxfed_snapshots.parquet", index=False)
    days = pd.date_range("2026-08-01", "2026-09-17", freq="D")
    pd.DataFrame({"series": "DFEDTARU", "observation_date": days.strftime("%Y-%m-%d"),
                  "value": [4.50 if d < pd.Timestamp("2026-09-10") else 4.25 for d in days]}
                 ).to_parquet(alt / "fred_rate_path.parquet", index=False)


def _falsifier_resolver(direction: str) -> dict:
    return {"type": "price_above", "symbol": "SPY", "level": 1.0, "direction": direction,
            "by_date": "2026-09-15", "mode": "terminal"}


def _open_pos(tid: str, leg: str, falsifiers: list) -> dict:
    return {"thesis_id": tid, "theme_class": "other", "conviction": 0.7,
            "weights": {leg: 0.2}, "sizing_scale": 0.2, "binding_cap": "per_name",
            "unconstrained_scale": 0.42, "downsized": True,
            "entry_px": {leg: 100.0}, "twin_entry_px": 600.0, "filed_date": "2026-09-01",
            "entry_date": "2026-09-02", "days_pending": 0, "horizon_days": 180, "held": 10,
            "thesis": {"thesis_id": tid, "falsifiers": falsifiers}}


def _seed_root(root: Path) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy(CHECKOUT / "config/substantially_identical.json",
                root / "config/substantially_identical.json")
    (root / "config/llm_settings.json").write_text(json.dumps(
        {"llm": {"kill_switch": False, "trading_kill_switch": False,
                 "monthly_budget_usd": 30.0, "max_output_tokens": 1500}}))
    # the tracked universe (the image bakes the real one)
    (root / "data/universe").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"ticker": ["ACME"], "start": [pd.Timestamp("2000-01-03")],
                  "end": [pd.NaT]}).to_parquet(root / "data/universe/sp500_membership_pit.parquet")
    # one constrained note with three expired predictions: two settle on the ALT-DATA, one
    # on a symbol OUTSIDE the sleeve's three (only a live fetch can price it)
    from paper_trader.artifact_paths import ANALYST_NOTE
    note = ANALYST_NOTE.path_for(root, NOTE_AS_OF)
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(json.dumps({"as_of": NOTE_AS_OF, "market_assessment": "t412 lock",
                                "predictions": [
        {"statement": "the KXFED 4.00 strike settles yes", "probability": 0.7,
         "resolver": {"type": "event_occurs", "source": "kalshi_settlement",
                      "event_id": KX_TICKER, "predicate": {"settles": "yes"},
                      "by_date": NOTE_AS_OF}},
        {"statement": "the Sept FOMC cuts", "probability": 0.6,
         "resolver": {"type": "event_occurs", "source": "fomc_calendar",
                      "event_id": "2026-09-09", "predicate": {"action": "cut"},
                      "by_date": NOTE_AS_OF}},
        {"statement": "QQQ above 1 on the expiry", "probability": 0.9,
         "resolver": {"type": "price_above", "symbol": "QQQ", "level": 1.0,
                      "direction": "above", "by_date": NOTE_AS_OF, "mode": "terminal"}}]}))
    # the machine thesis book with four open baskets, one per falsifier outcome
    st = {"_schema": "thesis_book/v1", "desk": "thesis_machine", "origin": "machine",
          "open": [
              _open_pos("th-kill", "SPY", [{"kind": "resolver", "check_by": "2026-12-31",
                                            "statement": "synthetic kill: SPY above 1",
                                            "resolver": _falsifier_resolver("above")}]),
              _open_pos("th-pass", "AGG", [{"kind": "resolver", "check_by": "2026-09-16",
                                            "statement": "synthetic: SPY below 1",
                                            "resolver": _falsifier_resolver("below")}]),
              _open_pos("th-qual", "QQQ", [{"kind": "qualitative", "check_by": "2026-12-31",
                                            "statement": "the theme stops trending"}]),
              _open_pos("th-event", "GLD", [{"kind": "resolver", "check_by": "2026-12-31",
                                             "statement": "an unknown market settles yes",
                                             "resolver": {"type": "event_occurs",
                                                          "source": "kalshi_settlement",
                                                          "event_id": "KXFED-NOT-ON-DISK",
                                                          "predicate": {"settles": "yes"},
                                                          "by_date": "2026-09-10"}}])],
          "closed": [], "days": [], "pending": []}
    (root / "data/state").mkdir(parents=True, exist_ok=True)
    (root / "data/state/thesis_book_machine.json").write_text(json.dumps(st))
    (root / "data/intel/thesis_calls.jsonl").write_text("".join(
        json.dumps({"thesis_id": p["thesis_id"], "origin": "machine", "as_of": "2026-09-01"})
        + "\n" for p in st["open"]))


def _drive(day: dt.date, root: Path, cloud: _S3Dir) -> dict:
    import scripts.run_paper_cloud_day as drv
    out = io.StringIO()
    with pytest.MonkeyPatch.context() as mp:
        _hermetic(mp)
        mp.setattr(drv, "now_et", lambda: NOW[day])
        with contextlib.redirect_stdout(out):
            rc = drv.main(["--allocator", "mean_variance", "--strategy", "trend_sleeve",
                           "--sleeve-notional-cap", "10000", "--dry-run"],
                          now=NOW[day], client=_client(), cloud=cloud, root=str(root))
    hb = json.loads((root / "data/state/paper_heartbeat.json").read_text())
    return {"rc": rc, "out": out.getvalue(), "hb": hb}


@pytest.fixture(scope="module")
def drives(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Two real main() runs on ONE root (seconds each); every test below reads the record."""
    base = tmp_path_factory.mktemp("t412")
    root, s3 = base / "root", base / "s3"
    root.mkdir()
    _seed_s3_altdata(s3)
    _seed_root(root)
    cloud = _S3Dir(s3, root)
    d1 = _drive(DAY1, root, cloud)
    d1["thesis"] = json.loads((root / "data/state/thesis_book_machine.json").read_text())
    d2 = _drive(DAY2, root, cloud)
    return {"root": root, "s3": s3, "d1": d1, "d2": d2, "altdata_pulls": cloud.altdata_pulls}


def _reg(d: dict) -> dict:
    return d["hb"]["source_register"]


def _day1_rows(drives: dict) -> list[dict]:
    return [r for r in map(json.loads, (drives["root"] / "data/intel/analyst_predictions.jsonl")
                           .read_text().splitlines()) if r.get("resolved_at") == str(DAY1)]


# --------------------------------------------------------------------------- #
# 1. STEP ORDER — the eval sees the alt-data the run pulled
# --------------------------------------------------------------------------- #
def test_the_eval_resolves_the_records_that_settle_on_the_pulled_altdata(drives):
    """THE REGRESSION. Before T-412 the alt-data arrived in step 7, after the eval: both
    event_occurs predictions logged source_absent_or_unsettled and n_resolvable stayed 0
    for them (the cloud's 0-of-59 shape)."""
    # DAY1's rows only: the two drives share one root (a cloud container does not), so a
    # DAY2 retry would resolve against alt-data step 7 left behind and mask the defect.
    log = {r["prediction_id"]: r for r in _day1_rows(drives)}
    pid = f"analyst_constrained:{NOTE_AS_OF}"
    assert log[f"{pid}#0"]["resolvable"] and log[f"{pid}#0"]["outcome"] == 1, log[f"{pid}#0"]
    assert log[f"{pid}#1"]["resolvable"] and log[f"{pid}#1"]["outcome"] == 1, log[f"{pid}#1"]
    # the market-implied baseline is read from the same pulled snapshot (PIT, note date)
    assert log[f"{pid}#0"]["baseline_implied"] == pytest.approx(0.62)
    assert "today: 3/3 due resolved" in drives["d1"]["out"], drives["d1"]["out"][-3000:]


def test_a_prediction_outside_the_sleeve_resolves_on_a_live_fetch(drives):
    """The cloud's reason code was source_absent_or_stale — the PRICE resolvers' — and the
    harness's only fallback for a non-sleeve symbol is a CSV the image does not carry."""
    rec = next(r for r in _day1_rows(drives) if r["resolver"].get("symbol") == "QQQ")
    assert rec["resolvable"] and rec["outcome"] == 1, rec


def test_the_altdata_is_pulled_once_per_run_and_the_archive_reuses_it(drives):
    assert drives["altdata_pulls"] == 2, "one pull per run (two runs), not one per reader"
    assert "ALTDATA-PULL pulled=True" in drives["d1"]["out"]


# --------------------------------------------------------------------------- #
# 2. THE SOURCE REGISTER
# --------------------------------------------------------------------------- #
def test_the_register_marks_a_present_source_fresh_at_its_reader(drives):
    reg = _reg(drives["d1"])
    kx = reg["sources"]["kxfed_snapshots"]
    assert kx["reads"]["eval_harness"]["verdict"] == "fresh", kx
    assert kx["reads"]["eval_harness"]["at_read"]["newest"] == "2026-09-16"
    assert kx["arrives_by"]["altdata_pull"]["ok"] is True
    assert reg["readers"]["eval_harness"]["ran"] is True


def test_the_register_flags_an_absent_source_as_degraded(drives):
    reg = _reg(drives["d1"])
    ag = reg["sources"]["analyst_notes_agentic"]["reads"]["eval_harness"]
    assert ag["verdict"] == "absent", ag
    assert reg["degraded"] is True
    assert any(p.startswith("analyst_notes_agentic -> eval_harness: absent")
               for p in reg["problems"]), reg["problems"]


def test_a_ledger_its_own_run_writes_later_is_absent_not_read_before_arrival(drives):
    """DAY1: the desk read the event ledger before the interpreter (later, same run, by
    design: signal t, fill t+1) created it. The desk had nothing — ABSENT, degraded — but
    "read before arrival" would wrongly tell the reader to move a sync."""
    ev = _reg(drives["d1"])["sources"]["event_calls"]
    assert ev["reads"]["event_desk"]["verdict"] == "absent", ev
    assert ev["at_tail"]["present"] is True and ev["same_run_writer"] == "intel_pulse"


def test_the_register_lists_a_retired_source_without_flagging_it(drives):
    reg = _reg(drives["d1"])
    ss = reg["sources"]["special_situations"]
    assert ss["reads"]["intel_pulse"]["verdict"] == "retired" and ss["retired"]
    assert not any(p.startswith("special_situations") for p in reg["problems"])


def test_the_register_never_touches_the_trading_verdict(drives):
    """A degraded register is its own channel: last_run stays whatever reconcile said."""
    d = drives["d1"]
    assert _reg(d)["degraded"] is True
    assert "information-path problem" not in str(d["hb"]["last_run"].get("reason"))
    assert "12. SOURCES" in d["out"]


# --------------------------------------------------------------------------- #
# 3. THE EVENT DESK'S FEED — fetched, interpreted, booked
# --------------------------------------------------------------------------- #
def test_the_8k_feed_lands_under_the_root_and_is_pushed_with_the_hoard(drives):
    root, s3 = drives["root"], drives["s3"]
    panel = pd.read_parquet(root / "data/macro_data/alt/edgar_8k_items.parquet")
    assert list(panel["accession"]) == [ACME_ACC]          # 8-K/A and untracked CIK excluded
    row = panel.iloc[0]
    assert (row["ticker"], row["items"], row["primary_document"]) == ("ACME", "2.02,9.01", ACME_DOC)
    assert (s3 / "altdata/data/macro_data/alt/edgar_8k_items.parquet").exists()
    receipt = json.loads((root / "data/macro_data/alt/edgar_8k_fetch_receipt.json").read_text())
    assert receipt["ok"] and receipt["index_ok"] == ["2026-09-16"]
    reg = _reg(drives["d1"])
    assert reg["sources"]["edgar_8k_items"]["reads"]["intel_pulse"]["verdict"] == "fresh"
    assert reg["sources"]["edgar_8k_items"]["arrives_by"]["edgar_8k_fetch"]["ok"] is True


def test_the_interpreter_files_a_call_from_the_seeded_filing(drives):
    led = [json.loads(ln) for ln in
           (drives["root"] / "data/intel/event_calls.jsonl").read_text().splitlines() if ln]
    assert [r["event_call"]["document_ref"] for r in led] == [f"{ACME_ACC}#2.02"], led
    assert led[0]["note_date"] == str(DAY1) and led[0]["event_call"]["symbol"] == "ACME"
    assert "EVENT-FEED status=ok" in drives["d1"]["out"], drives["d1"]["out"][-3000:]


def test_the_event_desk_opens_its_first_position_the_next_session(drives):
    """Signal t (DAY1's call), fill t+1 (DAY2's run). Before T-412 two more links were dead
    behind the missing feed: the desk's loader matched a flat call shape the ledger never
    writes, and the driver priced today's calls instead of the prior session's."""
    book = json.loads((drives["root"] / "data/state/event_shadow_book.json").read_text())
    opened = [p for p in book["open"] if p["symbol"] == "ACME"]
    assert opened, book["days"][-1]
    assert opened[0]["entry_date"] == str(DAY2) and opened[0]["as_of"] == str(DAY1)
    assert opened[0]["direction"] == "bullish" and opened[0]["horizon_days"] == 5
    reg2 = _reg(drives["d2"])
    assert reg2["sources"]["event_calls"]["reads"]["event_desk"]["verdict"] == "fresh"


# --------------------------------------------------------------------------- #
# 4. THESIS FALSIFIERS — resolved from the run's own data
# --------------------------------------------------------------------------- #
def test_a_resolver_falsifier_that_resolves_true_closes_its_thesis(drives):
    st = drives["d1"]["thesis"]
    closed = {c["thesis_id"]: c for c in st["closed"]}
    assert "th-kill" in closed, st["days"][-1]
    assert closed["th-kill"]["killed_by_falsifier"] is True
    assert closed["th-kill"]["exit_reason"].startswith("falsifier resolved TRUE")


def test_a_falsifier_checked_and_passed_no_longer_dies_on_its_deadline(drives):
    """th-pass's check_by (09-16) is past; before T-412 that alone closed it fail-closed.
    Its resolver came back FALSE, so it was checked and passed — it stays open."""
    st = drives["d1"]["thesis"]
    assert "th-pass" in {p["thesis_id"] for p in st["open"]}
    day = st["days"][-1]["falsifiers"]
    assert day["th-pass"][0]["status"] == "not_fired"


def test_an_undecidable_falsifier_is_reported_unresolvable_never_not_fired(drives):
    day = drives["d1"]["thesis"]["days"][-1]["falsifiers"]
    assert day["th-qual"][0]["status"] == "unresolvable"
    assert "qualitative" in day["th-qual"][0]["detail"]
    assert day["th-event"][0]["status"] == "unresolvable"
    assert "source_absent_or_unsettled" in day["th-event"][0]["detail"]
    assert "THESIS-FALSIFIERS[thesis_machine]" in drives["d1"]["out"]


# --------------------------------------------------------------------------- #
# Units behind the locks
# --------------------------------------------------------------------------- #
def test_the_form_index_parse_keeps_only_8k_and_reads_the_accession():
    import scripts.archive_altdata_t136 as ad
    df = ad._parse_form_index_8k(_FORM_IDX)
    assert list(df["accession"]) == [ACME_ACC, "0000009999-26-000001"]
    assert list(df["cik"]) == [ACME_CIK, 9999] and set(df["index_date"]) == {"2026-09-16"}
    assert df.iloc[0]["company"] == "ACME CORP"


def test_the_8k_pull_asks_sec_only_dedups_and_states_every_outcome(tmp_path, monkeypatch):
    import scripts.archive_altdata_t136 as ad
    from paper_trader.altdata_archive import _out_dir_under_root
    asked: list[str] = []

    def _rec(url: str, timeout: int = 90) -> bytes:
        asked.append(url)
        return _fake_sec_get(url, timeout)
    monkeypatch.setattr(ad, "_get", _rec)
    monkeypatch.setattr(ad, "EDGAR_8K_RATE_SLEEP_S", 0.0)
    with _out_dir_under_root(ad, tmp_path):
        first = ad.pull_8k_items(["ACME"], as_of="2026-09-17", days_back=2)
        n_sub = sum("/submissions/" in u for u in asked)
        second = ad.pull_8k_items(["ACME"], as_of="2026-09-17", days_back=2)
        none = ad.pull_8k_items([], as_of="2026-09-17")
        dead = ad.pull_8k_items(["ACME"], as_of="2026-09-25", days_back=2)  # no index faked
    assert first.startswith("edgar_8k: +1 new"), first
    assert second.startswith("edgar_8k: +0 new"), second
    assert sum("/submissions/" in u for u in asked) == n_sub == 1   # never re-asked
    assert none.startswith("edgar_8k: FAILED (empty universe") and "FAILED" in dead
    assert all(ad._is_sec_host(u) for u in asked), asked
    assert len(pd.read_parquet(tmp_path / ad.EDGAR_8K_PANEL)) == 1


def test_the_8k_pull_truncates_at_its_request_budget_and_says_so(tmp_path, monkeypatch):
    import scripts.archive_altdata_t136 as ad
    from paper_trader.altdata_archive import _out_dir_under_root
    monkeypatch.setattr(ad, "_get", _fake_sec_get)
    monkeypatch.setattr(ad, "EDGAR_8K_RATE_SLEEP_S", 0.0)
    monkeypatch.setattr(ad, "_edgar_cik_map", lambda uni, today: {ACME_CIK: "ACME", 9999: "NOPE"})
    with _out_dir_under_root(ad, tmp_path):
        line = ad.pull_8k_items(["ACME", "NOPE"], as_of="2026-09-17", days_back=2,
                                max_submissions=1)
    assert "TRUNCATED" in line, line
    assert json.loads((tmp_path / ad.EDGAR_8K_RECEIPT).read_text())["truncated"] is True


def test_a_missing_or_stale_8k_panel_is_degraded_never_a_quiet_day(tmp_path):
    from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig
    from intelligence.event_call.run_forward import pulse_step, run_forward
    kw = dict(governor=CostGovernor(GovernorConfig(), str(tmp_path / "spend.jsonl")),
              prompt_path=str(CHECKOUT / "config/prompts/event_interpreter/v1.txt"),
              model_id_requested="m", prompt_version="event_interpreter/v1",
              projected_cost_usd=0.01, raw_dir=str(tmp_path / "raw"),
              ledger_path=tmp_path / "l.jsonl", today=DAY1)
    absent = run_forward(str(DAY1), model_call=_fake_model,
                         panel_path=tmp_path / "missing.parquet", **kw)
    assert absent.degraded and absent.reason.startswith("8k_panel_absent"), absent
    stale_p = tmp_path / "stale.parquet"
    pd.DataFrame({"filing_date": ["2026-08-01"], "ticker": ["ACME"], "accession": ["a"],
                  "items": ["2.02"], "cik": [1]}).to_parquet(stale_p)
    stale = run_forward(str(DAY1), model_call=_fake_model, panel_path=stale_p, **kw)
    assert stale.degraded and stale.reason.startswith("8k_panel_stale"), stale
    no_model = pulse_step(str(DAY1), model_call=None, panel_path=tmp_path / "missing.parquet",
                          **{k: v for k, v in kw.items() if k != "today"})
    assert no_model["feed"]["ok"] is False and "absent" in no_model["feed"]["reason"]


def test_the_forward_window_finds_yesterdays_filing_and_the_body_is_fetched_once(tmp_path):
    from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig
    from intelligence.event_call.run_forward import run_forward
    p = tmp_path / "panel.parquet"
    pd.DataFrame({"ticker": ["ACME"], "cik": [ACME_CIK], "accession": [ACME_ACC],
                  "filing_date": ["2026-09-16"], "acceptance_dt": [""],
                  "items": ["2.02,7.01,9.01"], "primary_document": [ACME_DOC]}).to_parquet(p)
    fetched: list[tuple] = []

    def _body(cik, acc, **k):
        fetched.append((cik, acc, k.get("primary_document")))
        return _BODY
    r = run_forward(str(DAY1), model_call=_fake_model,
                    governor=CostGovernor(GovernorConfig(), str(tmp_path / "spend.jsonl")),
                    prompt_path=str(CHECKOUT / "config/prompts/event_interpreter/v1.txt"),
                    model_id_requested="m", prompt_version="event_interpreter/v1",
                    projected_cost_usd=0.01, raw_dir=str(tmp_path / "raw"),
                    ledger_path=tmp_path / "l.jsonl", today=DAY1, panel_path=p,
                    body_fetch=_body)
    assert r.n_documents == 2 and r.n_ok == 2, r           # 2.02 + 7.01; 9.01 excluded
    assert fetched == [(ACME_CIK, ACME_ACC, ACME_DOC)]      # one body per accession


def test_the_run_budget_defers_documents_without_marking_them_seen(tmp_path):
    from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig
    from intelligence.event_call.run_forward import run_forward
    p = tmp_path / "panel.parquet"
    pd.DataFrame({"ticker": ["ACME"], "cik": [ACME_CIK], "accession": [ACME_ACC],
                  "filing_date": ["2026-09-16"], "items": ["2.02,7.01"],
                  "primary_document": [ACME_DOC]}).to_parquet(p)
    r = run_forward(str(DAY1), model_call=_fake_model,
                    governor=CostGovernor(GovernorConfig(), str(tmp_path / "spend.jsonl")),
                    prompt_path=str(CHECKOUT / "config/prompts/event_interpreter/v1.txt"),
                    model_id_requested="m", prompt_version="event_interpreter/v1",
                    projected_cost_usd=0.01, raw_dir=str(tmp_path / "raw"),
                    ledger_path=tmp_path / "l.jsonl", today=DAY1, panel_path=p,
                    body_fetch=lambda *a, **k: _BODY, max_documents=1)
    assert (r.n_called, r.n_deferred, r.n_ok) == (1, 1, 1), r


def test_the_event_desk_reads_the_ledger_shape_the_service_writes(tmp_path):
    from paper_trader.event_shadow_book import EventShadowBook
    led = tmp_path / "data/intel/event_calls.jsonl"
    led.parent.mkdir(parents=True)
    led.write_text(json.dumps({"note_id": "eventcall:x#2.02", "note_date": "2026-09-17",
                               "predictions": [{"horizon": "5 trading days", "resolver": {}}],
                               "event_call": {"symbol": "ACME", "direction": "bearish",
                                              "materiality": 0.9,
                                              "event_type": "guidance_change"}}) + "\n")
    b = EventShadowBook(root=str(tmp_path))
    calls, why = b._load_calls("2026-09-17")
    assert why == "ok" and calls[0]["symbol"] == "ACME" and calls[0]["as_of"] == "2026-09-17"
    assert "ACME" in b.pending_symbols("2026-09-18")         # the PRIOR session's call is priced


def test_resolve_falsifier_statuses():
    from intelligence.analyst import eval_harness as eh
    idx = pd.bdate_range("2026-08-03", "2026-09-17")
    up = pd.Series(range(100, 100 + len(idx)), index=idx, dtype=float)
    pf = {"SPY": up}.get
    touch = {"kind": "resolver", "resolver": {"type": "price_above", "symbol": "SPY",
                                              "level": 110.0, "direction": "above",
                                              "by_date": "2026-12-31", "mode": "touch"}}
    terminal = {"kind": "resolver", "resolver": {**touch["resolver"], "mode": "terminal"}}
    gone = {"kind": "resolver", "resolver": {**terminal["resolver"], "symbol": "ZZZZ",
                                             "by_date": "2026-09-10"}}
    assert eh.resolve_falsifier(touch, "2026-08-03", "2026-09-17", price_fn=pf)[0] == "fired"
    assert eh.resolve_falsifier(terminal, "2026-08-03", "2026-09-17", price_fn=pf)[0] == "pending"
    st, why = eh.resolve_falsifier(gone, "2026-08-03", "2026-09-17", price_fn=pf)
    assert st == "unresolvable" and "source_absent_or_stale" in why
    assert eh.resolve_falsifier({"kind": "qualitative"}, "2026-08-03", "2026-09-17")[0] \
        == "unresolvable"


def test_a_book_recorded_without_a_resolution_pass_says_not_checked(tmp_path):
    from paper_trader.thesis_book import ThesisBook
    p = tmp_path / "data/state/thesis_book_machine.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"_schema": "thesis_book/v1", "open": [
        _open_pos("th-q", "SPY", [{"kind": "qualitative", "check_by": "2026-12-31",
                                   "statement": "s"}])], "closed": [], "days": [],
        "pending": []}))
    b = ThesisBook(root=str(tmp_path))
    s = b.record("2026-09-17", closes={"SPY": 600.0})
    assert b._state()["days"][-1]["falsifiers"]["th-q"][0]["status"] == "not_checked"
    assert s["falsifier_status_counts"] == {"not_checked": 1}


def test_the_altdata_sync_pulls_once_and_replays_a_failure():
    import scripts.run_paper_cloud_day as drv

    class _C:
        n = 0

        def pull_altdata(self) -> bool:          # a stand-in without the timeout keyword
            _C.n += 1
            return True
    s = drv._AltdataSync(_C())
    assert s.ensure(timeout_s=5) is True and s.ensure() is True and _C.n == 1

    class _Boom:
        def pull_altdata(self, timeout_s=None):
            raise RuntimeError("s3 down")
    b = drv._AltdataSync(_Boom())
    for _ in range(2):                             # step 7 still sees the failure
        with pytest.raises(RuntimeError):
            b.ensure()


def test_a_stalled_aws_call_is_bounded(monkeypatch):
    from paper_trader.cloud_state import CloudState, CloudStateConfig

    def _hang(*a: Any, **k: Any):
        raise subprocess.TimeoutExpired(cmd="aws", timeout=k.get("timeout"))
    monkeypatch.setattr(subprocess, "run", _hang)
    r = CloudState(CloudStateConfig(bucket="b"))._aws("s3", "sync", "x", "y", timeout_s=1)
    assert r.returncode == 124 and "timeout" in r.stderr


def test_the_register_names_a_read_before_arrival(tmp_path):
    from paper_trader import source_register as sr
    reg = sr.SourceRegister(tmp_path, sr.ACCOUNT_1, "2026-09-17")
    reg.read(sr.EVAL_HARNESS)                            # nothing on disk yet
    alt = tmp_path / "data/macro_data/alt"
    alt.mkdir(parents=True)
    pd.DataFrame({"snap_date": ["2026-09-16"], "ticker": ["X"]}).to_parquet(
        alt / "kalshi_kxfed_snapshots.parquet")
    reg.arrived(sr.ALTDATA_PULL, ok=True)
    blk = reg.block()
    assert blk["sources"]["kxfed_snapshots"]["reads"]["eval_harness"]["verdict"] \
        == sr.READ_BEFORE_ARRIVAL
    assert blk["readers"]["intel_pulse"]["ran"] is False
    assert any("intel_pulse: not_run" in p for p in blk["problems"])


def test_every_declared_source_has_a_reader_and_budgets_match_the_feed_gate():
    from paper_trader import source_register as sr
    from paper_trader.altdata_archive import _FEED_HEALTH
    gate = {rel: budget for _n, rel, _c, budget, _f, _e in _FEED_HEALTH}
    for s in sr.SOURCES:
        assert s.readers, f"{s.id} declares no reader"
        if s.rel in gate and not s.retired:
            assert s.max_age_days == gate[s.rel], (s.id, s.max_age_days, gate[s.rel])


def test_every_reader_reads_where_its_writer_writes_and_the_sync_moves_it():
    """One spelling per file: the 8-K panel's writer (the archiver's OUT_DIR), its reader
    (eightk_feed via the pulse), the register, the feed gate and the S3 sync all name the
    same path — the T-348 'reader encodes the writer's naming independently' class."""
    import intelligence.analyst.eval_harness as eh
    import scripts.archive_altdata_t136 as ad
    from intelligence.event_call.eightk_feed import FORWARD_PANEL_REL
    from paper_trader import altdata_archive as aa
    from paper_trader import source_register as sr
    from paper_trader.cloud_state import ALTDATA_DIRS
    rel = {s.id: s.rel for s in sr.SOURCES}
    assert FORWARD_PANEL_REL == aa.EDGAR_8K_PANEL_REL == f"{aa.ALT_REL}/{ad.EDGAR_8K_PANEL}" \
        == rel["edgar_8k_items"]
    assert CHECKOUT / FORWARD_PANEL_REL == ad.OUT_DIR / ad.EDGAR_8K_PANEL
    assert any(FORWARD_PANEL_REL.startswith(d + "/") for d in ALTDATA_DIRS)
    assert rel["kxfed_snapshots"] == str(eh.ALT_REL / eh.KALSHI_SNAP_NAME)
    assert rel["fred_rate_path"] == str(eh.ALT_REL / eh.FRED_PATH_NAME)
    gate = {r for _n, r, *_rest in aa._FEED_HEALTH}
    assert {rel["kxfed_snapshots"], rel["fred_rate_path"], rel["edgar_8k_items"]} <= gate
