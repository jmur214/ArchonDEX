"""tests/test_submit_arms_campaign_windows.py
==============================================
T-2026-05-24-053b: regression tests for the multi-year-window spec
extension in `scripts/submit_arms_campaign.py`.

Coverage:
1. Legacy `years` spec → cells get YYYY-01-01 / YYYY-12-31 windows
   AND `year_int_for_legacy` returns the integer year.
2. New `windows` spec → cells carry the exact start/end + the label
   computed from those dates (single year, multi-year, sub-year).
3. Per-window label override via `label` field on the window dict.
4. Spec validation: rejects both `years` AND `windows` set; rejects
   neither set; rejects malformed window entries.
5. Cell ID path includes the window_label segment (NOT the integer
   year), so legacy `years` campaigns produce the same S3 path as
   pre-T-053b.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.submit_arms_campaign import (
    Cell,
    _window_label,
    build_cells,
    load_spec,
)


def _spec_to_disk(spec: dict) -> Path:
    p = Path(tempfile.mktemp(suffix=".json"))
    p.write_text(json.dumps(spec))
    return p


# ---------------------- _window_label pure function ---------------------- #

def test_window_label_single_calendar_year_is_yyyy():
    assert _window_label("2024-01-01", "2024-12-31") == "2024"


def test_window_label_multi_year_is_yyyy_yyyy():
    assert _window_label("2014-01-01", "2025-12-31") == "2014-2025"


def test_window_label_sub_year_is_full_dates():
    assert _window_label("2024-03-15", "2024-09-30") == "2024-03-15_2024-09-30"


def test_window_label_override_wins():
    assert _window_label("2024-01-01", "2024-12-31", "mid14_25") == "mid14_25"


# ---------------------- Legacy `years` spec ---------------------- #

def test_legacy_years_spec_desugars_to_windows():
    spec_path = _spec_to_disk({
        "campaign_id": "test_legacy",
        "years": [2024, 2025],
        "reps": 2,
        "arms": {"arm0": {"config_patch": {}}},
    })
    cells = build_cells(load_spec(spec_path))
    assert len(cells) == 4  # 1 arm × 2 years × 2 reps
    assert cells[0].start_date == "2024-01-01"
    assert cells[0].end_date == "2024-12-31"
    assert cells[0].window_label == "2024"
    assert cells[0].rep == 1
    # year_int_for_legacy should return the integer year
    assert cells[0].year_int_for_legacy == 2024


def test_legacy_years_cell_id_path_unchanged():
    """S3 path for a year-based legacy spec keeps the YYYY segment so
    pre-T-053b campaign output paths remain backward-compatible."""
    spec_path = _spec_to_disk({
        "campaign_id": "legacy_pp",
        "years": [2024],
        "reps": 1,
        "arms": {"armX": {"config_patch": {}}},
    })
    cells = build_cells(load_spec(spec_path))
    assert cells[0].cell_id == "legacy_pp/armX/2024/rep1"


# ---------------------- New `windows` spec ---------------------- #

def test_windows_spec_12yr_single_window():
    spec_path = _spec_to_disk({
        "campaign_id": "t053b_proof",
        "windows": [{"start": "2014-01-01", "end": "2025-12-31"}],
        "reps": 5,
        "arms": {
            "arm0_off": {"config_patch": {}},
            "arm2_n3": {"config_patch": {
                "config/alpha_settings.json": {
                    "confidence_gate.enabled": True,
                    "confidence_gate.n_threshold": 3,
                }
            }},
        },
    })
    cells = build_cells(load_spec(spec_path))
    assert len(cells) == 10  # 2 arms × 1 window × 5 reps
    arm0_cells = [c for c in cells if c.arm == "arm0_off"]
    arm2_cells = [c for c in cells if c.arm == "arm2_n3"]
    assert len(arm0_cells) == 5
    assert len(arm2_cells) == 5
    sample = arm0_cells[0]
    assert sample.start_date == "2014-01-01"
    assert sample.end_date == "2025-12-31"
    assert sample.window_label == "2014-2025"
    # Multi-year window: year_int_for_legacy is None (don't set ARCHONDEX_YEAR)
    assert sample.year_int_for_legacy is None


def test_windows_spec_with_label_override():
    spec_path = _spec_to_disk({
        "campaign_id": "labeled",
        "windows": [{
            "start": "2014-06-01", "end": "2025-12-31",
            "label": "mid14_25",
        }],
        "reps": 1,
        "arms": {"armX": {"config_patch": {}}},
    })
    cells = build_cells(load_spec(spec_path))
    assert cells[0].window_label == "mid14_25"
    assert cells[0].cell_id == "labeled/armX/mid14_25/rep1"


def test_windows_spec_multiple_windows():
    spec_path = _spec_to_disk({
        "campaign_id": "rolling",
        "windows": [
            {"start": "2014-01-01", "end": "2018-12-31"},
            {"start": "2019-01-01", "end": "2024-12-31"},
        ],
        "reps": 1,
        "arms": {"armX": {"config_patch": {}}},
    })
    cells = build_cells(load_spec(spec_path))
    assert len(cells) == 2
    assert {c.window_label for c in cells} == {"2014-2018", "2019-2024"}


# ---------------------- Spec validation ---------------------- #

def test_spec_rejects_both_years_and_windows():
    spec_path = _spec_to_disk({
        "campaign_id": "bad",
        "years": [2024],
        "windows": [{"start": "2024-01-01", "end": "2024-12-31"}],
        "reps": 1, "arms": {"a": {"config_patch": {}}},
    })
    with pytest.raises(SystemExit, match="not both"):
        load_spec(spec_path)


def test_spec_rejects_neither_years_nor_windows():
    spec_path = _spec_to_disk({
        "campaign_id": "bad",
        "reps": 1, "arms": {"a": {"config_patch": {}}},
    })
    with pytest.raises(SystemExit, match="either"):
        load_spec(spec_path)


def test_spec_rejects_malformed_window():
    spec_path = _spec_to_disk({
        "campaign_id": "bad",
        "windows": [{"start": "2024-01-01"}],  # missing 'end'
        "reps": 1, "arms": {"a": {"config_patch": {}}},
    })
    with pytest.raises(SystemExit, match="start, end"):
        load_spec(spec_path)


def test_spec_rejects_empty_windows_list():
    spec_path = _spec_to_disk({
        "campaign_id": "bad",
        "windows": [],
        "reps": 1, "arms": {"a": {"config_patch": {}}},
    })
    with pytest.raises(SystemExit, match="non-empty"):
        load_spec(spec_path)


def test_spec_rejects_missing_arms():
    spec_path = _spec_to_disk({
        "campaign_id": "bad",
        "windows": [{"start": "2024-01-01", "end": "2024-12-31"}],
        "reps": 1,
    })
    with pytest.raises(SystemExit, match="missing required"):
        load_spec(spec_path)


# ---------------------- year_int_for_legacy edge cases ---------------------- #

def test_year_int_for_legacy_returns_None_for_partial_year():
    c = Cell(
        campaign_id="x", arm="a",
        start_date="2024-06-01", end_date="2024-12-31",
        window_label="2024H2", rep=1, config_patch={},
    )
    assert c.year_int_for_legacy is None


def test_year_int_for_legacy_returns_None_for_multi_year():
    c = Cell(
        campaign_id="x", arm="a",
        start_date="2014-01-01", end_date="2025-12-31",
        window_label="2014-2025", rep=1, config_patch={},
    )
    assert c.year_int_for_legacy is None


def test_year_int_for_legacy_returns_year_for_calendar_year():
    c = Cell(
        campaign_id="x", arm="a",
        start_date="2024-01-01", end_date="2024-12-31",
        window_label="2024", rep=1, config_patch={},
    )
    assert c.year_int_for_legacy == 2024
