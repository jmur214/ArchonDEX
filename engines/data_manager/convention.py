"""The UNIVERSAL convention label (option (a), the user's cutover ruling, 2026-10-22).

The processed cache is total return in two forms: EXACT ex-date total return where the provider's
series was written (the post-seam span of every `both` file; the whole of an `alpaca_only` file),
and the T-082b DRIP — Stooq bars scaled by a fitted exp(a + b·t), a constant-yield APPROXIMATION
that smears every ex-date step into a drift — before the seam. Option (a) keeps the drip and
LABELS it everywhere: every name in a run's panel carries, in the census, what each span of its
file IS. The label is never a default: it comes from the file's pinned write record (`convention`,
written by `tr_writer.full_refetch`), else from a declared whole-file override
(`config/convention_declarations.json`, for a file regenerated whole after the merge whose merge
record is stale — SPY), else from the merge record (`_merge_meta.json`) under the cache, witnessed
against the run's own frame where one is given (a frame that starts before the record's first bar
proves the record stale). A name with none of the three is UNLABELLED, by name and with the reason,
and the census gate FAILS the run on it. A cache with no merge record labels nothing from it, and
says so (`merge_meta_present: False`) — the gate reads that as every record-labelled name missing.

ONE function, called by BOTH census producers (`backtester/backtest_controller.py:_build_census`
and `engines/engine_d_discovery/discovery.py:candidate_census_block`), under the two-producer lock
in `tests/test_contracts.py` (`CENSUS_PROVENANCE_KEYS`).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd

from engines.data_manager.tr_writer import (DRIP, EXACT_TR, MERGE_META_NAME, WRITE_RECORDS_DIR,
                                            load_convention_declarations, load_merge_meta)

RULE = ("pre-seam = drip (T-082b's constant-yield approximation of the Stooq years); post-seam = "
        "exact_tr (the provider's ex-date total return); a file with no seam is one convention over "
        "its whole span. A name's label comes from its pinned write record, else a declared whole-file "
        "override, else the merge record (witnessed against the run's frame); a name with none of the "
        "three is UNLABELLED by name — never defaulted — and the gate fails the run")
SEAM_SEP = "<"
SIDE_SEP = "|"


def label_of(convention: dict) -> str:
    """One string per name: `exact_tr` (whole), or `drip<2018-01-02|exact_tr` (pre-seam, seam date,
    post-seam) — the form the census carries for every name in the panel."""
    if "whole" in convention:
        return str(convention["whole"])
    return f"{convention['pre_seam']}{SEAM_SEP}{convention['seam_date']}{SIDE_SEP}{convention['post_seam']}"


def _first_bar(df) -> Optional[pd.Timestamp]:
    if df is None or not len(df):
        return None
    idx = pd.DatetimeIndex(pd.to_datetime(df.index))
    idx = idx.tz_localize(None) if idx.tz is not None else idx
    return pd.Timestamp(idx.min())


def substrate_convention_record(cache_dir: Path, run_names: Optional[Iterable[str]] = None,
                                data_map: Optional[Dict[str, pd.DataFrame]] = None,
                                conventions: Optional[Dict[str, dict]] = None) -> dict:
    """The `substrate_convention` census block over `run_names` (the panel; every name in the merge
    record when None). Per name: its label (`per_name`), or why it has none (`unlabelled`). The
    block names the directory it READ (`cache_dir`) and whether the merge record and the write
    records were there, so it never describes a substrate it did not read."""
    cache_dir = Path(cache_dir)
    meta = load_merge_meta(cache_dir)
    conventions = load_convention_declarations() if conventions is None else conventions
    overrides = conventions["whole_file_overrides"]
    records_dir = cache_dir / WRITE_RECORDS_DIR
    if run_names is None and meta is None:
        raise FileNotFoundError(f"{cache_dir / MERGE_META_NAME}: no merge record and no run names — "
                                f"nothing to label")
    names = sorted(set(run_names)) if run_names is not None else sorted(meta)
    per_name: Dict[str, str] = {}
    unlabelled: Dict[str, str] = {}
    sources: Counter = Counter()
    for t in names:
        rec_path = records_dir / f"{t}.json"
        if rec_path.exists():
            rec = json.loads(rec_path.read_text())
            conv = rec.get("convention")
            if conv:
                per_name[t] = label_of(conv)
                sources["write_record"] += 1
                continue
            unlabelled[t] = ("a pinned write record with no convention block — written before the "
                             "option (a) writer (2026-10-22); the file's spans are unrecorded")
            continue
        if t in overrides:
            per_name[t] = str(overrides[t]["convention"])
            sources["declared_override"] += 1
            continue
        if meta is None:
            unlabelled[t] = f"no write record, no override, and the cache has no {MERGE_META_NAME}"
            continue
        entry = meta.get(t)
        if entry is None:
            unlabelled[t] = "no write record, no override, no merge record for the name"
            continue
        first = _first_bar(data_map.get(t)) if data_map is not None else None
        if first is not None and entry.get("first_bar_date") and first < pd.Timestamp(entry["first_bar_date"]):
            unlabelled[t] = (f"the merge record is STALE: the frame starts {first.date()}, before the "
                             f"record's first bar {entry['first_bar_date']} — the file was rewritten "
                             f"after the merge without a record or an override")
            continue
        if (entry.get("merge_case") == "both" and int(entry.get("n_stooq_pre_seam") or 0) > 0
                and entry.get("seam_date")):
            per_name[t] = label_of({"pre_seam": DRIP, "seam_date": entry["seam_date"], "post_seam": EXACT_TR})
        else:
            per_name[t] = EXACT_TR          # alpaca_only, or `both` with no pre-seam bars (AMCR)
        sources["merge_meta"] += 1
    labels = Counter(per_name.values())
    seams = Counter(v.split(SEAM_SEP, 1)[1].split(SIDE_SEP, 1)[0] for v in per_name.values() if SEAM_SEP in v)
    return {"cache_dir": str(cache_dir), "merge_meta_present": meta is not None,
            "records_dir_present": records_dir.is_dir(), "rule": RULE,
            "n_names": len(names), "n_labelled": len(per_name),
            "n_pre_seam_drip": int(sum(v for k, v in labels.items() if k.startswith(DRIP + SEAM_SEP))),
            "labels": dict(labels), "seams": dict(seams), "sources": dict(sources),
            "per_name": per_name, "unlabelled": unlabelled}
