"""The fundamentals RE-BAKE (scripts/rebake_fundamentals.py; the director's ruling and R's design
review, 2026-10-15). Each lock drives the real CLI (`main`) on a planted cache with a fake provider:
  * a planted MISS is fetched, written and RECORDED: the source and the provider's version, the
    attributes ACTUALLY read (exactly the four), the time, the outcome, the rows and columns, the
    first and last dates, and the md5 of the written file;
  * under the canonical switch, and under hermetic, it refuses: non-zero, nothing written, the
    provider never constructed;
  * misses only, as the LOADER defines one: a non-empty cached file is untouched; an EMPTY cached
    file is `present_empty`, untouched, non-zero;
  * names are explicit (a list or a census's refused set); none → non-zero;
  * it is never reachable from a backtest, the dashboard or the cloud path (AST, with a positive
    control).
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from engines.data_manager import data_manager as dmmod
from scripts import rebake_fundamentals as rb
from tests.test_fundamentals_miss_refusal_2026_10_15 import _FakeTicker

REPO = Path(__file__).resolve().parent.parent
FOUR = ["quarterly_income_stmt", "quarterly_balance_sheet", "quarterly_cashflow", "history"]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv(dmmod.REFUSE_YFINANCE_ENV, raising=False)
    monkeypatch.setenv("ARCHONDEX_HERMETIC", "0")
    dmmod.reset_fundamentals_log()
    yield
    dmmod.reset_fundamentals_log()


def _cache(tmp_path) -> Path:
    c = Path(tmp_path) / "processed"
    (c / "parquet").mkdir(parents=True)
    return c


def _boom(*a, **k):
    raise AssertionError("the provider was constructed")


def _record(cache: Path, t: str) -> dict:
    return json.loads((cache / "parquet" / rb.RECORDS_DIRNAME / f"{t}.json").read_text())


def test_a_planted_MISS_is_fetched_written_and_RECORDED_with_every_field(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(dmmod.yf, "Ticker", _FakeTicker)
    cache = _cache(tmp_path)
    assert rb.main(["--tickers", "newt", "--cache-dir", str(cache)]) == 0
    f = cache / "parquet" / "NEWT_fundamentals.parquet"
    assert f.exists()
    r = _record(cache, "NEWT")
    assert r["outcome"] == "fetched" and r["source"] == "yfinance"
    assert r["provider_version"] == getattr(dmmod.yf, "__version__", "unknown") != "unknown"
    assert r["provider_attributes_read"] == FOUR, r["provider_attributes_read"]
    assert r["rows"] > 0 and r["columns"] and r["first_date"] and r["last_date"]
    assert r["first_date"] <= r["last_date"] and r["fetched_at"].endswith("+00:00")
    assert r["md5"] == hashlib.md5(f.read_bytes()).hexdigest()
    out = capsys.readouterr().out
    assert out.count(rb.WARN) >= 1 and "WRITTEN into the pinned scope" in out
    assert dmmod.yf.Ticker is _FakeTicker, "the recording proxy must be removed after the fetch"


def test_under_the_CANONICAL_SWITCH_it_refuses_writes_nothing_never_constructs_the_provider(tmp_path, monkeypatch):
    monkeypatch.setenv(dmmod.REFUSE_YFINANCE_ENV, "1")
    monkeypatch.setattr(dmmod.yf, "Ticker", _boom)
    cache = _cache(tmp_path)
    assert rb.main(["--tickers", "NEWT", "--cache-dir", str(cache)]) == 2
    assert list((cache / "parquet").rglob("*")) == []


def test_under_HERMETIC_it_refuses(tmp_path, monkeypatch):
    monkeypatch.setenv("ARCHONDEX_HERMETIC", "1")
    monkeypatch.setattr(dmmod.yf, "Ticker", _boom)
    cache = _cache(tmp_path)
    assert rb.main(["--tickers", "NEWT", "--cache-dir", str(cache)]) == 2
    assert list((cache / "parquet").rglob("*")) == []


def test_a_NON_EMPTY_cached_file_is_left_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(dmmod.yf, "Ticker", _boom)
    cache = _cache(tmp_path)
    f = cache / "parquet" / "HAVE_fundamentals.parquet"
    pd.DataFrame({"PE_Ratio": [10.0]}, index=pd.DatetimeIndex(["2024-01-02"])).to_parquet(f)
    before = hashlib.md5(f.read_bytes()).hexdigest()
    assert rb.main(["--tickers", "HAVE", "--cache-dir", str(cache)]) == 0
    assert hashlib.md5(f.read_bytes()).hexdigest() == before
    assert not (cache / "parquet" / rb.RECORDS_DIRNAME / "HAVE.json").exists()


def test_an_EMPTY_cached_file_is_PRESENT_EMPTY_untouched_and_non_zero(tmp_path, monkeypatch):
    """The loader treats an empty parquet as a miss (R's condition (a)): reporting it "present" would
    leave a name the next canonical run refuses again."""
    monkeypatch.setattr(dmmod.yf, "Ticker", _boom)
    cache = _cache(tmp_path)
    f = cache / "parquet" / "HOLL_fundamentals.parquet"
    pd.DataFrame({"PE_Ratio": []}).to_parquet(f)
    before = hashlib.md5(f.read_bytes()).hexdigest()
    recs = rb.rebake(["HOLL"], cache)
    assert recs[0]["outcome"] == "present_empty"
    assert hashlib.md5(f.read_bytes()).hexdigest() == before
    assert rb.main(["--tickers", "HOLL", "--cache-dir", str(cache)]) == 1


def test_names_from_a_CENSUS_refused_set(tmp_path, monkeypatch):
    monkeypatch.setattr(dmmod.yf, "Ticker", _FakeTicker)
    cache = _cache(tmp_path)
    summ = tmp_path / "performance_summary.json"
    summ.write_text(json.dumps({"census": {"fundamentals_misses": {
        "refused": ["NEWT"], "blocked": [], "fetched": [], "empty": [], "sources": {}}}}))
    assert rb.main(["--from-census", str(summ), "--cache-dir", str(cache)]) == 0
    assert _record(cache, "NEWT")["outcome"] == "fetched"


def test_NO_names_is_refused_and_there_is_no_sweep_option(tmp_path):
    assert rb.main(["--tickers", " , ", "--cache-dir", str(_cache(tmp_path))]) == 2
    # the EMPTY string is a given-but-empty name list: the same designed refusal, never a TypeError
    assert rb.main(["--tickers", "", "--cache-dir", str(_cache(tmp_path / "e"))]) == 2
    with pytest.raises(SystemExit):
        rb.main(["--cache-dir", str(_cache(tmp_path / "b"))])      # a name source is required


def test_an_EMPTY_provider_result_is_recorded_EMPTY_and_writes_no_parquet(tmp_path, monkeypatch):
    class _Nothing(_FakeTicker):
        def __init__(self, *a, **k):
            super().__init__()
            self.quarterly_income_stmt = pd.DataFrame()
    monkeypatch.setattr(dmmod.yf, "Ticker", _Nothing)
    cache = _cache(tmp_path)
    assert rb.main(["--tickers", "NADA", "--cache-dir", str(cache)]) == 1
    assert not (cache / "parquet" / "NADA_fundamentals.parquet").exists()
    r = _record(cache, "NADA")
    assert r["outcome"] == "empty" and r["md5"] is None
    # the fetch reads the three statement tables, then returns on an empty income statement BEFORE
    # history(): a WITNESS records three here, where a constant would claim four
    assert r["provider_attributes_read"] == FOUR[:3], r["provider_attributes_read"]


# ---------------------------------------------------------------- never reachable -----------------

UNREACHABLE_FROM = ("engines", "orchestration", "backtester", "core", "paper_trader", "live_trader",
                    "cockpit")


def _references(path: Path) -> list:
    """Imports of, or string references to, the re-bake script (a dashboard command is a string).
    FAIL-CLOSED: a file the scanner cannot parse is checked as TEXT — it is never silently clean
    (the lock's first reversion run found exactly that: a plant that broke a file's syntax passed)."""
    try:
        text = path.read_text()
    except UnicodeDecodeError:
        text = path.read_bytes().decode("utf-8", "replace")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [0] if "rebake_fundamentals" in text else []
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module and "rebake_fundamentals" in n.module:
            hits.append(n.lineno)
        elif isinstance(n, ast.Import) and any("rebake_fundamentals" in a.name for a in n.names):
            hits.append(n.lineno)
        elif isinstance(n, ast.ImportFrom) and any(a.name == "rebake_fundamentals" for a in n.names):
            hits.append(n.lineno)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and "rebake_fundamentals" in n.value:
            hits.append(n.lineno)
    return hits


def test_the_rebake_is_NEVER_reachable_from_a_backtest_the_dashboard_or_the_cloud_path():
    bad = [f"{p.relative_to(REPO)}:{ln}" for d in UNREACHABLE_FROM if (REPO / d).exists()
           for p in (REPO / d).rglob("*.py") if "Archive" not in p.parts for ln in _references(p)]
    assert not bad, f"the re-bake is reachable from: {bad}"
    for sh in ("scripts/cloud_entrypoint.sh", "Dockerfile.backtest"):
        p = REPO / sh
        if p.exists():
            assert "rebake_fundamentals" not in p.read_text(), sh


def test_POSITIVE_CONTROL_the_reference_scan_sees_an_import_and_a_command_string(tmp_path):
    a = tmp_path / "a.py"
    a.write_text("from scripts.rebake_fundamentals import rebake\n")
    b = tmp_path / "b.py"
    b.write_text('CMD = [sys.executable, "-m", "scripts.rebake_fundamentals"]\n')
    assert _references(a) and _references(b)
    broken = tmp_path / "broken.py"
    broken.write_text('from __future__ CMD = "scripts.rebake_fundamentals"\n')      # unparseable
    assert _references(broken), "an unparseable file must not read as clean"
