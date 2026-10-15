"""A reader NEVER deletes (ruling, 2026-10-15; rides in the convention-guard unit).

`DataManager.load_cached` used to `unlink()` a cache file it could not parse — a reader silently
destroying substrate. Now an unreadable file is QUARANTINED (renamed to a sibling
`.unreadable-<UTC ts>`) and refused with CacheUnreadableError naming the path, the error and where
the bytes went. These locks plant corrupt files and assert the bytes survive the load.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engines.data_manager import data_manager as dmod

GARBAGE = b"\x00\x01this is not a parquet or a csv\xff" * 8


@pytest.fixture
def dm(tmp_path):
    return dmod.DataManager(cache_dir=str(tmp_path / "cache"))


def _quarantined(path):
    return sorted(path.parent.glob(path.name + ".unreadable-*"))


def test_a_corrupt_parquet_is_quarantined_and_refused_never_deleted(dm):
    pq = dm.parquet_cache_path("BADP", "1d")
    pq.write_bytes(GARBAGE)
    with pytest.raises(dmod.CacheUnreadableError) as ei:
        dm.load_cached("BADP", "1d")
    q = _quarantined(pq)
    assert len(q) == 1 and q[0].read_bytes() == GARBAGE, "the bytes must survive, byte-identical"
    assert not pq.exists(), "quarantine moves it out of the cache's name"
    assert str(pq) in str(ei.value) and str(q[0]) in str(ei.value), "path and destination named"


def test_a_corrupt_csv_is_quarantined_and_refused_never_deleted(dm):
    csv = dm.cache_path("BADC", "1d")
    csv.write_bytes(b'"unterminated,quote\n' + GARBAGE)
    with pytest.raises(dmod.CacheUnreadableError):
        dm.load_cached("BADC", "1d")
    q = _quarantined(csv)
    assert len(q) == 1 and q[0].read_bytes().endswith(GARBAGE)


def test_a_normalization_bug_does_NOT_quarantine_a_good_file(dm, monkeypatch):
    """Only the READ is guarded: a code bug must surface as itself and leave the file alone."""
    idx = pd.bdate_range("2024-01-02", periods=20)
    good = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": np.arange(20.0) + 1,
                         "Volume": 1.0}, index=idx)
    dm.save_cache("GOOD", "1d", good)
    pq = dm.parquet_cache_path("GOOD", "1d")
    before = pq.read_bytes()

    def boom(*a, **k):
        raise ValueError("normalize bug")
    monkeypatch.setattr(dmod.DataManager, "_normalize_df", staticmethod(boom))
    with pytest.raises(ValueError, match="normalize bug"):
        dm.load_cached("GOOD", "1d")
    assert pq.read_bytes() == before and not _quarantined(pq)


def test_a_missing_file_is_still_a_plain_cache_miss(dm):
    assert dm.load_cached("NOPE", "1d") is None
