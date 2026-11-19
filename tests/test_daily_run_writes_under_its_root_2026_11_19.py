# tests/test_daily_run_writes_under_its_root_2026_11_19.py
"""The daily paper run writes ONLY under the state root it is given — never into the checkout.

THE DEFECT (docs/State/health_check.md, MEDIUM, director 2026-11-17). The eval harness
(`SUMMARY = ROOT / "data" / ...`) and the performance digest (`DIGEST = ROOT / "docs" / ...`
plus its `docs/Measurements/` archive copy) resolved their output from the MODULE's own
location and ignored the root `run_paper_cloud_day.main(root=...)` was given. On
2026-11-17 a reviewer's simulation, run in a worktree whose `data/` was a symlink to the
main repo's, replaced the MAIN tree's `data/intel/analyst_eval_summary.json` with an empty
summary and failed the director's merge gate. The search for the same shape on the daily
path found two more writers: the news panel's month partition (`news_panel.PANEL_DIR`,
written on EVERY account's run) and the two alt-data archivers (`OUT_DIR`), plus the event
ledger the intel pulse appends to when a model key is present. In the cloud container the
root IS the checkout (`/app`), so the paths coincided and the fleet was unaffected.

THE LOCK drives the REAL daily `main()` through the account-1 branch (the only one that
reaches the eval harness and the digest) on a FRIDAY (the digest's day), with the broker
faked, S3 disabled, every socket refused, and steps 7 (alt-data) and 8 (news) allowed to
RUN rather than raising out at a missing cloud method the way older driver tests skip
them. One alt-data archiver function per module runs for real over a faked transport, so
the real write helpers resolve the redirected `OUT_DIR`. It then asserts that nothing in
the checkout was created, modified or removed, and that every writer's file landed under
the tmp root. Reversion-proven (2026-11-19): restoring any one writer's old path fails
the checkout assertion, naming the file.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import os
import shutil
import socket
import types
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import pytest

CHECKOUT = Path(__file__).resolve().parents[1]
TODAY = dt.date(2026, 9, 18)                       # a Friday — the digest fires only then
NOW = dt.datetime(2026, 9, 18, 13, 45, tzinfo=dt.timezone.utc)
NOTE_AS_OF = "2026-09-11"
PRED_EXPIRY = "2026-09-16"                         # expired by TODAY -> the harness resolves it

# Never walked: caches, and top-level dot-dirs (.git; .claude holds other agents' worktrees).
_SKIP_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})
# Every variable that could point a step at a real service or a real key.
_LIVE_ENV = ("ANTHROPIC_API_KEY", "ALPACA_API_KEY", "ALPACA_SECRET_KEY", "PAPER_NOTIFY_WEBHOOK",
             "ARCHONDEX_PAPER_STATE_BUCKET", "ARCHONDEX_RESULTS_BUCKET", "AWS_PROFILE")

Sig = Optional[tuple[int, int, int]]


# --------------------------------------------------------------------------- #
# The checkout listing
# --------------------------------------------------------------------------- #
def _checkout_listing() -> dict[str, Sig]:
    """Every path in the checkout: files -> (size, mtime_ns, ctime_ns), dirs -> None.

    Follows symlinks — a write THROUGH a worktree's data/ link into the main repo is the
    exact 2026-11-17 shape; a realpath set stops cycles. ctime is in the signature because
    the kernel sets it on every change and user code cannot set it back."""
    out: dict[str, Sig] = {}
    seen_real: set[str] = set()
    for dp, dns, fns in os.walk(CHECKOUT, followlinks=True):
        real = os.path.realpath(dp)
        if real in seen_real:
            dns[:] = []
            continue
        seen_real.add(real)
        rel_dp = os.path.relpath(dp, CHECKOUT)
        top = rel_dp == "."
        dns[:] = [d for d in dns
                  if d not in _SKIP_DIR_NAMES and not (top and d.startswith("."))]
        if not top:
            out[rel_dp + "/"] = None
        for f in fns:
            p = os.path.join(dp, f)
            try:
                st = os.stat(p)
                out[os.path.relpath(p, CHECKOUT)] = (st.st_size, st.st_mtime_ns, st.st_ctime_ns)
            except OSError:
                out[os.path.relpath(p, CHECKOUT)] = (-1, -1, -1)   # a dangling symlink
    return out


def _diff(before: dict[str, Sig], after: dict[str, Sig]) -> dict[str, list[str]]:
    return {"created": sorted(set(after) - set(before)),
            "removed": sorted(set(before) - set(after)),
            "modified": sorted(p for p in set(before) & set(after)
                               if before[p] is not None and before[p] != after[p])}


# --------------------------------------------------------------------------- #
# Hermetic stand-ins
# --------------------------------------------------------------------------- #
def _refuse(*_a: Any, **_k: Any) -> Any:
    raise OSError("network refused by the daily-run root lock — a step tried to connect")


class _Cloud:
    """CloudState stand-in: S3 disabled, and every sync main() calls answers without
    touching anything, so the alt-data (7) and news (8) steps RUN to their writers."""

    def __init__(self) -> None:
        self.cfg = types.SimpleNamespace(enabled=False, s3_root="LOCAL", prefix="root-lock")

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

    def pull_altdata(self) -> None:
        return None

    def push_altdata(self) -> bool:
        return True


def _client() -> Any:
    from paper_trader.paper_client import FakePaperClient
    idx = pd.bdate_range(end=pd.Timestamp(TODAY) - pd.Timedelta(days=1), periods=400)
    base = {"SPY": 600.0, "AGG": 98.0, "GLD": 420.0}
    series = {t: pd.Series([v * (1 + 0.0004 * i) for i in range(len(idx))], index=idx)
              for t, v in base.items()}

    class _C(FakePaperClient):
        def get_account(self) -> dict:
            return {"equity": 100_000.0, "cash": 100_000.0, "status": "ACTIVE"}

        def list_positions(self) -> list:
            return []

        def fetch_daily_closes(self, tickers, lookback_days=400) -> dict:
            return {t: series.get(t, pd.Series(
                [100.0 * (1 + 0.0004 * i) for i in range(len(idx))], index=idx))
                for t in tickers}

        def fetch_latest_prices(self, tickers) -> dict:
            return {t: float(series[t].iloc[-1]) if t in series else 100.0 for t in tickers}

        def trading_days(self, start, end) -> set:
            return {TODAY}

    return _C()


def _fake_epu_get(url: str, timeout: int = 90) -> bytes:
    """The EPU daily CSV, faked; the monthly .xlsx 'fails' (that source then reports FAILED)."""
    if url.endswith(".csv"):
        return b"day,month,year,daily_policy_index\n17,9,2026,101.5\n"
    raise OSError("not faked")


def _fake_regsho_get(url: str, timeout: int = 60) -> bytes:
    return (b"Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\n"
            b"20260917|SPY|1000|0|2000|B,Q,N\n")


def _one_article(client, universe, start, end, run_id, ingest_ts) -> pd.DataFrame:
    from intelligence import news_panel
    return pd.DataFrame([{
        "article_id": "lock-1", "created_at": pd.Timestamp(start, tz="UTC") + pd.Timedelta(hours=14),
        "updated_at": pd.Timestamp(start, tz="UTC") + pd.Timedelta(hours=14), "symbols": ["SPY"],
        "headline": "root-lock article", "summary": "", "content": "c", "source": "lock",
        "url": "", "author": "", "ingest_ts": ingest_ts, "ingest_run_id": run_id}],
        columns=news_panel.SCHEMA)


# The archiver jobs the daily run calls. One per module runs for real (pull_epu,
# pull_regsho_short_volume) over a faked transport; the rest are stubbed. A job added
# later and not listed here hits the refused socket and reports FAILED — fail-open,
# never a real request.
_ALT_STUBBED = ("pull_gpr", "snapshot_polymarket", "snapshot_kalshi", "snapshot_kxfed",
                "pull_fred_rate_path", "snapshot_cef", "pull_form4_index", "pull_usaspending")
_POS_STUBBED = ("pull_sec_ftd", "pull_naaim", "pull_finra_margin", "pull_finra_short_interest")


def _dotenv_names() -> tuple[str, ...]:
    """The variable NAMES the checkout's .env defines (values never read) — stripped like
    conftest's autouse fixture does, which a module-scoped fixture runs before."""
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
    # _creds reads a hard-coded .env path: it must never run here.
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
    mp.setattr(ad, "_get", _fake_epu_get)
    mp.setattr(ap, "_get_bytes", _fake_regsho_get)


def _seed(root: Path) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy(CHECKOUT / "config/substantially_identical.json",
                root / "config/substantially_identical.json")
    (root / "config/llm_settings.json").write_text(json.dumps(
        {"llm": {"kill_switch": False, "trading_kill_switch": False,
                 "monthly_budget_usd": 30.0, "max_output_tokens": 1500}}))
    # One constrained-analyst note under the ROOT with an already-expired prediction: the
    # harness resolves it only if it reads the root's notes, and logs it only if it writes
    # the root's log. The filename comes from the one declaration (T-348).
    from paper_trader.artifact_paths import ANALYST_NOTE
    note = ANALYST_NOTE.path_for(root, NOTE_AS_OF)
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(json.dumps({
        "as_of": NOTE_AS_OF, "market_assessment": "root lock",
        "predictions": [{"statement": "SPY above 1 on the expiry", "probability": 0.9,
                         "resolver": {"type": "price_above", "symbol": "SPY", "level": 1.0,
                                      "direction": "above", "by_date": PRED_EXPIRY,
                                      "mode": "terminal"}}]}))


@pytest.fixture(scope="module")
def drive(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """ONE real main() run (it costs seconds); every test below reads its record."""
    import scripts.archive_altdata_t136 as ad
    import scripts.archive_positioning_t136 as ap
    import scripts.run_paper_cloud_day as drv
    root = tmp_path_factory.mktemp("daily_run_root")
    out = io.StringIO()
    with pytest.MonkeyPatch.context() as mp:
        _hermetic(mp)
        _seed(root)
        before = _checkout_listing()
        with contextlib.redirect_stdout(out):
            rc = drv.main(["--allocator", "mean_variance", "--strategy", "trend_sleeve",
                           "--sleeve-notional-cap", "10000"],
                          now=NOW, client=_client(), cloud=_Cloud(), root=str(root))
        after = _checkout_listing()
        out_dirs = {"alt": ad.OUT_DIR, "pos": ap.OUT_DIR}
    return {"root": root, "rc": rc, "out": out.getvalue(),
            "diff": _diff(before, after), "out_dirs_after": out_dirs}


# --------------------------------------------------------------------------- #
# THE LOCK
# --------------------------------------------------------------------------- #
def test_the_daily_run_left_the_checkout_untouched(drive):
    """THE REGRESSION. Before 2026-11-19 this listed data/intel/analyst_eval_summary.json,
    data/intel/news_panel/news_202609.parquet, docs/State/performance_digest.md and the
    docs/Measurements/2026-09 archive copy (plus the alt-data parquets once step 7 ran)."""
    d = drive["diff"]
    assert not (d["created"] or d["modified"] or d["removed"]), (
        "the daily run, rooted at a tmp dir, wrote into the CHECKOUT "
        f"({CHECKOUT}) — created={d['created']} modified={d['modified']} "
        f"removed={d['removed']}. (A concurrent writer in this checkout during the ~seconds "
        "of the drive would also show here; re-run before blaming the run.)\n"
        + drive["out"][-3000:])


def test_the_eval_harness_scored_the_roots_note_into_the_roots_log(drive):
    root, out = drive["root"], drive["out"]
    summ = json.loads((root / "data/intel/analyst_eval_summary.json").read_text())
    assert summ["n_records"] == 1 and summ["n_resolvable"] == 1, summ
    log = [json.loads(ln) for ln in
           (root / "data/intel/analyst_predictions.jsonl").read_text().splitlines() if ln]
    assert [r["prediction_id"] for r in log] == [f"analyst_constrained:{NOTE_AS_OF}#0"]
    assert log[0]["outcome"] == 1
    assert "EVAL resolved=1/1" in out, out[-2000:]


def test_the_digest_and_its_archive_copy_are_under_the_root(drive):
    root, out = drive["root"], drive["out"]
    digest = root / "docs/State/performance_digest.md"
    archived = root / f"docs/Measurements/{TODAY:%Y-%m}/performance_digest_{TODAY}.md"
    assert digest.read_text().startswith(f"# Performance digest — {TODAY}")
    assert archived.read_text() == digest.read_text()
    line = next(ln for ln in out.splitlines() if "DIGEST     streams=" in ln)
    assert "ok=True" in line and f"path={digest}" in line, line


def test_the_news_partition_is_under_the_root(drive):
    part = drive["root"] / f"data/intel/news_panel/news_{TODAY:%Y%m}.parquet"
    df = pd.read_parquet(part)
    assert list(df["article_id"]) == ["lock-1"]
    assert "8. NEWS      append_today n_new=1" in drive["out"], drive["out"][-2000:]


def test_the_altdata_archivers_wrote_under_the_root_and_were_restored(drive):
    root = drive["root"]
    assert len(pd.read_parquet(root / "data/macro_data/alt/epu_daily_us.parquet")) == 1
    assert len(pd.read_parquet(root / "data/positioning/finra_regsho_short_volume.parquet")) == 1
    # the redirect is scoped to the run: the modules point back at their checkout after
    assert drive["out_dirs_after"] == {"alt": CHECKOUT / "data/macro_data/alt",
                                       "pos": CHECKOUT / "data/positioning"}


def test_the_census_reads_the_digest_the_step_wrote(drive):
    """Reader and writer now agree on the file: before, the census read <root>/docs/State/
    while the digest wrote the checkout's, so the clock MISSED on a day the digest ran."""
    hb = json.loads((drive["root"] / "data/state/paper_heartbeat.json").read_text())
    clock = hb["clock_census"]["detail"]["digest_written_weekly"]
    assert clock["status"] == "ADVANCED", clock


# --------------------------------------------------------------------------- #
# The model-gated writer: the intel pulse's event-call ledger
# --------------------------------------------------------------------------- #
def test_the_event_ledger_follows_the_pulse_root(tmp_path, monkeypatch):
    """With a model key the pulse runs D's event step, which appends to the event ledger.
    Its default is the module's checkout; the pulse must hand it the run's root."""
    import intelligence.event_call.run_forward as rf
    import paper_trader.intel_pulse as ip
    for name in _LIVE_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse)

    def _model(*_a: Any, **_k: Any) -> dict:
        raise RuntimeError("no model in this lock")

    monkeypatch.setattr(ip, "_model_call_or_none", lambda tier, settings: _model)
    monkeypatch.setattr(ip, "_scan_model_call_or_none", lambda settings: None)
    import intelligence.analyst.anthropic_adapter as aa
    monkeypatch.setattr(aa, "make_agentic_call", lambda *a, **k: _model)
    seen: dict[str, Any] = {}

    def _capture(as_of: str, **kw: Any) -> dict:
        seen.update(kw)
        return {"status": "ok", "reason": "captured", "n_ok": 0}

    monkeypatch.setattr(rf, "pulse_step", _capture)
    ip.run_intel_pulse("2026-09-18", portfolios={"sleeve": {}}, allowlist=["SPY"],
                       root=str(tmp_path), now_iso="2026-09-18T13:00:00",
                       load_panel=lambda *a, **k: pd.DataFrame(
                           columns=["created_at", "symbols", "headline", "content"]))
    assert seen.get("ledger_path") == tmp_path / "data/intel/event_calls.jsonl", seen
    assert seen.get("raw_dir") == str(tmp_path / "data/intel/llm_raw")


# --------------------------------------------------------------------------- #
# The cloud container: root IS the checkout, so every path is unchanged
# --------------------------------------------------------------------------- #
def test_where_the_root_is_the_checkout_every_path_is_the_old_one():
    """Production passes no root, so main() uses scripts/'s parent — the same directory
    every module's own ROOT resolves to. Joined onto it, each relative path is
    byte-for-byte the module constant the writer used before this change."""
    import intelligence.analyst.eval_harness as eh
    import intelligence.analyst.performance_digest as pdg
    import scripts.archive_altdata_t136 as ad
    import scripts.archive_positioning_t136 as ap
    import scripts.run_paper_cloud_day as drv
    from intelligence import news_panel
    from paper_trader import altdata_archive as aa
    from paper_trader import intel_pulse as ip
    from intelligence.event_call import event_service as es
    root = Path(drv.__file__).resolve().parents[1]
    assert root == CHECKOUT == eh.ROOT == pdg.ROOT == news_panel.ROOT == ad.ROOT == ap.ROOT
    assert root / eh.PRED_LOG_REL == eh.ROOT / "data" / "intel" / "analyst_predictions.jsonl"
    assert root / eh.SUMMARY_REL == eh.ROOT / "data" / "intel" / "analyst_eval_summary.json"
    assert root / eh.NOTES_REL == eh.NOTES_DIR
    assert root / eh.AGENTIC_NOTES_REL == eh.AGENTIC_NOTES_DIR
    assert root / eh.EVENT_LEDGER_REL == eh.EVENT_LEDGER == es.EVENT_CALLS_LEDGER
    assert root / ip.EVENT_LEDGER_REL == es.EVENT_CALLS_LEDGER
    assert root / pdg.DIGEST_REL == pdg.ROOT / "docs" / "State" / "performance_digest.md"
    assert root / pdg.ARCHIVE_REL == pdg.ROOT / "docs" / "Measurements"
    assert root / news_panel.PANEL_REL == news_panel.PANEL_DIR
    assert root / aa.ALT_REL == ad.OUT_DIR and root / aa.POSITIONING_REL == ap.OUT_DIR


def test_the_cloud_sync_moves_exactly_the_files_the_writers_now_write():
    """The readers that matter in the cloud are the S3 sync (cloud_state) and the census:
    both are root-relative, and these are the relative paths the writers now use."""
    import intelligence.analyst.eval_harness as eh
    import intelligence.analyst.performance_digest as pdg
    from intelligence import news_panel
    from paper_trader import altdata_archive as aa
    from paper_trader import intel_pulse as ip
    from paper_trader.cloud_state import ALTDATA_DIRS, DURABLE_PATHS, NEWS_PANEL_DIR
    for rel in (eh.PRED_LOG_REL, eh.SUMMARY_REL, eh.EVENT_LEDGER_REL, pdg.DIGEST_REL,
                Path(ip.EVENT_LEDGER_REL)):
        assert str(rel) in DURABLE_PATHS, rel
    assert str(news_panel.PANEL_REL) == NEWS_PANEL_DIR
    assert {aa.ALT_REL, aa.POSITIONING_REL} == set(ALTDATA_DIRS)


def test_an_explicit_path_still_wins_and_no_root_keeps_the_checkout():
    import intelligence.analyst.eval_harness as eh
    explicit = Path("/x/summary.json")
    assert eh._under_root(explicit, "/r", eh.SUMMARY_REL, eh.SUMMARY) == explicit
    assert eh._under_root(None, "/r", eh.SUMMARY_REL, eh.SUMMARY) == Path(
        "/r/data/intel/analyst_eval_summary.json")
    assert eh._under_root(None, None, eh.SUMMARY_REL, eh.SUMMARY) == eh.SUMMARY
