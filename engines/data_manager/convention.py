"""The UNIVERSAL convention label (option (a), the user's cutover ruling, 2026-10-22).

The processed cache is total return in two forms: EXACT ex-date total return where the provider's
series was written (the post-seam span of every `both` file; the whole of an `alpaca_only` file),
and the T-082b DRIP — Stooq bars scaled by a fitted exp(a + b·t), a constant-yield APPROXIMATION
that smears every ex-date step into a drift — before the seam. Option (a) keeps the drip and
LABELS it everywhere: every name in a run's panel carries, in the census, what each span of its
file IS. The label is never a default: it comes from the file's pinned write record (`convention`,
written by `tr_writer.full_refetch`), else from a declared whole-file override
(`config/convention_declarations.json`, for a file regenerated whole after the merge whose merge
record is stale — SPY), else from the merge record (`_merge_meta.json`) under the cache, WITNESSED
against the run's own frame (a frame that starts before the record's first bar proves the record
stale). A merge-record label with NO frame to witness it is UNMEASURED (R9, 2026-11-04): the name
is unlabelled with that reason, never labelled on trust — the writer's record and a declared
override need no witness (they describe the file itself); the merge record describes the file as
it was on 2026-05-23, so without the frame nothing proves it current. A name with none of the three
is UNLABELLED, by name and with the reason, and the census gate FAILS the run on it. A cache with
no merge record labels nothing from it, and says so (`merge_meta_present: False`) — the gate reads
that as every record-labelled name missing.

ONE function, called by BOTH census producers (`backtester/backtest_controller.py:_build_census`
and `engines/engine_d_discovery/discovery.py:candidate_census_block`), under the two-producer lock
in `tests/test_contracts.py` (`CENSUS_PROVENANCE_KEYS`). The same per-name resolution
(`_resolve`) gives the stale/holed-files guard each drip-labelled name's seam and kept pre-seam bar
count (`drip_spans`) for the `pre_seam_drip_gap` class (`coverage.py`), so the label and the
guard can never disagree on where a file's drip span is.
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
        "override, else the merge record (witnessed against the run's frame — unwitnessed, it is "
        "unmeasured); a name with none of the three is UNLABELLED by name — never defaulted — and the "
        "gate fails the run")
SEAM_SEP = "<"
SIDE_SEP = "|"
#: The witness summary a record carries: "frames" when the caller gave the run's frames (every
#: merge-record label checked against its frame), "unmeasured" when it gave none (R9).
WITNESS_FRAMES = "frames"
WITNESS_UNMEASURED = "unmeasured"


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


def cache_first_bar_frames(cache_dir: Path, names: Optional[Iterable[str]] = None) -> Dict[str, pd.DataFrame]:
    """One-row frames at each file's FIRST bar, read from the cache's own `<T>_1d.csv` files — the
    witness for a cache-wide label (the pass driver's `label`, the canonical data lock), where no
    run's frames exist: the file on disk IS what a run would load. A name with no csv is absent
    from the map, so its merge-record label stays unwitnessed (fail closed)."""
    cache_dir = Path(cache_dir)
    names = sorted(names) if names is not None else sorted(p.name[:-7] for p in cache_dir.glob("*_1d.csv"))
    out: Dict[str, pd.DataFrame] = {}
    for t in names:
        p = cache_dir / f"{t}_1d.csv"
        if not p.exists():
            continue
        with p.open() as fh:
            fh.readline()                       # the header
            first = fh.readline().split(",", 1)[0].strip()
        if first:
            out[t] = pd.DataFrame({"Close": [float("nan")]}, index=pd.DatetimeIndex([pd.Timestamp(first)]))
    return out


def _resolve(t: str, records_dir: Path, overrides: Dict[str, dict], meta: Optional[Dict[str, dict]],
             frame: Optional[pd.DataFrame], witnessed: bool) -> dict:
    """ONE per-name resolution: the write record, else the declared override, else the merge
    record witnessed against `frame`. Returns {"label", "source"} plus, for a drip pre-seam span,
    {"seam_date", "n_pre_seam_kept"} (the kept bar count the record carries — None when it does
    not); or {"unlabelled": reason}. `witnessed` is False when the caller gave no frames at all."""
    rec_path = records_dir / f"{t}.json"
    if rec_path.exists():
        rec = json.loads(rec_path.read_text())
        conv = rec.get("convention")
        if not conv:
            return {"unlabelled": ("a pinned write record with no convention block — written before the "
                                   "option (a) writer (2026-10-22); the file's spans are unrecorded")}
        out = {"label": label_of(conv), "source": "write_record"}
        if conv.get("pre_seam") == DRIP and conv.get("seam_date"):
            seam = rec.get("seam") or {}
            kept = seam.get("n_pre_seam_bars_kept")
            out.update(seam_date=str(conv["seam_date"]), n_pre_seam_kept=int(kept) if kept is not None else None)
        return out
    if t in overrides:
        return {"label": str(overrides[t]["convention"]), "source": "declared_override"}
    if meta is None:
        return {"unlabelled": f"no write record, no override, and the cache has no {MERGE_META_NAME}"}
    entry = meta.get(t)
    if entry is None:
        return {"unlabelled": "no write record, no override, no merge record for the name"}
    first = _first_bar(frame)
    if first is None:
        how = "no frames were given (data_map=None)" if not witnessed else "the name has no frame in data_map"
        return {"unlabelled": (f"UNWITNESSED: the merge record would label the name, but {how} — the "
                               f"record describes the file as merged on 2026-05-23 and nothing proves it "
                               f"current; the label is unmeasured, never taken on trust")}
    if entry.get("first_bar_date") and first < pd.Timestamp(entry["first_bar_date"]):
        return {"unlabelled": (f"the merge record is STALE: the frame starts {first.date()}, before the "
                               f"record's first bar {entry['first_bar_date']} — the file was rewritten "
                               f"after the merge without a record or an override")}
    if (entry.get("merge_case") == "both" and int(entry.get("n_stooq_pre_seam") or 0) > 0
            and entry.get("seam_date")):
        return {"label": label_of({"pre_seam": DRIP, "seam_date": entry["seam_date"], "post_seam": EXACT_TR}),
                "source": "merge_meta", "seam_date": str(entry["seam_date"]),
                "n_pre_seam_kept": int(entry["n_stooq_pre_seam"])}
    return {"label": EXACT_TR, "source": "merge_meta"}      # alpaca_only, or `both` with no pre-seam bars (AMCR)


def substrate_convention_record(cache_dir: Path, run_names: Optional[Iterable[str]] = None,
                                data_map: Optional[Dict[str, pd.DataFrame]] = None,
                                conventions: Optional[Dict[str, dict]] = None) -> dict:
    """The `substrate_convention` census block over `run_names` (the panel; every name in the merge
    record when None). Per name: its label (`per_name`), or why it has none (`unlabelled`). The
    block names the directory it READ (`cache_dir`), whether the merge record and the write
    records were there, and its `witness` — "frames" when every merge-record label was checked
    against the run's frame, "unmeasured" when no frames were given (R9: the merge-record names are
    then unlabelled, `n_unwitnessed` counts them, and the gate fails the run on them)."""
    cache_dir = Path(cache_dir)
    meta = load_merge_meta(cache_dir)
    conventions = load_convention_declarations() if conventions is None else conventions
    overrides = conventions["whole_file_overrides"]
    records_dir = cache_dir / WRITE_RECORDS_DIR
    if run_names is None and meta is None:
        raise FileNotFoundError(f"{cache_dir / MERGE_META_NAME}: no merge record and no run names — "
                                f"nothing to label")
    names = sorted(set(run_names)) if run_names is not None else sorted(meta)
    witnessed = data_map is not None
    per_name: Dict[str, str] = {}
    unlabelled: Dict[str, str] = {}
    sources: Counter = Counter()
    n_unwitnessed = 0
    for t in names:
        r = _resolve(t, records_dir, overrides, meta, data_map.get(t) if witnessed else None, witnessed)
        if "unlabelled" in r:
            unlabelled[t] = r["unlabelled"]
            n_unwitnessed += int(r["unlabelled"].startswith("UNWITNESSED"))
            continue
        per_name[t] = r["label"]
        sources[r["source"]] += 1
    labels = Counter(per_name.values())
    seams = Counter(v.split(SEAM_SEP, 1)[1].split(SIDE_SEP, 1)[0] for v in per_name.values() if SEAM_SEP in v)
    return {"cache_dir": str(cache_dir), "merge_meta_present": meta is not None,
            "records_dir_present": records_dir.is_dir(), "rule": RULE,
            "witness": WITNESS_FRAMES if witnessed else WITNESS_UNMEASURED, "n_unwitnessed": n_unwitnessed,
            "n_names": len(names), "n_labelled": len(per_name),
            "n_pre_seam_drip": int(sum(v for k, v in labels.items() if k.startswith(DRIP + SEAM_SEP))),
            "labels": dict(labels), "seams": dict(seams), "sources": dict(sources),
            "per_name": per_name, "unlabelled": unlabelled}


def drip_spans(cache_dir: Path, names: Iterable[str], data_map: Optional[Dict[str, pd.DataFrame]],
               conventions: Optional[Dict[str, dict]] = None) -> Dict[str, dict]:
    """Per name, for the guard's `pre_seam_drip_gap` class: `{"seam_date", "n_pre_seam_kept",
    "source"}` where the name's label carries a drip pre-seam span, else `{"refused": why}` — the
    name is unlabelled or unwitnessed (the same resolution as the label, so the class can never
    excuse a hole on a span the label does not call drip), or its label has no pre-seam drip."""
    cache_dir = Path(cache_dir)
    meta = load_merge_meta(cache_dir)
    conventions = load_convention_declarations() if conventions is None else conventions
    records_dir = cache_dir / WRITE_RECORDS_DIR
    witnessed = data_map is not None
    out: Dict[str, dict] = {}
    for t in sorted(set(names)):
        r = _resolve(t, records_dir, conventions["whole_file_overrides"], meta,
                     data_map.get(t) if witnessed else None, witnessed)
        if "unlabelled" in r:
            out[t] = {"refused": f"no convention label: {r['unlabelled']}"}
        elif "seam_date" not in r:
            out[t] = {"refused": f"the label is {r['label']!r}: no pre-seam drip span"}
        else:
            out[t] = {"seam_date": r["seam_date"], "n_pre_seam_kept": r["n_pre_seam_kept"], "source": r["source"]}
    return out
