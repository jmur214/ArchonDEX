# tests/test_t412_review_locks_2026_11_24.py
"""T-412, the independent review of 2026-11-24: one lock per finding.

The first build's 24 reversion-proven locks all passed while the reviewer, running it, found
that account 3's trading input had changed, that a timed-out pull could erase S3 history, and
that the register said "14/14 fresh" with the eval and the pulse both raising. Each test below
names the finding it holds. Every one was proven by reversion.

The S3 here is a directory behind the REAL CloudState (only its ``_aws`` is replaced, with the
CLI's own compare rule and filters), so what is pulled, pushed and overwritten is the code's
doing, not a stub's.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import fnmatch
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_information_reaches_desks_t412 as h  # noqa: E402  (the shared main() harness)
from paper_trader.cloud_state import CloudState, CloudStateConfig  # noqa: E402

CHECKOUT = h.CHECKOUT
DAY = h.DAY1                                                # Thu 2026-09-17


# --------------------------------------------------------------------------- #
# A directory S3 behind the real CloudState
# --------------------------------------------------------------------------- #
class SimCloud(CloudState):
    """``aws s3 cp|sync`` against a directory. Sync copies a file when the destination is
    missing, the sizes differ, or the source is newer; downloads keep S3's mtime; filters are
    applied in order, the last match winning — the CLI's rules."""

    def __init__(self, s3: Path, root: Path, prefix: str = "paper_state") -> None:
        super().__init__(CloudStateConfig(bucket="b", prefix=prefix), root=str(root))
        self.s3 = s3
        self.ops: list[str] = []
        self.sync_hook: Optional[Callable[[list[str], Optional[float]], Any]] = None

    def _loc(self, u: str) -> Path:
        return self.s3 / u.split("s3://b/", 1)[1] if u.startswith("s3://") else Path(u)

    def _aws(self, *args: str, timeout_s: Optional[float] = None) -> Any:
        a = list(args)
        ok = subprocess.CompletedProcess(a, 0, "", "")
        if a[:2] == ["s3", "cp"]:
            src, dst = self._loc(a[2]), self._loc(a[3])
            if not src.exists():
                return subprocess.CompletedProcess(a, 1, "", "404 Not Found")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            self.ops.append(("up " if a[3].startswith("s3://") else "down ") + a[3 if a[3].startswith("s3://") else 2])
            return ok
        if a[:2] == ["s3", "sync"]:
            if self.sync_hook is not None:
                hooked = self.sync_hook(a, timeout_s)
                if hooked is not None:
                    return hooked
            self.sync_dirs(a)
            return ok
        self.ops.append("metric " + " ".join(a))
        return ok

    def sync_dirs(self, a: list[str], only: Optional[set[str]] = None) -> list[str]:
        src, dst, flt = self._loc(a[2]), self._loc(a[3]), a[4:]
        rules = [(flt[i], flt[i + 1]) for i in range(len(flt) - 1)
                 if flt[i] in ("--include", "--exclude")]
        moved: list[str] = []
        dst.mkdir(parents=True, exist_ok=True)
        for f in sorted(src.rglob("*")) if src.exists() else []:
            rel = f.relative_to(src).as_posix()
            if not f.is_file() or (only is not None and rel not in only):
                continue
            take = True
            for kind, pat in rules:
                if fnmatch.fnmatch(rel, pat):
                    take = kind == "--include"
            d = dst / rel
            if take and (not d.exists() or d.stat().st_size != f.stat().st_size
                         or f.stat().st_mtime > d.stat().st_mtime + 1e-6):
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, d)
                if a[3].startswith("s3://"):                # S3 LastModified = upload time
                    self.ops.append("up " + a[3] + "/" + rel)
                moved.append(rel)
        return moved


ALT = "data/macro_data/alt"


def _days(n: int = 117) -> list[str]:
    return pd.bdate_range(end="2026-09-16", periods=n).strftime("%Y-%m-%d").tolist()


def _seed_hoard(s3: Path) -> Path:
    alt = s3 / "altdata" / ALT
    alt.mkdir(parents=True, exist_ok=True)
    (s3 / "altdata/data/positioning").mkdir(parents=True, exist_ok=True)
    d = _days()
    for name in ("kalshi_kxfed_snapshots.parquet", "polymarket_snapshots.parquet"):
        pd.DataFrame({"snap_date": d, "ticker": "X", "id": "1"}).to_parquet(alt / name, index=False)
    pd.DataFrame({"series": "DFEDTARU", "observation_date": d, "value": 4.0}).to_parquet(
        alt / "fred_rate_path.parquet", index=False)
    return alt


def _rows(alt: Path) -> dict[str, int]:
    return {p.name: len(pd.read_parquet(p)) for p in sorted(alt.glob("*.parquet"))}


def _archive_today(root: Path) -> None:
    import scripts.archive_altdata_t136 as ad
    from paper_trader.altdata_archive import _out_dir_under_root
    with _out_dir_under_root(ad, root / ALT):
        for name in ("kalshi_kxfed_snapshots.parquet", "polymarket_snapshots.parquet"):
            ad._append(pd.DataFrame({"snap_date": ["2026-09-17"], "ticker": ["X"], "id": ["1"]}),
                       root / ALT / name, ["snap_date", "ticker"])


# --------------------------------------------------------------------------- #
# B1 — account 3's trading input
# --------------------------------------------------------------------------- #
def _analyst_history(root: Path) -> tuple[Path, Any]:
    from intelligence.analyst import eval_harness as eh
    from paper_trader.artifact_paths import ANALYST_NOTE
    idx = pd.bdate_range("2026-08-01", "2026-09-30")
    s = pd.Series(range(100, 100 + len(idx)), index=idx, dtype=float)
    for i in range(10):
        d = f"2026-09-{i + 1:02d}"
        p = ANALYST_NOTE.path_for(root, d)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"as_of": d, "predictions": [{
            "statement": f"SPY closes above 5{i}0 by next week", "probability": .6,
            "resolver": {"type": "price_above", "symbol": "SPY", "level": 100 + i,
                         "direction": "above", "by_date": "2026-09-15", "mode": "terminal"}}]}))
    eh.run("2026-09-18", price_fn=lambda _s: s, event_fn=lambda a, b: None, root=root)
    return root / eh.PRED_LOG_REL, s


def _event_week(root: Path) -> None:
    led = root / "data/intel/event_calls.jsonl"
    led.write_text("".join(json.dumps({
        "note_id": f"eventcall:acc{d}-{k}#2.02", "note_date": f"2026-09-{8 + d:02d}",
        "predictions": [{"statement": f"T{k} outperforms SPY over 5 sessions", "probability": .6,
                         "resolver": {"type": "relative_return", "symbol_a": f"T{k}",
                                      "symbol_b": "SPY", "op": "gt",
                                      "start_date": f"2026-09-{8 + d:02d}",
                                      "end_date": f"2026-09-{15 + d:02d}"}}],
        "event_call": {"document_ref": f"acc{d}-{k}#2.02", "symbol": f"T{k}"}}) + "\n"
        for d in range(5) for k in range(25)))


def test_B1_a_live_event_desk_leaves_the_traded_analysts_bundle_byte_identical(tmp_path, monkeypatch):
    """A week of the event desk (125 expired predictions in the shared log) used to fill all
    50 places and push every one of the analyst's own predictions out of the bundle behind
    the note account 3 trades."""
    from intelligence.analyst import context_builder as cb, eval_harness as eh
    log, s = _analyst_history(tmp_path)
    monkeypatch.setattr(cb._open_predictions_section, "__defaults__", (log,))
    kw = dict(portfolios={"sleeve": {"SPY": 0.3}}, load_panel=lambda **_k: pd.DataFrame())
    before = cb.canonical_json(cb.build_bundle("2026-09-21", **kw))
    _event_week(tmp_path)
    eh.run("2026-09-21", price_fn=lambda _s: s, event_fn=lambda a, b: None, root=tmp_path)
    assert sum('"event_interpreter"' in ln for ln in log.read_text().splitlines()) == 125
    assert cb.canonical_json(cb.build_bundle("2026-09-21", **kw)) == before
    # and it is what the pre-T-412 rule produced from the analysts' rows alone
    own = [json.loads(ln) for ln in log.read_text().splitlines()]
    own = {r["prediction_id"]: r for r in own if r["source"] != "event_interpreter"}
    legacy = sorted(({"statement": r["statement"], "probability": r["probability"],
                      "horizon": r.get("horizon")} for r in own.values()),
                    key=lambda x: str(x["statement"]))[:50]
    assert json.loads(before)["open_predictions"]["open"] == legacy and len(legacy) == 10


def test_B1_a_row_with_no_source_is_kept_as_the_analysts_unless_it_is_an_event_call():
    from intelligence.analyst.eval_harness import is_analyst_row
    assert is_analyst_row({"note_id": "analyst:2026-07-01"})
    assert is_analyst_row({"source": "analyst_agentic"})
    assert not is_analyst_row({"note_id": "eventcall:a#2.02"})
    assert not is_analyst_row({"source": "event_interpreter"})
    assert not is_analyst_row({"source": "some_future_desk"})


def test_B1_an_event_that_settles_early_enters_the_log_on_its_own_date(tmp_path):
    """Logging it the day the event settles would put a row into account 3's bundle days
    before it ever appeared there."""
    from intelligence.analyst import eval_harness as eh
    note = {"note_id": "n", "note_date": "2026-09-01", "predictions": [{
        "statement": "s", "probability": .5, "resolver": {
            "type": "event_occurs", "source": "fomc_calendar", "event_id": "2026-09-09",
            "predicate": {"action": "cut"}, "by_date": "2026-09-25"}}]}
    kw = dict(notes=[note], event_fn=lambda a, b: "cut", root=tmp_path)
    eh.run("2026-09-18", **kw)
    assert not (tmp_path / eh.PRED_LOG_REL).exists()
    eh.run("2026-09-25", **kw)
    rows = eh._load_log(tmp_path / eh.PRED_LOG_REL)
    assert [r["outcome"] for r in rows] == [1]


def test_B1_the_agentic_arm_still_reads_only_the_analysts_resolved_record(tmp_path):
    from intelligence.analyst import eval_harness as eh
    from intelligence.analyst.agentic_readers import build_readers
    _log, s = _analyst_history(tmp_path)
    before = build_readers(tmp_path, "2026-09-21")["query_resolved_predictions"]({"limit": 20})
    _event_week(tmp_path)
    eh.run("2026-09-21", price_fn=lambda _s: s, event_fn=lambda a, b: None, root=tmp_path)
    after = build_readers(tmp_path, "2026-09-21")["query_resolved_predictions"]({"limit": 20})
    assert before and after == before


# --------------------------------------------------------------------------- #
# Found while fixing: settlement before the event (switched on by the early pull)
# --------------------------------------------------------------------------- #
def test_an_event_is_settled_only_once_the_series_reaches_its_date(tmp_path):
    """FRED's last value was carried forward to any date asked for: a December FOMC meeting
    asked about in September settled "hold", a December strike settled "yes", and a thesis
    falsifier on either FIRED — permanently."""
    from intelligence.analyst import eval_harness as eh
    alt = tmp_path / ALT
    alt.mkdir(parents=True)
    d = pd.date_range("2026-08-01", "2026-09-17", freq="D").strftime("%Y-%m-%d")
    pd.DataFrame({"series": "DFEDTARU", "observation_date": d,
                  "value": [4.5 if x < "2026-09-10" else 4.25 for x in d]}).to_parquet(
        alt / "fred_rate_path.parquet", index=False)
    pd.DataFrame([{"snap_date": "2026-09-16", "ticker": f"KX-{e[5:7]}", "floor_strike": 4.0,
                   "strike_type": "greater", "expiration_time": f"{e}T18:00:00Z"}
                  for e in ("2026-09-16", "2026-12-16")]
                 # a finalized market's newest row: Kalshi drops its expiration_time
                 + [{"snap_date": "2026-09-17", "ticker": "KX-09", "floor_strike": 4.0,
                     "strike_type": "greater", "expiration_time": None}]).to_parquet(
        alt / "kalshi_kxfed_snapshots.parquet", index=False)
    fn = eh.event_fn_for_root(tmp_path)
    assert fn("fomc_calendar", "2026-12-16") is None
    assert fn("kalshi_settlement", "KX-12") is None
    assert fn("fomc_calendar", "2026-09-09") == "cut"       # positive control: it happened
    assert fn("kalshi_settlement", "KX-09") == "yes"
    spec = {"type": "event_occurs", "source": "kalshi_settlement", "event_id": "KX-12",
            "predicate": {"settles": "yes"}, "by_date": "2026-12-20"}
    st, _ = eh.resolve_falsifier({"kind": "resolver", "resolver": spec}, "2026-09-01",
                                 "2026-09-18", event_fn=fn)
    assert st == "pending"


# --------------------------------------------------------------------------- #
# B2 / item 6 — the shared hoard in S3
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("mode", ["early_pull_times_out", "every_sync_fails"])
def test_B2_an_incomplete_pull_never_costs_s3_history(tmp_path, mode):
    """117 rows became 1: a bounded pull landed one file, reported success, and step 7
    archived into the fragment and pushed it. The rc≠0 form predates T-412."""
    import scripts.run_paper_cloud_day as drv
    s3, root = tmp_path / "s3", tmp_path / "root"
    alt = _seed_hoard(s3)
    before = _rows(alt)
    cloud = SimCloud(s3, root)

    def hook(a: list[str], timeout_s: Optional[float]) -> Any:
        if not a[2].startswith("s3://") or "macro_data/alt" not in a[2]:
            return None
        if mode == "every_sync_fails" or timeout_s is not None:
            cloud.sync_dirs(a, only={"fred_rate_path.parquet"})       # one file landed
            return subprocess.CompletedProcess(a, 124 if timeout_s else 1, "", "stopped")
        return None
    cloud.sync_hook = hook
    sync = drv._AltdataSync(cloud)
    assert sync.ensure(timeout_s=1.0) is False              # never "pulled" when it was not
    clean = sync.ensure()
    _archive_today(root)
    pushed = cloud.push_altdata()
    after = _rows(alt)
    if mode == "early_pull_times_out":
        assert (clean, pushed) == (True, True)
        assert after == {**before, "kalshi_kxfed_snapshots.parquet": 118,
                         "polymarket_snapshots.parquet": 118}
    else:
        assert (clean, pushed) == (False, False) and after == before
        assert "NOT pushed" in cloud.altdata_push_notes[0]


def test_B2_one_failed_directory_makes_the_pull_incomplete(tmp_path):
    cloud = SimCloud(tmp_path / "s3", tmp_path / "root")
    _seed_hoard(tmp_path / "s3")
    cloud.sync_hook = lambda a, t: (subprocess.CompletedProcess(a, 1, "", "denied")
                                    if "positioning" in a[2] else None)
    assert cloud.pull_altdata() is False and cloud.altdata_clean is False


def test_B2_the_8k_history_survives_an_early_pull_that_missed_it(tmp_path):
    """The same hole, for account 1's own panel: built without its history, it must not
    replace that history."""
    s3, root = tmp_path / "s3", tmp_path / "root"
    alt = _seed_hoard(s3)
    panel = "edgar_8k_items.parquet"
    pd.DataFrame({"accession": [f"a{i}" for i in range(50)],
                  "filing_date": ["2026-09-01"] * 50}).to_parquet(alt / panel, index=False)
    cloud = SimCloud(s3, root)
    cloud.altdata_owner_8k = True
    cloud.sync_hook = lambda a, t: (subprocess.CompletedProcess(a, 124, "", "timeout")
                                    if t is not None else None)
    from paper_trader.cloud_state import ALTDATA_EARLY_FILES
    assert cloud.pull_altdata(timeout_s=1.0, only=ALTDATA_EARLY_FILES) is False
    (root / ALT).mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"accession": ["new"], "filing_date": ["2026-09-16"]}).to_parquet(
        root / ALT / panel, index=False)                    # the fetch, over nothing
    assert cloud.pull_altdata() is True
    cloud.push_altdata()
    assert len(pd.read_parquet(alt / panel)) == 50
    assert any("8-K files NOT pushed" in n for n in cloud.altdata_push_notes)


def _sec(day: str) -> Callable[..., bytes]:
    def get(url: str, timeout: int = 90) -> bytes:
        if url.endswith("company_tickers.json"):
            return json.dumps({"0": {"cik_str": 1000, "ticker": "ACME"}}).encode()
        if "daily-index" in url:
            d = url.split("form.")[1][:8]
            D = dt.date(int(d[:4]), int(d[4:6]), int(d[6:]))
            if D >= dt.date.fromisoformat(day) or D.weekday() >= 5:
                raise OSError("404")
            return f"8-K  ACME  1000  {d}  edgar/data/1000/acc-{d}.txt\n".encode()
        ds = pd.bdate_range("2026-09-01", day)
        return json.dumps({"filings": {"recent": {
            "accessionNumber": [f"acc-{x:%Y%m%d}" for x in ds],
            "filingDate": [f"{x:%Y-%m-%d}" for x in ds], "acceptanceDateTime": [""] * len(ds),
            "form": ["8-K"] * len(ds), "items": ["2.02"] * len(ds),
            "primaryDocument": ["d"] * len(ds)}}}).encode()
    return get


def test_6_three_accounts_on_one_prefix_never_roll_the_8k_panel_back(tmp_path, monkeypatch):
    """Accounts 2 and 3 pull before account 1's push and push after it (09:45/09:50/09:55).
    S3 froze at day 1 (2 of 16 filings) and they raised a false stale alarm from day 4."""
    import scripts.archive_altdata_t136 as ad
    import scripts.run_paper_cloud_day as drv
    from paper_trader.altdata_archive import (ACCOUNT_1_FEEDS, _out_dir_under_root,
                                              assess_feed_health)
    monkeypatch.setattr(ad, "EDGAR_8K_RATE_SLEEP_S", 0.0)
    s3 = tmp_path / "s3"
    alt = _seed_hoard(s3)
    clock = [1_700_000_000.0]

    def stamp(ops: list[str]) -> None:                       # S3 LastModified = upload time
        for op in ops:
            if op.startswith("up s3://b/altdata/"):
                clock[0] += 60
                os.utime(s3 / op.split("s3://b/", 1)[1], (clock[0], clock[0]))
    for day in pd.bdate_range("2026-09-14", "2026-10-02"):
        ds = f"{day:%Y-%m-%d}"
        monkeypatch.setattr(ad, "_get", _sec(ds))
        cl = {k: SimCloud(s3, tmp_path / f"{k}_{ds}") for k in ("a1", "a2", "a3")}
        cl["a1"].altdata_owner_8k = True                     # the driver's rule
        drv._AltdataSync(cl["a1"]).ensure(timeout_s=60)
        with _out_dir_under_root(ad, cl["a1"].root / ALT):
            ad.pull_8k_items(["ACME"], as_of=ds)
        for k in ("a2", "a3"):
            drv._AltdataSync(cl[k]).ensure()
        for k in ("a1", "a2", "a3"):
            if k == "a1":
                drv._AltdataSync(cl[k]).ensure()
            # every account archives the shared feeds
            f = cl[k].root / ALT / "polymarket_snapshots.parquet"
            ad._append(pd.DataFrame({"snap_date": [ds], "ticker": ["X"], "id": ["1"]}), f,
                       ["snap_date", "ticker"])
            assert cl[k].push_altdata() is True
            stamp(cl[k].ops)
        for k in ("a2", "a3"):                               # they neither hold nor gate it
            assert not (cl[k].root / ALT / "edgar_8k_items.parquet").exists()
            _d, stale = assess_feed_health(cl[k].root, not_collected_here=ACCOUNT_1_FEEDS)
            assert not [x for x in stale if x.startswith("edgar_8k")]
    have = set(pd.read_parquet(alt / "edgar_8k_items.parquet")["filing_date"])
    assert have == set(pd.bdate_range("2026-09-10", "2026-10-01").strftime("%Y-%m-%d"))


def test_6_a_file_this_run_did_not_change_is_never_pushed_over_a_newer_one(tmp_path):
    """The same race for ANY hoard file: an account whose fetch failed holds an older,
    smaller copy, and `aws s3 sync` uploads whenever sizes differ."""
    s3 = tmp_path / "s3"
    alt = _seed_hoard(s3)
    slow = SimCloud(s3, tmp_path / "slow")
    assert slow.pull_altdata() is True                       # its copy: 117 rows
    f = alt / "polymarket_snapshots.parquet"                 # another account appends …
    pd.DataFrame({"snap_date": _days() + ["2026-09-17"], "ticker": "X", "id": "1"}).to_parquet(
        f, index=False)
    (tmp_path / "slow" / ALT / "part.parquet.1a2B3c4D").write_text("killed download")
    assert slow.push_altdata() is True                       # … and this one pushes after
    assert len(pd.read_parquet(f)) == 118
    assert not (alt / "part.parquet.1a2B3c4D").exists()


# --------------------------------------------------------------------------- #
# main()-level drives on the directory S3
# --------------------------------------------------------------------------- #
PX = {"SPY": 600.0, "AGG": 98.0, "GLD": 420.0}


def _client(day: dt.date, *, forming: Optional[float] = None, calls: Optional[list] = None) -> Any:
    from paper_trader.paper_client import FakePaperClient
    idx = pd.bdate_range(end=pd.Timestamp(day) - pd.Timedelta(days=1), periods=400)

    class _C(FakePaperClient):
        def get_account(self) -> dict:
            return {"equity": 100_000.0, "cash": 100_000.0, "status": "ACTIVE"}

        def list_positions(self) -> list:
            return []

        def submit_order(self, **k: Any) -> Any:
            if calls is not None:
                calls.append(("SUBMIT", k["symbol"]))
            self.script_polls(k["client_order_id"], [{
                "broker_order_id": "b-" + k["client_order_id"][-8:], "status": "filled",
                "filled_qty": k["qty"], "filled_avg_price": PX.get(k["symbol"], 100.0),
                "filled_at": f"{day}T13:46:00+00:00"}])
            return super().submit_order(**k)

        def fetch_daily_closes(self, tickers, lookback_days=400) -> dict:
            bad = [t for t in tickers if "-" in t or "^" in t]
            if bad:                                         # the broker rejects the BATCH
                raise RuntimeError(f"invalid symbol: {bad[0]}")
            out = {}
            for t in tickers:
                s = pd.Series([PX.get(t, 100.0) * (1 - 0.0004 * (len(idx) - 1 - i))
                               for i in range(len(idx))], index=idx)
                if forming is not None:                     # 09:45 ET: today's partial bar
                    s = pd.concat([s, pd.Series([forming], index=[pd.Timestamp(day)])])
                out[t] = s
            return out

        def fetch_latest_prices(self, tickers) -> dict:
            return {t: PX.get(t, 100.0) for t in tickers}

        def trading_days(self, start, end) -> set:
            return {h.DAY1, h.DAY2}
    return _C()


def _seed_marks(root: Path, day: dt.date) -> None:
    p = root / "data/state/price_basis_marks.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"marks": {t: {"px": v, "run_date": str(day - dt.timedelta(days=1))}
                                       for t, v in PX.items()}}))


def _main(tmp_path: Path, *, patch: Optional[Callable[[pytest.MonkeyPatch], None]] = None,
          cloud: Any = None, client: Any = None, day: dt.date = DAY, armed: bool = True,
          strategy: str = "trend_sleeve") -> dict[str, Any]:
    import scripts.run_paper_cloud_day as drv
    root, s3 = tmp_path / "root", tmp_path / "s3"
    if not root.exists():
        root.mkdir()
        h._seed_root(root)
        _seed_marks(root, day)
    if cloud is None:
        h._seed_s3_altdata(s3)
        cloud = SimCloud(s3, root)
    out, err = io.StringIO(), io.StringIO()
    raised: Optional[BaseException] = None
    rc: Any = None
    with pytest.MonkeyPatch.context() as mp:
        h._hermetic(mp)
        mp.setattr(drv, "now_et", lambda: h.NOW[day])
        if patch is not None:
            patch(mp)
        argv = ["--allocator", "mean_variance", "--strategy", strategy,
                "--sleeve-notional-cap", "10000"] + ([] if armed else ["--dry-run"])
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = drv.main(argv, now=h.NOW[day], client=client or _client(day), cloud=cloud,
                              root=str(root))
        except BaseException as exc:  # noqa: BLE001 — a simulated kill
            raised = exc
    hb_p = root / "data/state/paper_heartbeat.json"
    return {"rc": rc, "raised": raised, "out": out.getvalue(), "err": err.getvalue(),
            "root": root, "s3": s3, "cloud": cloud,
            "hb": json.loads(hb_p.read_text()) if hb_p.exists() else {}}


class _Killed(BaseException):
    """Not an Exception: like a SIGKILL, no fail-open handler can absorb it."""


def _kill_early_pull(mp: pytest.MonkeyPatch) -> None:
    def boom(self: Any, timeout_s: Any = None, only: Any = None) -> bool:
        raise _Killed("early pull")
    mp.setattr(CloudState, "pull_altdata", boom)


def _kill_feed(mp: pytest.MonkeyPatch) -> None:
    import paper_trader.altdata_archive as A
    mp.setattr(A, "run_8k_feed", lambda *a, **k: (_ for _ in ()).throw(_Killed("8-K feed")))


def _kill_interpreter(mp: pytest.MonkeyPatch) -> None:
    import intelligence.event_call.run_forward as rf
    mp.setattr(rf, "run_forward", lambda *a, **k: (_ for _ in ()).throw(_Killed("interpreter")))


@pytest.mark.parametrize("kill", [_kill_early_pull, _kill_feed, _kill_interpreter])
def test_7_a_run_killed_in_a_new_slow_step_keeps_its_order_journal(tmp_path, kill):
    """Between the orders and the main push there are now minutes of network. A container
    killed there used to lose the day's journal: tomorrow every fill is unexplained."""
    r = _main(tmp_path, patch=kill)
    assert isinstance(r["raised"], _Killed)
    s3 = r["s3"] / "paper_state/data/paper_state/orders.jsonl"
    local = r["root"] / "data/paper_state/orders.jsonl"
    assert s3.exists() and s3.read_text() == local.read_text()
    rows = [json.loads(ln) for ln in s3.read_text().splitlines()]
    assert {x.get("ticker") for x in rows} >= {"SPY"} and len(rows) >= 3
    hb = json.loads((r["s3"] / "paper_state/data/state/paper_heartbeat.json").read_text())
    assert hb["last_run"]["run_date"] == str(DAY)
    assert "source_register" not in hb                       # it never reached its tail …
    from scripts.fleet_health import judge_source_register
    assert "did not reach its tail" in judge_source_register("a1", hb, True)[0][0]   # … said so
    assert not [o for o in r["cloud"].ops if "PaperRunCanonical" in o]   # no metric: alarm fires


def test_7_the_post_trade_push_is_account_1s_and_precedes_the_new_steps(tmp_path):
    r = _main(tmp_path)
    assert r["rc"] == 0, r["err"][-2000:]
    assert r["out"].index("POST-TRADE PUSH ok") < r["out"].index("ALTDATA-PULL") \
        < r["out"].index("EDGAR-8K")
    other = _main(tmp_path / "a3", strategy="reconcile_only") if (tmp_path / "a3").mkdir() is None else None
    assert "POST-TRADE PUSH" not in other["out"]


def test_B2_the_driver_does_not_push_a_hoard_it_could_not_pull(tmp_path):
    root, s3 = tmp_path / "root", tmp_path / "s3"
    root.mkdir()
    h._seed_root(root)
    _seed_marks(root, DAY)
    alt = _seed_hoard(s3)
    before = _rows(alt)
    cloud = SimCloud(s3, root)
    cloud.sync_hook = lambda a, t: (subprocess.CompletedProcess(a, 1, "", "AccessDenied")
                                    if a[2].startswith("s3://b/altdata") else None)
    r = _main(tmp_path, cloud=cloud)
    assert r["rc"] == 0 and _rows(alt) == before
    assert not [o for o in cloud.ops if o.startswith("up s3://b/altdata")]
    assert r["hb"]["altdata"]["degraded"] is True
    assert "hoard_pull_incomplete" in r["hb"]["altdata"]["reason"]


def test_8_todays_partial_bar_settles_nothing_and_fires_nothing(tmp_path):
    """The run is at 09:45 ET and the vendor already returns a bar dated today. A crash print
    in it FIRED a terminal, a touch and a drawdown falsifier — a permanent close."""
    root = tmp_path / "root"
    root.mkdir()
    h._seed_root(root)
    _seed_marks(root, DAY)
    f = lambda res: [{"kind": "resolver", "check_by": "2026-12-31", "statement": "s",
                      "resolver": res}]
    st = {"_schema": "thesis_book/v1", "open": [
        h._open_pos("t-term", "QQQ", f({"type": "price_above", "symbol": "QQQ", "level": 50.0,
                                        "direction": "below", "by_date": str(DAY),
                                        "mode": "terminal"})),
        h._open_pos("t-touch", "QQQ", f({"type": "price_above", "symbol": "QQQ", "level": 50.0,
                                         "direction": "below", "by_date": "2026-12-18",
                                         "mode": "touch"})),
        h._open_pos("t-dd", "QQQ", f({"type": "dd_exceeds", "symbol": "QQQ",
                                      "threshold_pct": 30.0, "start_date": "2026-08-03",
                                      "end_date": "2026-12-01"}))],
        "closed": [], "days": [], "pending": []}
    (root / "data/state/thesis_book_machine.json").write_text(json.dumps(st))
    from paper_trader.artifact_paths import ANALYST_NOTE
    ANALYST_NOTE.path_for(root, "2026-09-15").write_text(json.dumps({
        "as_of": "2026-09-15", "predictions": [{"statement": "SPY below 100 today",
        "probability": .1, "resolver": {"type": "price_above", "symbol": "SPY", "level": 100.0,
                                        "direction": "below", "by_date": str(DAY),
                                        "mode": "terminal"}}]}))
    r = _main(tmp_path, client=_client(DAY, forming=1.0), armed=False)
    book = json.loads((root / "data/state/thesis_book_machine.json").read_text())
    assert [p["thesis_id"] for p in book["open"]] == ["t-term", "t-touch", "t-dd"], r["out"][-1500:]
    assert {v[0]["status"] for v in book["days"][-1]["falsifiers"].values()} == {"pending"}
    rows = [json.loads(ln) for ln in
            (root / "data/intel/analyst_predictions.jsonl").read_text().splitlines()]
    today = next(x for x in rows if x["statement"] == "SPY below 100 today")
    assert today["resolvable"] is False and today["outcome"] is None
    assert r["hb"]["source_register"]["readers"]["eval_harness"]["outcome"]["n_awaiting"] == 1


# --------------------------------------------------------------------------- #
# 3 — the register tells the truth about a broken path
# --------------------------------------------------------------------------- #
def test_3_a_reader_that_raises_is_a_problem_however_fresh_its_input(tmp_path):
    def patch(mp: pytest.MonkeyPatch) -> None:
        import intelligence.analyst.eval_harness as eh
        mp.setattr(eh, "run", lambda *a, **k: (_ for _ in ()).throw(TypeError("boom")))
        import paper_trader.intel_pulse as ip
        mp.setattr(ip, "run_intel_pulse", lambda *a, **k: (_ for _ in ()).throw(KeyError("x")))
        import paper_trader.event_shadow_book as eb
        mp.setattr(eb.EventShadowBook, "record",
                   lambda *a, **k: (_ for _ in ()).throw(ValueError("desk")))
    reg = _main(tmp_path, patch=patch, armed=False)["hb"]["source_register"]
    said = " ".join(reg["problems"])
    assert reg["degraded"] and "eval_harness: raised TypeError" in said
    assert "intel_pulse: raised KeyError" in said and "event_desk: raised ValueError" in said


@pytest.mark.parametrize("ev, says", [
    ({"status": "degraded", "reason": "error:KeyError"}, "degraded: error:KeyError"),
    ({"status": "degraded", "reason": "no_model_adapter"}, "no_model_adapter"),
    ({"status": "ok", "n_documents": 9, "n_ok": 0, "n_no_body": 9}, "interpreted none"),
    ({"status": "ok", "n_documents": 9, "n_ok": 4, "n_no_body": 5}, "no filing body for 5 of 9"),
    ({"status": "ok", "n_documents": 9, "n_ok": 8, "n_skipped": 1}, "refused or failed"),
    ({"status": "ok", "n_documents": 9, "n_ok": 4, "n_deferred": 5}, "deferred"),
    ({"status": "ok", "n_documents": 9, "n_ok": 3, "n_invalid": 6}, "replies invalid"),
    ({"status": "ok", "n_documents": 1, "n_ok": 1, "feed": {"ok": True, "n_bad_dates": 2}},
     "unparseable filing date"),
    ({}, "returned nothing"),
])
def test_3_every_way_the_interpreter_can_produce_nothing_is_named(ev, says):
    from paper_trader.source_register import event_interpreter_problems
    assert says in " ".join(event_interpreter_problems(ev))


def test_3_a_whole_day_of_the_interpreter_is_not_a_problem():
    from paper_trader.source_register import event_interpreter_problems
    assert event_interpreter_problems({"status": "ok", "n_documents": 30, "n_ok": 27,
                                       "n_no_body": 2, "n_invalid": 1, "n_deferred": 0,
                                       "n_skipped": 0, "feed": {"ok": True}}) == []
    assert event_interpreter_problems({"status": "ok", "n_documents": 0}) == []   # a re-run


IDX = "8-K  ACME  1000  {d}  edgar/data/1000/acc-{d}.txt\n"


def _feed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, get: Callable[..., bytes],
          universe: Optional[list[str]] = None, **kw: Any) -> str:
    import scripts.archive_altdata_t136 as ad
    from paper_trader.altdata_archive import _out_dir_under_root
    monkeypatch.setattr(ad, "_get", get)
    monkeypatch.setattr(ad, "EDGAR_8K_RATE_SLEEP_S", 0.0)
    with _out_dir_under_root(ad, tmp_path):
        return ad.pull_8k_items(universe or ["ACME"], as_of="2026-09-17", **kw)


def _with(base: Callable[..., bytes], match: str, reply: Any) -> Callable[..., bytes]:
    def get(url: str, timeout: int = 90) -> bytes:
        if match in url:
            if isinstance(reply, Exception):
                raise reply
            return reply
        return base(url, timeout)
    return get


@pytest.mark.parametrize("match, reply, kw, verdict, says", [
    ("daily-index", b"", {}, "FAILED", "holding no 8-K row"),
    ("daily-index", b"<html>Undeclared Automated Tool</html>", {}, "FAILED", "block page"),
    ("form.20260916.idx", OSError("403"), {}, "PARTIAL", "prior business day's index (2026-09-16) is missing"),
    ("form.20260916.idx", b"<html>", {}, "PARTIAL", "holds no 8-K row"),
    ("submissions", json.dumps({"filings": {"latest": {}}}).encode(), {}, "FAILED", "JSON shape"),
    ("submissions", OSError("429"), {}, "FAILED", "1 of 1 submissions requests failed"),
    ("nothing", b"", {"time_budget_s": 1e-9}, "FAILED", "time budget was spent"),
    ("company_tickers", b"{}", {}, "FAILED", "mapped to an SEC CIK"),
])
def test_3_a_feed_that_did_not_deliver_says_so(tmp_path, monkeypatch, match, reply, kw, verdict, says):
    line = _feed(tmp_path, monkeypatch, _with(_sec("2026-09-17"), match, reply), **kw)
    assert line.startswith(f"edgar_8k: {verdict}") and says in line, line
    import paper_trader.altdata_archive as A
    monkeypatch.setattr(A, "tracked_universe", lambda *a: ["ACME"])
    import scripts.archive_altdata_t136 as ad
    monkeypatch.setattr(ad, "pull_8k_items", lambda *a, **k: line)
    assert A.run_8k_feed(str(tmp_path), as_of="2026-09-17").ok is False


def test_3_a_healthy_feed_is_ok_and_a_truncated_ticker_map_is_never_cached(tmp_path, monkeypatch):
    import scripts.archive_altdata_t136 as ad
    line = _feed(tmp_path, monkeypatch, _sec("2026-09-17"))
    assert line.startswith("edgar_8k: +3 new") and "PARTIAL" not in line, line
    cache = tmp_path / ad.EDGAR_TICKERS_CACHE
    good = cache.read_text()
    uni = ["ACME"] + [f"T{i}" for i in range(19)]            # the map resolves 1 of 20
    line = _feed(tmp_path, monkeypatch, _sec("2026-09-17"), universe=uni)
    assert line.startswith("edgar_8k: PARTIAL") and "resolves 5% of 20" in line, line
    assert cache.read_text() == good


def test_3_the_eval_share_has_stated_exclusions_and_no_permanent_alarm(tmp_path):
    from intelligence.analyst import eval_harness as eh
    log = tmp_path / eh.PRED_LOG_REL
    log.parent.mkdir(parents=True)

    def row(pid: str, at: str, ok: bool, due: str, src: str = "price", **kw: Any) -> str:
        return json.dumps({"prediction_id": pid, "resolved_at": at, "resolvable": ok,
                           "resolve_date": due, "resolve_source": src,
                           "resolve_detail": "source_absent_or_stale",
                           "resolver": {"type": "price_above", "symbol": pid.upper(), **kw}}) + "\n"
    T = "2026-09-18"
    log.write_text("".join([
        row("a", T, True, "2026-09-16"), row("b", T, False, "2026-09-16"),
        row("c", T, False, "2026-09-16"), row("d", T, False, "2026-09-16"),
        row("e", T, False, T)]))                             # its own bar does not exist yet
    rt = eh.resolved_today(T, root=tmp_path)
    assert (rt["n_judged"], rt["n_resolved"], rt["n_awaiting"]) == (4, 1, 1)
    assert "resolved 1 of 4" in eh.resolution_problem(rt)
    # a symbol that can never be priced: chronic, not a daily alarm …
    old = [row("dead", f"2026-09-{d:02d}", False, "2026-09-01") for d in (11, 14, 15, 16, 17)]
    log.write_text("".join(old + [row("dead", T, False, "2026-09-01"), row("ok", T, True, T)]))
    rt = eh.resolved_today(T, root=tmp_path)
    assert rt["n_chronic"] == 1 and rt["n_judged"] == 1 and eh.resolution_problem(rt) is None
    # … until there are several
    many = "".join(row(f"d{i}", f"2026-09-{d:02d}", False, "2026-09-01")
                   for i in range(5) for d in (14, 15, 16, 18))
    log.write_text(many)
    assert "5 prediction(s) unresolvable" in eh.resolution_problem(
        eh.resolved_today(T, root=tmp_path))


def test_3_a_register_that_fails_itself_is_never_printed_as_clean():
    from paper_trader import source_register as sr
    reg = sr.SourceRegister("/nonexistent", sr.ACCOUNT_1, "2026-09-17")
    reg._reads = None                                        # type: ignore[assignment]
    blk = reg.block()
    assert blk["failed"] is True and blk["degraded"] is True
    assert "FAILED" in sr.register_line(blk) and "no declared" not in sr.register_line(blk)
    none = sr.SourceRegister("/nonexistent", "deploy_candidate", "2026-09-17").block()
    assert "no declared information sources" in sr.register_line(none)


def test_3_a_block_that_cannot_be_recorded_is_notified_and_left_as_failed(tmp_path):
    from paper_trader.heartbeat import PaperHeartbeat
    r = _main(tmp_path, armed=False, patch=lambda mp: mp.setattr(
        PaperHeartbeat, "record_source_register",
        lambda self, b: (_ for _ in ()).throw(RuntimeError("disk"))))
    assert r["hb"]["source_register"]["failed"] is True
    assert "could not be recorded" in (r["root"] / "data/state/paper_alerts.log").read_text()


def test_3_fleet_health_reads_the_register():
    from scripts import fleet_health as fh
    hb = {"last_run": {"run_date": "2026-12-01", "canonical": True}}
    ok = {"as_of": "2026-12-01", "n_sources": 9, "degraded": False}
    j = lambda blk, req=True: fh.judge_source_register("a", {**hb, "source_register": blk}, req)
    assert j(ok) == ([], [])
    assert "FAILED" in j({**ok, "failed": True, "n_sources": None})[0][0]
    assert "not 2026-12-01" in j({**ok, "as_of": "2026-11-30"})[0][0]
    problems, notes = j({**ok, "degraded": True, "n_problems": 2, "problems": ["x", "y"]})
    assert problems == [] and "2 information-path problem(s)" in notes[0]
    assert fh.judge_source_register("a", hb, True)[0] and not fh.judge_source_register("a", hb, False)[0]


def _fleet(reg: dict[str, Any], run_date: str) -> Any:
    from scripts import fleet_health as fh
    docs = {f"{p}/data/state/paper_heartbeat.json": {
        "last_run": {"run_date": run_date, "canonical": True},
        **({"source_register": reg[a]} if reg.get(a) else {})} for a, p in fh.ACCOUNTS.items()}
    book = {"days": [{"date": run_date, "book_growth": 1.0, "twin_growth": 1.0}]}
    return fh.evaluate(lambda k: (json.dumps(docs.get(k, book)).encode(), ""),
                       dt.date.fromisoformat(run_date))


def test_3_the_register_is_required_once_any_account_has_written_one():
    from scripts import fleet_health as fh
    a1, a2, a3 = list(fh.ACCOUNTS)
    blk = {"as_of": "2026-11-30", "n_sources": 1, "degraded": False}
    assert _fleet({}, "2026-11-30").ok                       # before the deploy: not required
    v = _fleet({a1: blk, a2: blk}, "2026-11-30")             # account 3's run never finished
    assert not v.ok and [p for p in v.problems if p.startswith(a3)]
    assert _fleet({a1: blk, a2: blk, a3: blk}, "2026-11-30").ok
    assert len(_fleet({}, "2026-12-07").problems) == 3       # merged but never deployed


# --------------------------------------------------------------------------- #
# 4 — one bad symbol; 5 — one bad prediction; one bad document
# --------------------------------------------------------------------------- #
def test_4_one_bad_symbol_never_empties_the_batch(tmp_path):
    """BRK-B (the membership file's spelling) left the event desk with 0 of 4 valid calls."""
    from paper_trader.event_shadow_book import EventShadowBook
    from paper_trader.report_prices import fetch_closes, last_prices
    syms = ["AAPL", "MSFT", "JPM", "BRK-B", "^GSPC", "QQQQQQQ"]
    led = tmp_path / "data/intel/event_calls.jsonl"
    led.parent.mkdir(parents=True)
    led.write_text("".join(json.dumps({
        "note_id": f"e:{s}", "note_date": "2026-09-17",
        "predictions": [{"horizon": "5 trading days", "resolver": {}}],
        "event_call": {"document_ref": s, "symbol": s, "direction": "bullish",
                       "materiality": .8, "event_type": "earnings_result"}}) + "\n" for s in syms))
    b = EventShadowBook(root=str(tmp_path))
    got = fetch_closes(_client(DAY), b.pending_symbols("2026-09-18"), lookback_days=10)
    b.record("2026-09-18", closes=last_prices(got))
    assert {p["symbol"] for p in b._state()["open"]} == {"AAPL", "MSFT", "JPM", "BRK-B"}
    assert set(got.dropped) == {"^GSPC", "QQQQQQQ"}


def test_4_a_rejected_batch_is_split_to_the_bad_name_within_a_call_limit():
    from paper_trader.report_prices import MAX_CALLS, fetch_closes

    class _C:
        n = 0

        def fetch_daily_closes(self, t, lookback_days=0):
            _C.n += 1
            if "DEAD" in t:
                raise RuntimeError("400")
            return {x: pd.Series([1.0], index=[pd.Timestamp("2026-09-16")]) for x in t}

    names = [f"T{chr(65 + i // 26)}{chr(65 + i % 26)}" for i in range(60)] + ["DEAD"]
    got = fetch_closes(_C(), names, lookback_days=10)
    assert len(got.closes) == 60 and set(got.dropped) == {"DEAD"} and got.calls <= MAX_CALLS

    class _Down:
        n = 0

        def fetch_daily_closes(self, t, lookback_days=0):
            _Down.n += 1
            raise RuntimeError("down")
    got = fetch_closes(_Down(), names, lookback_days=10)
    assert not got.closes and _Down.n == MAX_CALLS and len(got.dropped) == 61


def test_5_one_prediction_that_cannot_be_resolved_does_not_cost_the_others(tmp_path):
    """A spin-off with no price on the start date raised TypeError out of the whole eval:
    no log, no summary, every day."""
    from intelligence.analyst import eval_harness as eh
    idx = pd.bdate_range("2026-06-01", "2026-09-17")
    up = pd.Series(range(100, 100 + len(idx)), index=idx, dtype=float)
    newco = up[up.index >= "2026-09-08"]
    note = {"note_id": "n", "note_date": "2026-09-01", "predictions": [
        {"statement": s, "probability": .6, "resolver": r} for s, r in (
            ("good", {"type": "relative_return", "symbol_a": "ACME", "symbol_b": "SPY",
                      "op": "gt", "start_date": "2026-09-01", "end_date": "2026-09-10"}),
            ("spinoff", {"type": "relative_return", "symbol_a": "NEWCO", "symbol_b": "SPY",
                         "op": "gt", "start_date": "2026-09-01", "end_date": "2026-09-10"}),
            ("no window", {"type": "price_above", "symbol": "NEWCO", "level": 1.0,
                           "direction": "above", "by_date": "2026-09-04", "mode": "touch"}),
            ("zero level", {"type": "price_above", "symbol": "SPY", "level": 0.0,
                            "direction": "above", "by_date": "2026-09-10", "mode": "terminal"}))]
        + [{"statement": "no resolver", "probability": .5}, "not an object"]}

    def px(sym: str) -> Any:
        if sym == "BOOM":
            raise ValueError("x")
        return {"SPY": up, "ACME": up, "NEWCO": newco}.get(sym)
    note["predictions"].append({"statement": "raises", "probability": .5, "resolver": {
        "type": "price_above", "symbol": "BOOM", "level": 1.0, "direction": "above",
        "by_date": "2026-09-10", "mode": "terminal"}})
    summ = eh.run("2026-09-18", notes=[note], price_fn=px, root=tmp_path)
    got = {r["statement"]: r for r in eh._load_log(tmp_path / eh.PRED_LOG_REL)}
    assert got["good"]["resolvable"] and got["zero level"]["outcome"] == 1
    assert got["zero level"]["baseline_persistence"] is None
    assert got["spinoff"]["resolve_detail"] == "insufficient_window_data"
    assert got["no window"]["resolve_detail"] == "insufficient_window_data"   # not "never touched"
    assert got["raises"]["resolve_detail"] == "error:ValueError"
    assert got["no resolver"]["resolve_detail"].startswith("invalid_resolver")
    assert summ["n_resolvable"] == 2 and (tmp_path / eh.SUMMARY_REL).exists()


def _run_fwd(tmp_path: Path, rows: list[dict], *, model: Any = None, body: Any = None,
             as_of: str = "2026-09-17", **kw: Any) -> dict:
    from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig
    from intelligence.event_call import run_forward as rf
    p = tmp_path / "panel.parquet"
    pd.DataFrame(rows).to_parquet(p, index=False)
    gov = kw.pop("governor", None) or CostGovernor(GovernorConfig(), str(tmp_path / "s.jsonl"))
    return rf.pulse_step(as_of, model_call=model or h._fake_model, governor=gov,
                         prompt_path=str(CHECKOUT / "config/prompts/event_interpreter/v1.txt"),
                         model_id_requested="m", prompt_version="event_interpreter/v1",
                         projected_cost_usd=0.1, raw_dir=str(tmp_path / "raw"),
                         ledger_path=tmp_path / "l.jsonl",
                         today=dt.date.fromisoformat(as_of), panel_path=p,
                         body_fetch=body or (lambda *a, **k: h._BODY), **kw)


def _doc(i: int, d: str, items: str = "2.02") -> dict:
    return {"ticker": "ACME", "cik": i + 1, "accession": f"acc{i}", "filing_date": d,
            "items": items, "primary_document": "d"}


def test_5_one_bad_document_or_reply_does_not_cost_the_batch(tmp_path):
    n = [0]

    def model(p: str, b: str, m: int) -> dict:
        n[0] += 1
        return {**h._fake_model(p, b, m), **({"text": "[]"} if n[0] == 1 else {})}

    def body(cik: Any, acc: str, **k: Any) -> str:
        if acc == "acc1":
            raise ValueError("bad cik")
        return h._BODY
    r = _run_fwd(tmp_path, [_doc(i, "2026-09-16") for i in range(4)], model=model, body=body)
    assert (r["status"], r["n_documents"], r["n_ok"], r["n_invalid"]) == ("ok", 4, 2, 2)
    raw = list((tmp_path / "raw").iterdir())                 # one file a month, not one a call
    assert [f.name for f in raw] == ["raw_event_calls_2026-09.jsonl"]
    assert len(raw[0].read_text().splitlines()) == 3


def test_minor_the_window_reaches_back_to_the_last_session_across_a_holiday(tmp_path):
    """Three calendar days dropped Friday's filings on the Tuesday after a Monday holiday and
    Thursday's on the Monday after Christmas (2026-12-24 would have been the first)."""
    for as_of, filed, prev in (("2026-01-20", "2026-01-16", "2026-01-16"),
                               ("2026-12-28", "2026-12-24", "2026-12-24")):
        t = tmp_path / as_of
        t.mkdir()
        assert _run_fwd(t, [_doc(0, filed)], as_of=as_of)["n_documents"] == 0
        assert _run_fwd(t, [_doc(0, filed)], as_of=as_of, prev_session=prev)["n_documents"] == 1
    from intelligence.event_call.run_forward import _date_floor
    d = dt.date(2026, 9, 17)
    assert _date_floor(d, 3, "2026-05-22") == "2026-09-14"   # a dead series never widens it
    assert _date_floor(d, 3, "2026-09-16") == _date_floor(d, 3, "junk") == "2026-09-14"


def test_minor_refused_calls_are_not_counted_and_the_rest_are_deferred(tmp_path):
    from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig
    gov = CostGovernor(GovernorConfig(monthly_budget_usd=0.0), str(tmp_path / "z.jsonl"))
    r = _run_fwd(tmp_path, [_doc(i, "2026-09-16") for i in range(5)], governor=gov)
    assert (r["n_called"], r["n_skipped"], r["n_deferred"]) == (0, 1, 4)


def test_minor_a_bad_date_or_a_duplicate_row_costs_only_itself(tmp_path):
    rows = [_doc(0, "2026-09-16", "2.02, 7.01"), _doc(0, "2026-09-16"), _doc(1, "not a date")]
    r = _run_fwd(tmp_path, rows)
    assert (r["status"], r["n_documents"], r["n_called"]) == ("ok", 2, 2)
    assert r["feed"]["n_bad_dates"] == 1
    from paper_trader.source_register import event_interpreter_problems
    assert "unparseable filing date" in " ".join(event_interpreter_problems(r))


def test_minor_a_kill_condition_with_no_prices_is_unresolvable_not_pending():
    from intelligence.analyst import eval_harness as eh
    for res in ({"type": "price_above", "symbol": "ZZZ", "level": 1.0, "direction": "above",
                 "by_date": "2026-12-15", "mode": "touch"},
                {"type": "dd_exceeds", "symbol": "ZZZ", "threshold_pct": 10,
                 "start_date": "2026-08-01", "end_date": "2026-12-01"}):
        st, why = eh.resolve_falsifier({"kind": "resolver", "resolver": res}, "2026-08-01",
                                       "2026-09-18", price_fn=lambda s: None)
        assert st == "unresolvable" and "ZZZ" in why
    assert eh.resolve_falsifier("x", "2026-08-01", "2026-09-18")[0] == "unresolvable"  # type: ignore[arg-type]


def test_a_checked_and_passed_falsifier_survives_a_later_day_without_data(tmp_path):
    from paper_trader.thesis_book import ThesisBook
    p = tmp_path / "data/state/thesis_book_machine.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"_schema": "thesis_book/v1", "open": [h._open_pos("t", "SPY", [
        {"kind": "resolver", "check_by": "2026-09-16", "statement": "s",
         "resolver": h._falsifier_resolver("below")}])], "closed": [], "days": [], "pending": []}))
    b = ThesisBook(root=str(tmp_path))
    px = {"SPY": 600.0}
    b.record("2026-09-17", closes=px, falsifier_status={"t": [
        {"index": 0, "status": "not_fired", "detail": "close_asof=600"}]})
    b.record("2026-09-18", closes=px, falsifier_status={"t": [
        {"index": 0, "status": "unresolvable", "detail": "no price series for SPY"}]})
    assert [x["thesis_id"] for x in b._state()["open"]] == ["t"]
    assert b._state()["days"][-1]["falsifiers"]["t"][0]["status"] == "not_fired"


# --------------------------------------------------------------------------- #
# The SEC transport; the cohort boundary
# --------------------------------------------------------------------------- #
def test_minor_the_contact_user_agent_never_follows_a_redirect_off_sec_gov():
    import urllib.request
    from core.sec_http import SecHttpError, _StayOnSec, fetch
    req = urllib.request.Request("https://www.sec.gov/x", headers={"User-Agent": "contact"})
    redir = lambda to: _StayOnSec().redirect_request(req, None, 302, "Found", {}, to)
    for to in ("https://other.example/x", "https://sec.gov.evil.example/x",
               "http://www.sec.gov/x"):
        with pytest.raises(SecHttpError):
            redir(to)
    assert redir("https://data.sec.gov/y").full_url == "https://data.sec.gov/y"
    with pytest.raises(SecHttpError):
        fetch("https://other.example/x", {"User-Agent": "contact"}, timeout=1)


def test_7_a_trickling_server_cannot_hold_a_sec_request_past_its_deadline():
    from core.sec_http import SecHttpError, _read_all
    now = [0.0]

    class _Drip:
        def read1(self, n: int) -> bytes:
            now[0] += 0.5
            return b"x"
    with pytest.raises(SecHttpError):
        _read_all(_Drip(), 2.0, lambda: now[0])
    assert now[0] <= 3.0


def test_minor_every_sec_caller_uses_the_bounded_transport(monkeypatch):
    import core.sec_http as sh
    import intelligence.event_call.eightk_body as eb
    import scripts.archive_altdata_t136 as ad
    import scripts.archive_positioning_t136 as ap
    seen: list[str] = []
    monkeypatch.setattr(sh, "fetch", lambda url, headers, *, timeout: seen.append(url) or b"ok")
    monkeypatch.setattr(eb, "fetch", sh.fetch)
    monkeypatch.setattr(eb, "RATE_SLEEP", 0.0)
    assert ad._get("https://www.sec.gov/a") == ap._get_bytes("https://www.sec.gov/b") == b"ok"
    assert eb._get("https://www.sec.gov/c") == "ok"
    assert [u[-1] for u in seen] == ["a", "b", "c"]


def test_9_the_agentic_arms_new_information_set_is_a_declared_cohort():
    """rate_path and events go from empty to live with no prompt change — the T-350 class.
    An earlier STAMPED boundary used to silence every later announced one."""
    from intelligence.analyst import information_cohorts as ic
    reg = json.loads((CHECKOUT / "config/information_cohorts.json").read_text())["sources"]
    c = {x["label"]: x for x in reg["analyst_agentic"]["cohorts"]}["rates_and_events_fed"]
    start = c["from_date"] or c["pending_from"]
    assert ic.cohort_for("analyst_agentic", "2026-11-24", reg) == "price_fed"
    got = ic.cohort_for("analyst_agentic", start, reg)
    assert got == ("rates_and_events_fed" if c["from_date"] else "rates_and_events_fed_UNSTAMPED")
    stamped = json.loads(json.dumps(reg))
    for x in stamped["analyst_agentic"]["cohorts"]:
        if x["label"] == "rates_and_events_fed":
            x["from_date"] = "2026-11-30"
    assert ic.cohort_for("analyst_agentic", "2026-11-30", stamped) == "rates_and_events_fed"
    assert ic.cohort_for("analyst_agentic", "2026-11-27", stamped) == "price_fed"
    assert ic.cohort_for("analyst_agentic", "2026-08-15", stamped) == "price_blind"
    assert ic.cohort_caveat("analyst_agentic", got, reg)
