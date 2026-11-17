"""Option (a)'s UNIVERSAL convention label (2026-10-22): every name in a run's panel carries, in the
census, what each span of its file IS — the pre-seam DRIP vs exact total return — from its pinned
write record, else a declared override, else the merge record witnessed against the run's frame.
Never a default: an unlabelled name FAILS the gate; so does an errored record. Written by BOTH
census producers (the two-producer lock in tests/test_contracts.py names the key)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from core.census import assert_census
from engines.data_manager import tr_writer as w
from engines.data_manager.convention import cache_first_bar_frames, label_of, substrate_convention_record

IDX = pd.bdate_range("2024-01-02", periods=30)
NO_CONV = {s: {} for s in w.CONVENTION_SECTIONS}


def _cache(tmp_path: Path, meta: dict | None, records: dict | None = None) -> Path:
    d = tmp_path / "cache"
    d.mkdir()
    if meta is not None:
        (d / w.MERGE_META_NAME).write_text(json.dumps({"per_ticker": meta}))
    for t, rec in (records or {}).items():
        (d / w.WRITE_RECORDS_DIR).mkdir(exist_ok=True)
        (d / w.WRITE_RECORDS_DIR / f"{t}.json").write_text(json.dumps({"ticker": t, **rec}))
    return d


def _entry(case="both", seam="2018-01-02", n_pre=100, first="2000-01-03"):
    return {"merge_case": case, "seam_date": seam if case == "both" else None,
            "n_stooq_pre_seam": n_pre if case == "both" else 0, "first_bar_date": first}


def _witness(d: Path, *names: str) -> dict:
    """A PLANTED drip-cache witness for planted merge-record names (T-387 review, 2026-11-12): the
    merge-record fallback labels a seam file drip only when its bytes equal the frozen witness, so a
    planted cache certifies its own planted files — a minimal csv where the name has none (an existing
    csv is never overwritten), and the witness is that file's sha256."""
    import hashlib
    out = {}
    for t in names:
        csv = d / f"{t}_1d.csv"
        if not csv.exists():
            csv.write_text("Date,Open,High,Low,Close,Volume\n2000-01-03,1,1,1,1,1\n")
        out[t] = {"csv": hashlib.sha256(csv.read_bytes()).hexdigest()}
    return out


def _frame(start="2024-01-02"):
    return pd.DataFrame({"Close": 1.0}, index=pd.bdate_range(start, periods=30))


def _gate(block):
    return assert_census({"census": {"n_resolved": 1, "n_in_panel": 1, "n_trades": 3,
                                     "trades_canon_md5": "0" * 32, "regime_total_bars": 10,
                                     "regime_unknown_frac": 0.0, "substrate_convention": block},
                          "bootstrap_ci_skip_reason": "test"})


# ── the three sources, in order, and the label's form ─────────────────────────────

def test_labels_come_from_the_write_record_then_the_override_then_the_merge_record(tmp_path):
    d = _cache(tmp_path, {"REC": _entry(), "OVR": _entry(case="alpaca_only"), "META": _entry(),
                          "WHOLE": _entry(case="alpaca_only"), "NOPRE": _entry(n_pre=0)},
               records={"REC": {"convention": {"pre_seam": "drip", "seam_date": "2020-04-09", "post_seam": "exact_tr"}}})
    conv = {**NO_CONV, "whole_file_overrides": {"OVR": {"convention": "exact_tr"}}}
    names = ["REC", "OVR", "META", "WHOLE", "NOPRE"]
    r = substrate_convention_record(d, run_names=names, data_map={t: _frame() for t in names}, conventions=conv,
                                    drip_witness=_witness(d, "META"))
    assert r["per_name"] == {"REC": "drip<2020-04-09|exact_tr", "OVR": "exact_tr",
                             "META": "drip<2018-01-02|exact_tr", "WHOLE": "exact_tr", "NOPRE": "exact_tr"}
    assert r["sources"] == {"write_record": 1, "declared_override": 1, "merge_meta": 3}
    assert r["n_pre_seam_drip"] == 2 and r["seams"] == {"2020-04-09": 1, "2018-01-02": 1}
    assert r["unlabelled"] == {} and r["merge_meta_present"] and r["records_dir_present"]
    assert r["cache_dir"] == str(d) and r["witness"] == "frames" and r["n_unwitnessed"] == 0
    assert _gate(r).canonical


def test_the_record_wins_over_the_merge_record_for_a_rewritten_file(tmp_path):
    """A file written whole by the writer (AMCR after its declared re-fetch) reads from its record,
    not the merge record it no longer matches."""
    d = _cache(tmp_path, {"X": _entry()}, records={"X": {"convention": {"whole": "exact_tr"}}})
    assert substrate_convention_record(d, run_names=["X"], conventions=NO_CONV)["per_name"] == {"X": "exact_tr"}


def test_label_of_is_the_one_string_form():
    assert label_of({"whole": "exact_tr"}) == "exact_tr"
    assert label_of({"pre_seam": "drip", "seam_date": "2018-01-02", "post_seam": "exact_tr"}) == "drip<2018-01-02|exact_tr"


# ── never a default: unlabelled names, by name and reason, FAIL the gate ───────────

def test_a_name_with_no_record_no_override_and_no_merge_entry_is_UNLABELLED_and_the_gate_fails(tmp_path):
    d = _cache(tmp_path, {"KNOWN": _entry()})
    r = substrate_convention_record(d, run_names=["KNOWN", "NEWT"], data_map={"KNOWN": _frame(), "NEWT": _frame()},
                                    conventions=NO_CONV, drip_witness=_witness(d, "KNOWN"))
    assert r["per_name"] == {"KNOWN": "drip<2018-01-02|exact_tr"}
    assert list(r["unlabelled"]) == ["NEWT"] and "no merge record" in r["unlabelled"]["NEWT"]
    v = _gate(r)
    assert not v.canonical and any("NEWT" in f and "NO convention label" in f for f in v.failures), v.failures


def test_a_merge_record_the_runs_own_frame_proves_STALE_is_unlabelled(tmp_path):
    """SPY's shape: the merge record says alpaca_only from 2020-04-09; the file (and the frame)
    start 1993. The record is stale, and only a declared override may label the name."""
    d = _cache(tmp_path, {"SPY": _entry(case="alpaca_only", first="2020-04-09")})
    frame = _frame("1993-01-29")
    r = substrate_convention_record(d, run_names=["SPY"], data_map={"SPY": frame}, conventions=NO_CONV)
    assert "STALE" in r["unlabelled"]["SPY"] and not _gate(r).canonical
    conv = {**NO_CONV, "whole_file_overrides": {"SPY": {"convention": "exact_tr"}}}
    r2 = substrate_convention_record(d, run_names=["SPY"], data_map={"SPY": frame}, conventions=conv)
    assert r2["per_name"] == {"SPY": "exact_tr"} and _gate(r2).canonical


def test_a_pinned_record_WITHOUT_a_convention_block_is_unlabelled_not_assumed(tmp_path):
    """A file written by the writer before option (a) has a record but no convention: its spans
    are unrecorded, and the merge record is not consulted for a rewritten file."""
    d = _cache(tmp_path, {"X": _entry()}, records={"X": {"mode": "adjusted"}})
    r = substrate_convention_record(d, run_names=["X"], conventions=NO_CONV)
    assert "no convention block" in r["unlabelled"]["X"] and not _gate(r).canonical


def test_a_cache_with_NO_merge_record_labels_nothing_from_it_and_says_so(tmp_path):
    d = _cache(tmp_path, None)
    r = substrate_convention_record(d, run_names=["A", "B"], conventions=NO_CONV)
    assert r["merge_meta_present"] is False and set(r["unlabelled"]) == {"A", "B"}
    assert all(w.MERGE_META_NAME in why for why in r["unlabelled"].values())
    assert not _gate(r).canonical
    with pytest.raises(FileNotFoundError):
        substrate_convention_record(d, conventions=NO_CONV)        # no names and no record: nothing to label


def test_an_ERRORED_substrate_convention_record_fails_the_gate_and_an_absent_one_warns():
    v = _gate({"error": "RuntimeError('boom')"})
    assert any("substrate_convention record errored" in f for f in v.failures)
    v2 = assert_census({"census": {"n_resolved": 1, "n_in_panel": 1, "n_trades": 3, "trades_canon_md5": "0" * 32,
                                   "regime_total_bars": 10, "regime_unknown_frac": 0.0},
                        "bootstrap_ci_skip_reason": "test"})
    assert any("no substrate_convention record" in x for x in v2.warnings)


# ── both producers, EXECUTED, on the canonical cache ──────────────────────────────

def test_the_candidate_producer_labels_its_names_and_refuses_an_unknown_one():
    from engines.engine_d_discovery.discovery import candidate_census_block

    class _C:
        nonzero_calls, errors = 5, 0
    good = candidate_census_block("cand_v1", _C(), n_trades=50, data_map={"SPY": _frame(), "AAPL": _frame()},
                                  window=(str(IDX[0].date()), str(IDX[-1].date())))
    sc = good["substrate_convention"]
    assert "error" not in sc and sc["per_name"]["SPY"] == "exact_tr" and sc["unlabelled"] == {}
    bad = candidate_census_block("cand_v1", _C(), n_trades=50, data_map={"SPY": _frame(), "ZZZZ": _frame()},
                                 window=(str(IDX[0].date()), str(IDX[-1].date())))
    v = assert_census({"census": bad, "bootstrap_ci_skip_reason": "test"})
    assert any("ZZZZ" in f and "NO convention label" in f for f in v.failures), v.failures
    assert "error" in candidate_census_block("cand_v1", _C(), n_trades=50)["substrate_convention"]


def test_the_backtest_producer_labels_the_panel_from_the_canonical_cache(tmp_path):
    from backtester.backtest_controller import BacktestController

    class _Alpha:
        class collector:
            _signal_counts, _bars_collected, _edge_errors, _edge_error_samples = {"e": 3}, 40, {}, {}

        class processor:
            paused_edge_ids: set = set()
        edges = {"e": object()}

    ctrl = object.__new__(BacktestController)
    ctrl.alpha, ctrl.regime_detector = _Alpha(), object()
    ctrl.data_map = {"SPY": _frame(), "C": _frame(), "ZZZZ": _frame()}
    ctrl._census_n_resolved = 3
    ctrl._census_regime_total_bars, ctrl._census_regime_unknown_bars = 40, 3
    ctrl._membership_intervals, ctrl._census_universe = None, sorted(ctrl.data_map)
    ctrl._census_window = (str(IDX[0].date()), str(IDX[-1].date()))
    p = tmp_path / "trades.csv"
    pd.DataFrame({"ticker": ["SPY"], "pnl": [1.0]}).to_csv(p, index=False)
    sc = ctrl._build_census(str(p))["substrate_convention"]
    assert sc["cache_dir"] == str(w.CANONICAL_CACHE_DIR) and sc["per_name"]["SPY"] == "exact_tr"
    assert sc["per_name"]["C"] == "drip<2020-04-09|exact_tr" and list(sc["unlabelled"]) == ["ZZZZ"]
    # R9 (2026-11-04): the controller hands the label its FRAMES — C's merge-record label is witnessed.
    assert sc["witness"] == "frames" and sc["n_unwitnessed"] == 0


def test_the_canonical_cache_is_labelled_whole_with_575_pre_seam_drip_files():
    """A data lock on today's canonical cache: every one of the 730 files labelled, none by default;
    575 carry a pre-seam drip span (the 626 `both` files minus 51 with no pre-seam bars); SPY by
    its declared override. Fails when the cache or its merge record changes — re-measure, re-pin.
    Note, 2026-11-12 (T-387): still true of TODAY's canonical (drip). It flips on cutover day under the
    USER's (a′) ruling — 575 `era_tr` from the write records — in re-pin #2's commit (runbook §6, S6)."""
    # R9 (2026-11-04): a cache-wide label is witnessed against the FILES' first bars (what a run loads).
    r = substrate_convention_record(w.CANONICAL_CACHE_DIR, data_map=cache_first_bar_frames(w.CANONICAL_CACHE_DIR))
    assert r["n_names"] == 730 and r["n_labelled"] == 730 and r["unlabelled"] == {}
    assert r["witness"] == "frames" and r["n_unwitnessed"] == 0
    assert r["n_pre_seam_drip"] == 575 and r["labels"]["exact_tr"] == 155
    assert r["sources"] == {"merge_meta": 729, "declared_override": 1} and r["per_name"]["SPY"] == "exact_tr"


# ── R9 (2026-11-04): a merge-record label with NO frame is UNMEASURED, never taken on trust ──
#
# Found by the execution review of fa26a7b: the producer accepted `data_map=None`, skipped the
# stale-record witness and labelled every merge-record name anyway — 38 tests passed with the
# controller mutated to pass None. The ruled behaviour, built here: without the frame the name is
# UNLABELLED with the reason "UNWITNESSED … unmeasured", the record says `witness: "unmeasured"`
# and counts `n_unwitnessed`, and the gate fails the run under invariant 13 (10 on the cutover branch,
# renumbered at the merge onto main). The write record and
# a declared override describe the file itself and need no witness.

def test_R9_a_merge_record_label_with_NO_frames_is_UNWITNESSED_unmeasured_and_the_gate_fails(tmp_path):
    d = _cache(tmp_path, {"META": _entry(), "REC": _entry(), "OVR": _entry(case="alpaca_only")},
               records={"REC": {"convention": {"whole": "exact_tr"}}})
    conv = {**NO_CONV, "whole_file_overrides": {"OVR": {"convention": "exact_tr"}}}
    r = substrate_convention_record(d, run_names=["META", "REC", "OVR"], data_map=None, conventions=conv)
    assert r["witness"] == "unmeasured" and r["n_unwitnessed"] == 1
    assert r["per_name"] == {"REC": "exact_tr", "OVR": "exact_tr"}            # no witness needed
    assert list(r["unlabelled"]) == ["META"] and r["unlabelled"]["META"].startswith("UNWITNESSED")
    assert "data_map=None" in r["unlabelled"]["META"] and "unmeasured" in r["unlabelled"]["META"]
    v = _gate(r)
    assert not v.canonical and any("META" in f and "NO convention label" in f and "UNWITNESSED" in f
                                   for f in v.failures), v.failures
    # the positive control: the same name WITH its frame is labelled from the record, witnessed
    ok = substrate_convention_record(d, run_names=["META", "REC", "OVR"], data_map={"META": _frame()},
                                     conventions=conv, drip_witness=_witness(d, "META"))
    assert ok["per_name"]["META"] == "drip<2018-01-02|exact_tr" and ok["n_unwitnessed"] == 0
    assert ok["witness"] == "frames" and _gate(ok).canonical


def test_R9_a_name_whose_frame_is_ABSENT_from_the_given_frames_is_unwitnessed_too(tmp_path):
    """Frames were given, but not this name's: the per-name form of the same fail-open."""
    d = _cache(tmp_path, {"META": _entry(), "OTHER": _entry()})
    r = substrate_convention_record(d, run_names=["META", "OTHER"], data_map={"OTHER": _frame()},
                                    conventions=NO_CONV, drip_witness=_witness(d, "OTHER"))
    assert r["witness"] == "frames" and r["n_unwitnessed"] == 1 and r["per_name"] == {"OTHER": "drip<2018-01-02|exact_tr"}
    assert r["unlabelled"]["META"].startswith("UNWITNESSED") and "no frame in data_map" in r["unlabelled"]["META"]
    assert not _gate(r).canonical


def test_R9_a_cache_wide_label_is_witnessed_against_each_files_FIRST_bar(tmp_path):
    """`cache_first_bar_frames`: one-row frames at each csv's first bar; a name with no csv is absent
    (its merge-record label stays unwitnessed — fail closed), so the pass driver's `label` and the
    canonical data lock witness what a run would load."""
    d = _cache(tmp_path, {"EARLY": _entry(first="2000-01-03"), "LATE": _entry(first="2000-01-03"), "NOCSV": _entry()})
    (d / "EARLY_1d.csv").write_text("Date,Open,High,Low,Close,Volume\n1999-06-01,1,1,1,1,1\n1999-06-02,1,1,1,1,1\n")
    (d / "LATE_1d.csv").write_text("Date,Open,High,Low,Close,Volume\n2001-02-01,1,1,1,1,1\n")
    frames = cache_first_bar_frames(d)
    assert set(frames) == {"EARLY", "LATE"}
    assert frames["EARLY"].index[0] == pd.Timestamp("1999-06-01") and frames["LATE"].index[0] == pd.Timestamp("2001-02-01")
    r = substrate_convention_record(d, data_map=frames, conventions=NO_CONV, drip_witness=_witness(d, "LATE"))
    assert r["per_name"] == {"LATE": "drip<2018-01-02|exact_tr"}
    assert "STALE" in r["unlabelled"]["EARLY"]                      # the file starts before the record
    assert r["unlabelled"]["NOCSV"].startswith("UNWITNESSED") and r["n_unwitnessed"] == 1


def _call_keywords(path: Path, func: str, callee: str) -> set:
    """Keyword names of every call to `callee` inside function `func` (AST, never text). A keyword
    whose value is the constant `None` does NOT count — `data_map=None` was R's probe."""
    import ast
    tree = ast.parse(path.read_text())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func)
    kws = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and (getattr(n.func, "id", None) or getattr(n.func, "attr", None)) == callee:
            kws |= {k.arg for k in n.keywords
                    if not (isinstance(k.value, ast.Constant) and k.value.value is None)}
    return kws


def test_R9_every_caller_hands_the_label_its_frames():
    """Both census producers and the pass driver's `label` call the producer WITH `data_map=`
    (AST); the executed half is the backtest-producer lock above (`witness == "frames"`)."""
    root = Path(__file__).resolve().parents[1]
    assert "data_map" in _call_keywords(root / "backtester" / "backtest_controller.py", "_build_census",
                                        "substrate_convention_record")
    assert "data_map" in _call_keywords(root / "engines" / "engine_d_discovery" / "discovery.py",
                                        "candidate_census_block", "substrate_convention_record")
    assert "data_map" in _call_keywords(root / "scripts" / "cutover_step1_pass.py", "cmd_label",
                                        "substrate_convention_record")
