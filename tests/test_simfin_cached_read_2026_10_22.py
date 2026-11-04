"""simfin_adapter: a CACHED read never rebuilds and never downloads (the 2026-10-22 incident).

What happened: `sf.load_*` re-downloads a raw dataset older than `refresh_days` (default 30),
so a panel build through a worktree's data/raw symlink replaced the six pinned raw files; and
`build_and_cache` rebuilt the panel whenever the raw CSVs were NEWER than it, so the next
load_panel() in any tree pointing at main's data rewrote the pinned panel.

Each case redirects the adapter's two module paths (SIMFIN_RAW_DIR, PROCESSED_PATH) into
tmp_path, plants a panel with raw CSVs NEWER than it, and puts a sentinel on the library's
download seam (`simfin.download._download`) and on the three loaders: a network call or a
library load during a cached read raises, so a pass means neither happened. The positive
control proves the sentinel sits on the real path.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import pytest

import simfin.download as sf_download
from engines.data_manager.data_manager import REFUSE_YFINANCE_ENV
from engines.data_manager.fundamentals import simfin_adapter as sa


class NetworkTouched(AssertionError):
    """The sentinel: raised by anything that would reach SimFin or load through the library."""


SWITCHES = ("ARCHONDEX_MEASURED", "ARCHONDEX_HERMETIC", REFUSE_YFINANCE_ENV, "SIMFIN_API_KEY")


def test_the_adapter_spells_the_canonical_switch_by_the_data_managers_name():
    """The adapter names the switch locally (so it does not reach the data manager in the import
    graph — tests/test_env_entries_2026_10_15.py's reachability lock); the name must stay equal."""
    assert sa.CANONICAL_SWITCH_ENV == REFUSE_YFINANCE_ENV


@pytest.fixture
def switches_off(monkeypatch):
    for name in SWITCHES:
        monkeypatch.delenv(name, raising=False)


def _plant_panel(path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"Ticker": ["AAPL"], "publish_date": [pd.Timestamp("2024-01-01")],
                  "net_income": [1.0]}).to_parquet(path)
    old = time.time() - 3600
    os.utime(path, (old, old))                      # an hour older than the raw files below
    return path.read_bytes()


def _plant_raw(raw_dir: Path) -> dict[str, bytes]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for n in sa.RAW_DATASETS:
        (raw_dir / n).write_text(f"Ticker;SimFinId\nAAPL;1\n# {n}\n")
        out[n] = (raw_dir / n).read_bytes()
    return out


@pytest.fixture
def layout(tmp_path, monkeypatch, switches_off):
    """A panel and three raw CSVs NEWER than it, both under tmp_path; the adapter pointed at them."""
    raw = tmp_path / "data" / "raw" / "simfin"
    processed = tmp_path / "data" / "processed" / "fundamentals_simfin.parquet"
    panel_bytes = _plant_panel(processed)
    raw_bytes = _plant_raw(raw)
    monkeypatch.setattr(sa, "SIMFIN_RAW_DIR", raw)
    monkeypatch.setattr(sa, "PROCESSED_PATH", processed)
    return {"root": tmp_path, "raw": raw, "processed": processed,
            "panel_bytes": panel_bytes, "raw_bytes": raw_bytes}


@pytest.fixture
def no_network(monkeypatch):
    def boom(*a, **k):
        raise NetworkTouched(f"the library's download/load path was reached: {a[:1]} {sorted(k)}")
    monkeypatch.setattr(sf_download, "_download", boom)
    for name in ("load_income", "load_balance", "load_cashflow"):
        monkeypatch.setattr(sa.sf, name, boom)


def _unchanged(layout) -> None:
    assert layout["processed"].read_bytes() == layout["panel_bytes"], "the panel was rewritten"
    for n, b in layout["raw_bytes"].items():
        assert (layout["raw"] / n).read_bytes() == b, f"{n} was refreshed"


# --------------------------------------------------------------------------------------------
# THE LOCK: raw files newer than the panel -> the read serves the panel byte-for-byte, no network
# --------------------------------------------------------------------------------------------

def test_cached_read_serves_the_panel_unchanged_when_raw_files_are_newer(layout, no_network, capsys):
    assert all(v == "newer_than_panel" for v in sa.raw_staleness().values())
    df = sa.load_panel()
    assert list(df["Ticker"]) == ["AAPL"]
    _unchanged(layout)
    out = capsys.readouterr().out
    assert "newer_than_panel" in out and "NOT a trigger" in out, "staleness is RECORDED, not acted on"


def test_build_and_cache_without_force_is_the_cached_read(layout, no_network):
    assert sa.build_and_cache() == layout["processed"]
    _unchanged(layout)


def test_a_cached_read_with_a_key_set_still_never_rebuilds(layout, no_network, monkeypatch):
    """The old condition rebuilt when raw was newer AND a key was present; the key no longer matters."""
    monkeypatch.setenv("SIMFIN_API_KEY", "not-a-real-key")
    sa.load_panel()
    _unchanged(layout)


def test_a_missing_panel_is_refused_not_built_and_no_directory_is_created(tmp_path, monkeypatch,
                                                                           switches_off, no_network):
    raw = tmp_path / "data" / "raw" / "simfin"
    _plant_raw(raw)
    processed = tmp_path / "data" / "processed" / "fundamentals_simfin.parquet"
    monkeypatch.setattr(sa, "SIMFIN_RAW_DIR", raw)
    monkeypatch.setattr(sa, "PROCESSED_PATH", processed)
    with pytest.raises(sa.FundamentalsPanelMissing):
        sa.load_panel()
    assert not processed.parent.exists(), "a cached read must not mkdir the processed dir"


def test_get_panel_abstains_on_a_missing_panel_outside_measured_mode(tmp_path, monkeypatch,
                                                                       switches_off, no_network):
    from engines.engine_a_alpha.edges import _fundamentals_helpers as fh
    processed = tmp_path / "data" / "processed" / "fundamentals_simfin.parquet"
    monkeypatch.setattr(sa, "SIMFIN_RAW_DIR", tmp_path / "data" / "raw" / "simfin")
    monkeypatch.setattr(sa, "PROCESSED_PATH", processed)
    fh.reset_panel_cache()
    try:
        assert fh.get_panel() is None
    finally:
        fh.reset_panel_cache()
    assert not (tmp_path / "data").exists()


def test_a_cached_raw_read_with_a_dataset_absent_is_refused_not_downloaded(layout, no_network):
    (layout["raw"] / sa.RAW_DATASETS[0]).unlink()
    with pytest.raises(sa.FundamentalsRebuildRefused, match="never downloads"):
        sa.load_raw_panels()


# --------------------------------------------------------------------------------------------
# The declared rebuild: refused under every switch; otherwise reads raw with a refresh that
# cannot fire, and only `download=True` (with the key) lets the library download (refresh 0)
# --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,value", [
    ("ARCHONDEX_MEASURED", "1"),
    ("ARCHONDEX_HERMETIC", "strict"),
    ("ARCHONDEX_HERMETIC", "warn"),
    (REFUSE_YFINANCE_ENV, "1"),
])
def test_rebuild_is_refused_under_each_switch_before_anything_is_touched(layout, no_network,
                                                                          monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(sa.FundamentalsRebuildRefused, match="refused"):
        sa.rebuild_panel()
    with pytest.raises(sa.FundamentalsRebuildRefused):
        sa.load_panel(force_rebuild=True)
    with pytest.raises(sa.FundamentalsRebuildRefused):
        sa.build_and_cache(force=True)
    _unchanged(layout)


def _recording_loaders(monkeypatch):
    calls: list[tuple[str, dict]] = []
    frame = pd.DataFrame({"x": [1.0]})

    def make(name):
        def f(*a, **k):
            calls.append((name, dict(k)))
            return frame
        return f
    for name in ("load_income", "load_balance", "load_cashflow"):
        monkeypatch.setattr(sa.sf, name, make(name))
    monkeypatch.setattr(sa.sf, "set_data_dir", lambda *a, **k: None)
    monkeypatch.setattr(sa.sf, "set_api_key", lambda *a, **k: None)
    monkeypatch.setattr(sa, "build_panel", lambda inc, bal, cf: frame)
    monkeypatch.setattr(sa, "compute_factors", lambda p: pd.DataFrame({"rebuilt": [1]}))
    return calls


def test_declared_rebuild_reads_raw_with_a_refresh_that_cannot_fire(layout, monkeypatch, capsys):
    calls = _recording_loaders(monkeypatch)
    monkeypatch.setattr(sf_download, "_download",
                        lambda *a, **k: (_ for _ in ()).throw(NetworkTouched("download")))
    out_path = sa.rebuild_panel(download=False)
    assert out_path == layout["processed"]
    assert [c[0] for c in calls] == ["load_income", "load_balance", "load_cashflow"]
    assert all(c[1]["refresh_days"] == sa._NEVER_REFRESH_DAYS for c in calls)
    assert "rebuilt" in pd.read_parquet(out_path).columns, "the declared rebuild DID write"
    assert sa.REBAKE_WARN.split(" — ")[0] in capsys.readouterr().out


def test_declared_download_needs_the_key_and_passes_refresh_zero(layout, monkeypatch):
    calls = _recording_loaders(monkeypatch)
    with pytest.raises(sa.FundamentalsRebuildRefused, match="SIMFIN_API_KEY"):
        sa.rebuild_panel(download=True)
    assert calls == [], "nothing loaded without the key"
    monkeypatch.setenv("SIMFIN_API_KEY", "not-a-real-key")
    sa.rebuild_panel(download=True)
    assert all(c[1]["refresh_days"] == 0 for c in calls)


# --------------------------------------------------------------------------------------------
# Positive control: the sentinel sits on the library's real download path
# --------------------------------------------------------------------------------------------

def test_the_network_sentinel_is_on_the_library_download_path(tmp_path, monkeypatch, switches_off):
    raw = tmp_path / "data" / "raw" / "simfin"       # no datasets on disk
    monkeypatch.setattr(sa, "SIMFIN_RAW_DIR", raw)
    monkeypatch.setattr(sa, "PROCESSED_PATH", tmp_path / "data" / "processed" / "p.parquet")
    monkeypatch.setenv("SIMFIN_API_KEY", "not-a-real-key")

    def boom(*a, **k):
        raise NetworkTouched("download")
    monkeypatch.setattr(sf_download, "_download", boom)
    with pytest.raises(NetworkTouched):
        sa.load_raw_panels(allow_download=True)      # the declared refresh reaches the seam
