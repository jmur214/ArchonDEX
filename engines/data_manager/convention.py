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

OPTION (a′) (USER RULING 2026-11-12, T-387): the cutover's pre-seam convention is `era_tr` (Stooq
where Stooq is total return; the missed dividends restored per measured ex-date; no-reference spans
raw Stooq, LABELLED UNVERIFIED), written by `tr_writer.era_tr_rewrite` into the file's record. The
label reads it from the record like any other; an era_tr record must carry its `era_tr` block (the
per-file `unverified_missed_era_spans` / `unverified_pre2003_span`), or the name is UNLABELLED —
the census could no longer say what each span IS. The block carries the unverified spans per name
(`unverified`). `pre_seam_spans` (the guard's input; `drip_spans` is its old name, kept) covers a
kept pre-seam Stooq span under EITHER label: (a′) changes no pre-seam date, so the kept span's own
holes are the same days. `drip` stays a valid label — it is what the pre-cutover cache IS.

THE MERGE-RECORD `drip` FALLBACK FAILS CLOSED after (a′) (the T-387 review's MAJOR, 2026-11-12). The
merge record describes every `both` file as drip, which stops being true once the (a′) rewrite has
run; read without the file's write record it would silently re-label an era_tr file drip. So the
fallback may label a seam file drip ONLY with POSITIVE evidence that the file IS the drip:
  1. its bytes (csv, and the parquet twin where present) equal the FROZEN drip-cache witness
     (`config/drip_cache_witness_repin1.json`, derived from re-pin #1's committed manifest). The (a′)
     rewrite changes 573 of the 575 files, so a rewritten file can never match; an ABSENT witness,
     an absent file or an unlisted name labels nothing drip. Evidence that is MISSING therefore reads
     as "not proven drip", never as "drip" — the signal cannot be forged by omission;
  2. and the cache holds NO era_tr write record. The two files (a′) leaves byte-identical (PODD,
     POM) would pass rule 1; a cache with any era_tr record is post-(a′), and there a seam file with no
     write record is UNLABELLED, never inferred. (This rule alone could be defeated by dropping every
     record — rule 1 is what holds then; for PODD/POM the drip label would still be byte-true.)
Hashes are computed once per file version per process (keyed by path, size and mtime).
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import pandas as pd

from engines.data_manager.tr_writer import (DRIP, ERA_TR, EXACT_TR, MERGE_META_NAME, PRE_SEAM_CONVENTIONS,
                                            WRITE_RECORDS_DIR, load_convention_declarations, load_merge_meta)

RULE = ("pre-seam = era_tr (option (a') — Stooq where Stooq is total return, the missed dividends "
        "restored per measured ex-date, no-reference spans raw Stooq and LABELLED UNVERIFIED; the "
        "cutover's convention, read from the write record with its unverified spans) or drip (T-082b's "
        "constant-yield approximation of the Stooq years; the pre-cutover cache); post-seam = "
        "exact_tr (the provider's ex-date total return); a file with no seam is one convention over "
        "its whole span. A name's label comes from its pinned write record, else a declared whole-file "
        "override, else the merge record (witnessed against the run's frame — unwitnessed, it is "
        "unmeasured; a seam file's drip label also needs its bytes to equal the frozen drip-cache "
        "witness and the cache to hold no era_tr record — never inferred after (a')); a name with none "
        "of the three is UNLABELLED by name — never defaulted — and the gate fails the run")
SEAM_SEP = "<"
SIDE_SEP = "|"
#: The FROZEN drip-cache witness (module docstring): the bytes re-pin #1 pinned for every merged file
#: with pre-seam bars. Never regenerated from a later manifest.
DRIP_WITNESS_PATH = Path(__file__).resolve().parents[2] / "config" / "drip_cache_witness_repin1.json"
#: The unverified-span keys an era_tr write record's block MUST carry (values may be empty) — a block
#: without them cannot say what is unverified, so the name is unlabelled.
ERA_TR_BLOCK_KEYS = ("unverified_missed_era_spans", "unverified_pre2003_span")
_DEFAULT = "default"
_SHA_CACHE: Dict[Tuple[str, int, int], str] = {}


#: The commit whose `config/substrate_manifest.sha256` the frozen witness was derived from (re-pin #1).
DRIP_WITNESS_SOURCE_COMMIT = "1bb6764"
_DRIP_WITNESS_DOC = (
    "The DRIP-CACHE WITNESS (T-387 follow-up, 2026-11-12): positive evidence that a merged file IS the "
    "T-082b drip as re-pin #1 pinned it. The census's merge-record fallback may label a seam file `drip` "
    "ONLY when its bytes equal these (engines/data_manager/convention.py); a file the (a′) rewrite changed "
    "can never match, and an ABSENT witness labels nothing drip (fail closed). FROZEN: derived once from "
    "the committed re-pin #1 manifest, never regenerated from a later manifest (after re-pin #2 that "
    "manifest pins the era_tr bytes). Recipe: for every `both` file with n_stooq_pre_seam > 0 in "
    "data/processed/_merge_meta.json, the sha256 lines of data/processed/<T>_1d.csv and "
    "data/processed/parquet/<T>_1d.parquet in source_manifest.")


def derive_drip_witness_text(manifest_bytes: bytes, merge_meta_bytes: bytes) -> str:
    """THE recipe of `config/drip_cache_witness_repin1.json`, as text (its exact bytes): from re-pin #1's
    manifest (`git show 1bb6764:config/substrate_manifest.sha256`) and the merge record, every merged
    file with pre-seam bars and the sha256 the manifest pins for its csv and parquet. The lock in
    tests/test_era_tr_writer_t387.py re-derives it and asserts byte-equality with the committed file."""
    pins: Dict[str, str] = {}
    for ln in manifest_bytes.decode().splitlines():
        if ln.strip():
            h, path = ln.split("  ", 1)
            pins[path] = h
    meta = json.loads(merge_meta_bytes.decode())["per_ticker"]
    targets = sorted(t for t, r in meta.items()
                     if r.get("merge_case") == "both" and int(r.get("n_stooq_pre_seam") or 0) > 0)
    files = {t: {"csv": pins[f"data/processed/{t}_1d.csv"], "parquet": pins[f"data/processed/parquet/{t}_1d.parquet"]}
             for t in targets}
    out = {"_doc": _DRIP_WITNESS_DOC, "source_manifest": "config/substrate_manifest.sha256",
           "source_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
           "source_commit": f"{DRIP_WITNESS_SOURCE_COMMIT} (RE-PIN #1 — the drip substrate PINNED)",
           "merge_record_sha256": hashlib.sha256(merge_meta_bytes).hexdigest(),
           "n_files": len(files), "files": files}
    return json.dumps(out, indent=1, sort_keys=False) + "\n"


def load_drip_witness(path: Path = DRIP_WITNESS_PATH) -> Optional[Dict[str, dict]]:
    """The frozen witness's per-name hashes, or None when the file is absent (then NOTHING is labelled
    drip from the merge record — fail closed). A malformed witness raises."""
    path = Path(path)
    if not path.exists():
        return None
    files = json.loads(path.read_text())["files"]
    if not isinstance(files, dict):
        raise ValueError(f"{path}: `files` is not a map")
    return files


def _sha256(path: Path) -> str:
    st = path.stat()
    key = (str(path.resolve()), st.st_size, st.st_mtime_ns)
    if key not in _SHA_CACHE:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        _SHA_CACHE[key] = h.hexdigest()
    return _SHA_CACHE[key]


def is_drip_witnessed(cache_dir: Path, t: str, witness: Optional[Dict[str, dict]]) -> Optional[str]:
    """None when the file under `cache_dir` IS the drip the witness pinned (csv always; parquet where
    the cache holds one); else why it is not proven drip."""
    if witness is None:
        return ("no drip-cache witness (config/drip_cache_witness_repin1.json absent) — a seam file with "
                "no write record is never inferred drip")
    pins = witness.get(t)
    if not pins:
        return "the name is not in the drip-cache witness — its file is not proven to be the drip"
    csv = Path(cache_dir) / f"{t}_1d.csv"
    if not csv.exists():
        return f"no {csv.name} under the cache — the drip cannot be witnessed"
    if _sha256(csv) != pins.get("csv"):
        return (f"{csv.name} is NOT the drip re-pin #1 pinned (its bytes differ) and it has no write record "
                f"— after the (a′) rewrite a seam file is labelled only from its record")
    pq = Path(cache_dir) / "parquet" / f"{t}_1d.parquet"
    if pq.exists() and _sha256(pq) != pins.get("parquet"):
        return (f"parquet/{pq.name} is NOT the drip re-pin #1 pinned (its bytes differ) and the file has no "
                f"write record")
    return None


def stooq_corrections_label(block: dict) -> dict:
    """T-394: what an era_tr write record says about the Stooq corrections — the Tier-1 rows applied to the
    file and its Tier-2 label (found, NOT applied). A block with no label (`unverified_stooq_corrections`
    absent or null: written without the pinned table) reads `recorded: False`, never as zero."""
    applied = ((block.get("stooq_corrections") or {}).get("applied")) or []
    lab = block.get("unverified_stooq_corrections")
    if lab is None:
        return {"tier1_applied": len(applied), "recorded": False, "n_steps": None, "n_blocks": None,
                "n_known_unapplied": None}
    return {"tier1_applied": len(applied), "recorded": True, "n_steps": int(lab.get("n_steps", 0)),
            "n_blocks": int(lab.get("n_blocks", 0)), "n_known_unapplied": len(lab.get("known_unapplied") or []),
            "table_sha256": (block.get("stooq_corrections") or {}).get("table_sha256")}


def era_tr_records_present(records_dir: Path) -> bool:
    """The cache is post-(a′): at least one pinned write record labels a pre-seam span era_tr."""
    if not records_dir.is_dir():
        return False
    for p in records_dir.glob("*.json"):
        try:
            conv = json.loads(p.read_text()).get("convention") or {}
        except (OSError, ValueError):
            continue          # an unreadable record is that name's problem (`_resolve` reports it)
        if conv.get("pre_seam") == ERA_TR:
            return True
    return False
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
             frame: Optional[pd.DataFrame], witnessed: bool, drip_witness: Optional[Dict[str, dict]] = None,
             post_a_prime: bool = False) -> dict:
    """ONE per-name resolution: the write record, else the declared override, else the merge
    record witnessed against `frame` (and, for a seam file, against the drip-cache witness and the
    post-(a′) rule — module docstring). Returns {"label", "source"} plus, for a kept pre-seam span,
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
        if conv.get("pre_seam") == ERA_TR:
            block = rec.get("era_tr")
            if not block:
                return {"unlabelled": ("the write record says the pre-seam span is era_tr but carries no "
                                       "era_tr block — its UNVERIFIED spans are unknown, so what each span "
                                       "IS cannot be said")}
            missing = [k for k in ERA_TR_BLOCK_KEYS if k not in block]
            if missing:
                return {"unlabelled": (f"the write record's era_tr block lacks {missing} — what is UNVERIFIED "
                                       f"in the span is unknown; never read as fully verified")}
            out["unverified"] = {"missed_era_spans": list(block["unverified_missed_era_spans"] or []),
                                 "pre2003_span": block["unverified_pre2003_span"]}
            out["stooq"] = stooq_corrections_label(block)
        if conv.get("pre_seam") in PRE_SEAM_CONVENTIONS and conv.get("seam_date"):
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
        # The drip is never INFERRED after (a′): positive evidence only (module docstring).
        if post_a_prime:
            return {"unlabelled": ("the cache is post-(a′) (an era_tr write record is present): a seam file "
                                   "with no write record is never inferred drip from the merge record")}
        why = is_drip_witnessed(records_dir.parent, t, drip_witness)
        if why is not None:
            return {"unlabelled": why}
        return {"label": label_of({"pre_seam": DRIP, "seam_date": entry["seam_date"], "post_seam": EXACT_TR}),
                "source": "merge_meta", "seam_date": str(entry["seam_date"]),
                "n_pre_seam_kept": int(entry["n_stooq_pre_seam"])}
    return {"label": EXACT_TR, "source": "merge_meta"}      # alpaca_only, or `both` with no pre-seam bars (AMCR)


def substrate_convention_record(cache_dir: Path, run_names: Optional[Iterable[str]] = None,
                                data_map: Optional[Dict[str, pd.DataFrame]] = None,
                                conventions: Optional[Dict[str, dict]] = None,
                                drip_witness: Any = _DEFAULT) -> dict:
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
    drip_witness = load_drip_witness() if isinstance(drip_witness, str) and drip_witness == _DEFAULT else drip_witness
    post_a_prime = era_tr_records_present(records_dir)
    per_name: Dict[str, str] = {}
    unlabelled: Dict[str, str] = {}
    sources: Counter = Counter()
    n_unwitnessed = 0
    unverified: Dict[str, dict] = {}
    stooq: Dict[str, dict] = {}
    for t in names:
        r = _resolve(t, records_dir, overrides, meta, data_map.get(t) if witnessed else None, witnessed,
                     drip_witness, post_a_prime)
        if "unlabelled" in r:
            unlabelled[t] = r["unlabelled"]
            n_unwitnessed += int(r["unlabelled"].startswith("UNWITNESSED"))
            continue
        per_name[t] = r["label"]
        sources[r["source"]] += 1
        u = r.get("unverified")
        if u and (u["missed_era_spans"] or u["pre2003_span"]):
            unverified[t] = u
        if r.get("stooq") is not None:
            stooq[t] = r["stooq"]
    labels = Counter(per_name.values())
    seams = Counter(v.split(SEAM_SEP, 1)[1].split(SIDE_SEP, 1)[0] for v in per_name.values() if SEAM_SEP in v)
    return {"cache_dir": str(cache_dir), "merge_meta_present": meta is not None,
            "records_dir_present": records_dir.is_dir(), "rule": RULE,
            "witness": WITNESS_FRAMES if witnessed else WITNESS_UNMEASURED, "n_unwitnessed": n_unwitnessed,
            # the merge-record drip fallback's evidence (T-387 review): the frozen witness, and the
            # post-(a′) rule that switches the fallback off for every seam file
            "drip_witness_present": drip_witness is not None, "post_a_prime": post_a_prime,
            "n_names": len(names), "n_labelled": len(per_name),
            "n_pre_seam_drip": int(sum(v for k, v in labels.items() if k.startswith(DRIP + SEAM_SEP))),
            "n_pre_seam_era_tr": int(sum(v for k, v in labels.items() if k.startswith(ERA_TR + SEAM_SEP))),
            # option (a′): what is UNVERIFIED inside each era_tr span, per name (never dropped)
            "n_unverified_missed_era": sum(1 for u in unverified.values() if u["missed_era_spans"]),
            "n_unverified_pre2003": sum(1 for u in unverified.values() if u["pre2003_span"]),
            "unverified": unverified,
            # T-394: the pinned Tier-1 Stooq corrections each era_tr file received, and its Tier-2 LABEL —
            # corrections found and NOT applied (yfinance-derived, unverified). "not_recorded" is a file
            # written without the table: its label is unknown, never read as "nothing unverified".
            "n_stooq_tier1_applied": sum(1 for v in stooq.values() if v["tier1_applied"]),
            "n_stooq_tier1_rows": sum(v["tier1_applied"] for v in stooq.values()),
            "n_unverified_stooq_corrections": sum(1 for v in stooq.values()
                                                  if v["recorded"] and (v["n_steps"] or v["n_blocks"] or v["n_known_unapplied"])),
            "n_stooq_label_not_recorded": sum(1 for v in stooq.values() if not v["recorded"]),
            "stooq_corrections": {t: v for t, v in stooq.items()
                                  if v["tier1_applied"] or not v["recorded"] or v["n_steps"] or v["n_blocks"]
                                  or v["n_known_unapplied"]},
            "labels": dict(labels), "seams": dict(seams), "sources": dict(sources),
            "per_name": per_name, "unlabelled": unlabelled}


def pre_seam_spans(cache_dir: Path, names: Iterable[str], data_map: Optional[Dict[str, pd.DataFrame]],
                   conventions: Optional[Dict[str, dict]] = None, drip_witness: Any = _DEFAULT) -> Dict[str, dict]:
    """Per name, for the guard's `pre_seam_drip_gap` class: `{"seam_date", "n_pre_seam_kept",
    "source"}` where the name's label carries a KEPT pre-seam Stooq span (drip or, after the
    cutover, era_tr — the same bar dates), else `{"refused": why}` — the name is unlabelled or
    unwitnessed (the same resolution as the label, so the class can never excuse a hole on a span
    the label does not call a kept pre-seam span), or its label has no pre-seam span."""
    cache_dir = Path(cache_dir)
    meta = load_merge_meta(cache_dir)
    conventions = load_convention_declarations() if conventions is None else conventions
    records_dir = cache_dir / WRITE_RECORDS_DIR
    witnessed = data_map is not None
    drip_witness = load_drip_witness() if isinstance(drip_witness, str) and drip_witness == _DEFAULT else drip_witness
    post_a_prime = era_tr_records_present(records_dir)
    out: Dict[str, dict] = {}
    for t in sorted(set(names)):
        r = _resolve(t, records_dir, conventions["whole_file_overrides"], meta,
                     data_map.get(t) if witnessed else None, witnessed, drip_witness, post_a_prime)
        if "unlabelled" in r:
            out[t] = {"refused": f"no convention label: {r['unlabelled']}"}
        elif "seam_date" not in r:
            out[t] = {"refused": f"the label is {r['label']!r}: no pre-seam drip span or era_tr span"}
        else:
            out[t] = {"seam_date": r["seam_date"], "n_pre_seam_kept": r["n_pre_seam_kept"], "source": r["source"]}
    return out


#: The pre-(a′) name of `pre_seam_spans` (2026-11-04), kept for its callers.
drip_spans = pre_seam_spans
