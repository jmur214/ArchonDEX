"""T-394 — locks on the wiring of the PINNED Tier-1 Stooq corrections into the cutover writer.

Pre-declared: `docs/Sources/proposal_era_tr_tier1_wiring_t394_2026-11-14.md` §1. The writer
(`tr_writer.era_tr_rewrite`) applies exactly the rows of a sha256-pinned table through
`era_tr.build_file(changes=…)`; Tier 2 is never applied and rides as a label in the write record and the census.
Each lock plants its case on the T-387 fixtures (a merged cache built with the merge's own functions) and was
proven by REVERSION (the source string named in its docstring).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engines.data_manager import era_tr as et
from engines.data_manager import stooq_tier1 as st1
from engines.data_manager import tr_writer as w

REPO = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fx = _load("_t387_fixtures_for_t394", "tests/test_era_tr_writer_t387.py")       # the planted world
TICKER, SEAM = fx.TICKER, fx.SEAM
STEP_DAY, BLOCK_A, BLOCK_B = "2016-11-10", "2017-08-14", "2017-08-15"
STEP, DELTA = -0.05, 0.004
ROWS = [{"ticker": TICKER, "kind": "spinoff_step", "date": STEP_DAY, "end_date": None, "log_amount": STEP},
        {"ticker": TICKER, "kind": "block", "date": BLOCK_A, "end_date": BLOCK_B, "log_amount": DELTA}]
TIER2 = {TICKER: {"n_steps": 1, "n_blocks": 2, "steps": ["2006-11-20"],
                  "blocks": [["2008-05-07", "2008-05-08"], ["2013-12-19", "2014-01-03"]]}}


@pytest.fixture(scope="module")
def planted():
    return fx._plant(seed=13, quarterly_yield=0.009, stooq_missed=False)


def table(rows=None, tier2=None, known=None) -> st1.Tier1Table:
    rows = ROWS if rows is None else rows
    return st1.Tier1Table(sha256="sha-of-the-test-table", rows={TICKER: list(rows)} if rows else {},
                          unverified_sha256="sha-of-the-test-labels", unverified=tier2 or {},
                          known_unapplied=known or {})


def _rewrite(tmp: Path, name: str, p, **kw):
    cache = fx._seed_merged_cache(tmp / name, p)
    return cache, fx._rewrite(cache, p, **kw)


# ── the shipped, pinned tables ─────────────────────────────────────────────────

def test_the_shipped_tables_match_their_pins_and_hold_exactly_the_eleven_rows():
    t = st1.load_tier1()
    assert t.sha256 == st1.TIER1_SHA256 and t.unverified_sha256 == st1.UNVERIFIED_SHA256
    got = sorted((k, r["date"], r["kind"]) for k, v in t.rows.items() for r in v)
    assert got == [("APD", "2016-10-03", "spinoff_step"), ("CAG", "2016-11-10", "spinoff_step"),
                   ("DOC", "2016-11-01", "spinoff_step"), ("HLT", "2017-01-04", "spinoff_step"),
                   ("HON", "2018-10-29", "spinoff_step"), ("HPE", "2017-04-03", "spinoff_step"),
                   ("HPE", "2017-09-01", "spinoff_step"), ("IBM", "2019-08-12", "block"),
                   ("KG", "2018-02-12", "block"), ("MRK", "2019-08-12", "block"), ("TJX", "2019-08-12", "block")]
    for rows in t.rows.values():                       # each row carries T-265's own measurement beside it
        for r in rows:
            assert abs(r["t265_log_amount"] - r["log_amount"]) <= 0.25 * abs(r["log_amount"])
    lab = json.loads(st1.UNVERIFIED_PATH.read_text())
    assert lab["n_rows"] == 1579 and lab["n_files"] == 374 == len(t.unverified)
    assert sum(v["n_steps"] + v["n_blocks"] for v in t.unverified.values()) == 1579
    assert sorted(t.known_unapplied) == ["APD", "GE", "HON"]
    assert not (set(k for k, v in t.rows.items()) & {"DHR", "ETN", "XRX"})      # no row on a guard-changed file


def test_a_tampered_table_or_label_file_is_refused(tmp_path):
    """Reversion: `if got != want:` → `if False:` in stooq_tier1.load_tier1."""
    doc = json.loads(st1.TIER1_PATH.read_text())
    doc["rows"][0]["log_amount"] *= 1.01                # one amount nudged by 1 %
    bad = tmp_path / "tier1.json"
    bad.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    with pytest.raises(st1.StooqTier1Refusal, match="not the pinned"):
        st1.load_tier1(path=bad)
    lab = tmp_path / "labels.json"
    lab.write_text(st1.UNVERIFIED_PATH.read_text().replace('"n_rows": 1579', '"n_rows": 1578'))
    with pytest.raises(st1.StooqTier1Refusal, match="not the pinned"):
        st1.load_tier1(unverified_path=lab)
    with pytest.raises(st1.StooqTier1Refusal, match="absent"):
        st1.load_tier1(path=tmp_path / "nope.json")


def test_a_table_with_a_duplicate_row_or_the_wrong_count_is_refused(tmp_path):
    """Reversion: `if key in seen:` → `if False:` (the duplicate then slips to the count check: the message differs)."""
    doc = json.loads(st1.TIER1_PATH.read_text())
    dup = dict(doc, rows=doc["rows"][:-1] + [doc["rows"][0]])
    p = tmp_path / "dup.json"
    p.write_text(json.dumps(dup))
    with pytest.raises(st1.StooqTier1Refusal, match="two rows for one file and date"):
        st1.load_tier1(path=p, expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    short = tmp_path / "short.json"
    short.write_text(json.dumps(dict(doc, rows=doc["rows"][:-1])))
    with pytest.raises(st1.StooqTier1Refusal, match="10 rows, not 11"):
        st1.load_tier1(path=short, expected_sha256=hashlib.sha256(short.read_bytes()).hexdigest())


# ── the rows are applied exactly ──────────────────────────────────────────────

def test_the_rows_are_applied_exactly_and_recorded(tmp_path, planted):
    """A step and a block on a clean file: every bar before the step × exp(s), the block's bars × exp(−δ) more,
    nothing else — to the bit of "the (a′) bytes read back and corrected".
    Reversions: `vals[:n_pre] = vals[:n_pre] * corr` → `vals[:n_pre] = vals[:n_pre] * 1.0` (the audit then refuses);
    `np.add.at(expected, cpos, changes.to_numpy(dtype=float))` → `… 0 * changes.to_numpy(dtype=float))` (the step
    audit no longer absorbs the changes and refuses a correct write)."""
    base_dir, _ = _rewrite(tmp_path, "v5", planted)
    cache, rec = _rewrite(tmp_path, "t1", planted, stooq_corrections=table())
    base, got = fx._closes(base_dir), fx._closes(cache)
    pre = base.index < SEAM
    changes = st1.changes_for_file(TICKER, ROWS, base.index, SEAM)
    want = base.to_numpy().copy()
    want[pre] = want[pre] * et.correction_factor(base.index[pre], SEAM, changes)
    assert np.array_equal(got.to_numpy(), want)                             # bit-identical
    ratio = np.log(got / base)
    step_day, a, b = pd.Timestamp(STEP_DAY), pd.Timestamp(BLOCK_A), pd.Timestamp(BLOCK_B)
    assert np.allclose(ratio[ratio.index < step_day], STEP, atol=1e-12)
    assert np.allclose(ratio[(ratio.index >= step_day) & (ratio.index < a)], 0.0, atol=1e-12)
    assert np.allclose(ratio[(ratio.index >= a) & (ratio.index < b)], -DELTA, atol=1e-12)
    assert np.allclose(ratio[ratio.index >= b], 0.0, atol=1e-12)
    block = rec["era_tr"]
    assert block["stooq_corrections"] == {"table_sha256": "sha-of-the-test-table", "tier": "1", "applied": ROWS}
    assert block["rails"]["step_audit"]["pass"] and block["rails"]["step_audit"]["n_correction_steps"] == 3
    assert block["rails"]["splice_audit"]["pass"]
    post = lambda d: [ln for ln in fx._lines(d) if ln[:10] >= str(SEAM.date())]         # noqa: E731
    assert [ln.split(",")[:6] for ln in post(cache)] == [ln.split(",")[:6] for ln in post(base_dir)]


def test_no_table_writes_v5_and_says_the_label_was_not_recorded(tmp_path, planted):
    """Reversion: `if stooq_corrections is not None else None)}` → `… else {})}` (a file written without the
    table would then read as "nothing unverified")."""
    base_dir, rec = _rewrite(tmp_path, "v5", planted)
    block = rec["era_tr"]
    assert block["stooq_corrections"]["applied"] == [] and block["stooq_corrections"]["table_sha256"] is None
    assert block["unverified_stooq_corrections"] is None
    census = fx._label(base_dir)
    assert census["n_stooq_label_not_recorded"] == 1 and census["n_unverified_stooq_corrections"] == 0
    assert census["stooq_corrections"][TICKER]["recorded"] is False


# ── refusals ───────────────────────────────────────────────────────────────────

def _refused(tmp_path, planted, rows, match):
    cache = fx._seed_merged_cache(tmp_path / "c", planted)
    before = (cache / f"{TICKER}_1d.csv").read_bytes()
    with pytest.raises(w.WriterRefusal, match=match):
        fx._rewrite(cache, planted, stooq_corrections=table(rows))
    assert (cache / f"{TICKER}_1d.csv").read_bytes() == before                # nothing written
    assert not (cache / w.WRITE_RECORDS_DIR / f"{TICKER}.json").exists()


def test_a_row_on_or_after_the_seam_is_refused(tmp_path, planted):
    """Reversion: `if d >= seam:` → `if False:` in stooq_tier1.changes_for_file (the row would then be recorded as
    applied while moving nothing)."""
    _refused(tmp_path, planted, [dict(ROWS[0], date="2018-03-01")], "on or after the seam")


def test_a_block_that_ends_after_the_seam_is_refused(tmp_path, planted):
    """Reversion: `if b > seam or b <= d:` → `if b <= d:`."""
    _refused(tmp_path, planted, [dict(ROWS[1], date="2017-12-28", end_date="2018-01-04")], "after the seam")


def test_a_row_whose_date_is_not_a_bar_of_the_file_is_refused(tmp_path, planted):
    """Reversion: `if pos < 0:` → `if False:` (the change would land on the next bar)."""
    _refused(tmp_path, planted, [dict(ROWS[0], date="2016-11-12")], "not a bar of the file")       # a Saturday


def test_a_row_naming_a_file_the_copy_does_not_have_is_refused_before_any_write(tmp_path, planted, monkeypatch):
    """Reversion: `if missing:` → `if False:` in stooq_tier1.check_universe."""
    with pytest.raises(st1.StooqTier1Refusal, match="not merged files with pre-seam bars"):
        st1.check_universe(table(), ["AAPL", "MSFT"])
    st1.check_universe(table(), [TICKER, "AAPL"])
    # the DRIVER: the pinned table names ten real files; a copy that holds only the planted one is refused …
    monkeypatch.setattr(fx.cs, "CANDIDATES_ROOT", tmp_path)       # the driver only writes under the candidates root
    copy = fx._seed_merged_cache(tmp_path / "copy_of_canonical", planted)
    yf = tmp_path / "yf"
    yf.mkdir()
    (yf / "_fetch_log.jsonl").write_text(json.dumps({"ticker": TICKER, "prices": "no_data"}) + "\n")
    raw = tmp_path / "raw"
    raw.mkdir()
    argv = ["era-tr", "--copy", str(copy), "--yf-dir", str(yf), "--raw-stooq", str(raw), "--yf-manifest", "none",
            "--dry-run", "--out-dir", str(tmp_path / "rows")]
    with pytest.raises(SystemExit, match="REFUSED: Tier-1 rows name files"):
        fx.cs.main(argv)
    # … and the refusal is the table's: without it the same command runs (the positive control)
    assert fx.cs.main(argv + ["--stooq-corrections", "none"]) in (0, 2)


def test_a_row_at_an_ex_date_the_guard_touched_is_refused(tmp_path, planted, monkeypatch):
    """The guard and the table must never both act on one event (none does today).
    Reversion: `pd.DatetimeIndex(frame["Date"]), seam, guard_days)` → `…, seam, None)` in tr_writer.era_tr_rewrite."""
    real = et.analyse_reference

    def with_a_refused_ex_date(*a, **k):
        ref = real(*a, **k)
        lab = ref.labels.copy()
        i = int(np.argmin(np.abs((pd.DatetimeIndex(lab["day"]) - pd.Timestamp(STEP_DAY)).days)))
        lab.loc[lab.index[i], "refused"] = True
        ref.labels = lab
        return ref

    monkeypatch.setattr(et, "analyse_reference", with_a_refused_ex_date)
    day = str(pd.Timestamp(planted.divs.index[np.argmin(np.abs((planted.divs.index - pd.Timestamp(STEP_DAY)).days))]).date())
    _refused(tmp_path, planted, [dict(ROWS[0], date=day)], "guard refused or repaired")
    # the unit rule: three bars either side
    dates = pd.bdate_range("2016-01-04", periods=40)
    with pytest.raises(st1.StooqTier1Refusal):
        st1.changes_for_file("X", [dict(ROWS[0], date=str(dates[13].date()))], dates, dates[-1], dates[[10]])
    assert len(st1.changes_for_file("X", [dict(ROWS[0], date=str(dates[14].date()))], dates, dates[-1], dates[[10]])) == 1


# ── Tier 2 is a label, never applied ───────────────────────────────────────────

def test_tier_2_is_never_applied_and_rides_in_the_record_and_the_census(tmp_path, planted):
    """A file with Tier-2 entries and no Tier-1 row is written as v5, byte for byte, and LABELLED.
    Reversions: `"unverified_stooq_corrections": (stooq_corrections.unverified_for(ticker)` → `… (None` in
    tr_writer (the record loses the label); `out["stooq"] = stooq_corrections_label(block)` → `out["stooq"] = None`
    in convention._resolve (the census loses it)."""
    base_dir, _ = _rewrite(tmp_path, "v5", planted)
    known = {TICKER: [{"date": "2019-02-26", "what": "a known omission"}]}
    cache, rec = _rewrite(tmp_path, "t2", planted, stooq_corrections=table(rows=[], tier2=TIER2, known=known))
    assert (cache / f"{TICKER}_1d.csv").read_bytes() == (base_dir / f"{TICKER}_1d.csv").read_bytes()
    lab = rec["era_tr"]["unverified_stooq_corrections"]
    assert (lab["n_steps"], lab["n_blocks"]) == (1, 2) and lab["blocks"][1] == ["2013-12-19", "2014-01-03"]
    assert lab["known_unapplied"] == known[TICKER] and "NOT applied" in lab["meaning"]
    assert rec["era_tr"]["stooq_corrections"]["applied"] == [] and rec["era_tr"]["stooq_correction_changes"] == []
    assert fx._record(cache)["era_tr"]["unverified_stooq_corrections"] == lab          # as written to disk
    census = fx._label(cache)
    assert census["n_unverified_stooq_corrections"] == 1 and census["n_stooq_tier1_applied"] == 0
    assert census["stooq_corrections"][TICKER] == {"tier1_applied": 0, "recorded": True, "n_steps": 1, "n_blocks": 2,
                                                   "n_known_unapplied": 1, "table_sha256": "sha-of-the-test-table"}
    cache1, _ = _rewrite(tmp_path, "t1", planted, stooq_corrections=table(tier2=TIER2))
    c1 = fx._label(cache1)
    assert c1["n_stooq_tier1_applied"] == 1 and c1["n_stooq_tier1_rows"] == 2 and c1["n_stooq_label_not_recorded"] == 0


def test_the_rewrite_with_the_table_still_never_runs_twice(tmp_path, planted):
    cache, _ = _rewrite(tmp_path, "t1", planted, stooq_corrections=table())
    once = (cache / f"{TICKER}_1d.csv").read_bytes()
    with pytest.raises(w.WriterRefusal, match="not 'drip'"):
        fx._rewrite(cache, planted, stooq_corrections=table())
    assert (cache / f"{TICKER}_1d.csv").read_bytes() == once


def test_no_changes_is_exactly_the_a_prime_factor():
    dates = pd.bdate_range("2017-01-02", periods=30)
    assert (et.correction_factor(dates, dates[-1] + pd.Timedelta(days=3), None) == 1.0).all()
    assert (et.correction_factor(dates, dates[-1] + pd.Timedelta(days=3), pd.Series(dtype=float)) == 1.0).all()


# ── the declared bytes, on the real files ──────────────────────────────────────

BYTES = REPO / "config" / "era_tr_tier1_bytes_t394.json"
V4 = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_v4_2026_11_11")


def test_the_declared_bytes_name_the_ten_files_of_the_eleven_rows():
    d = json.loads(BYTES.read_text())
    t = st1.load_tier1()
    assert sorted(d["changed"]) == sorted(t.rows) and len(d["changed"]) == 10
    assert d["table_sha256"] == st1.TIER1_SHA256 and d["files"] == 575 and d["equal_to_v5"] == 565
    for row in d["changed"].values():
        assert row["v5_md5"] != row["tier1_md5"]


@pytest.mark.skipif(not (V4 / "MANIFEST.md5").exists(), reason="the v4 candidate is not on this machine")
def test_the_build_reproduces_the_declared_bytes_on_real_files():
    """HPE (two steps), IBM (a block) and APD equal T-390's own v5 + Tier 1 render; KO and DHR equal v5.
    Reversion: `corr = correction_factor(pre_dates, seam, changes) if …` folded into `factor` (one multiplication)
    changes the last bits and breaks the identity — see the proposal §1.3."""
    from scripts import drip_fix_candidate_t384 as t384
    d = json.loads(BYTES.read_text())
    v5 = json.loads((REPO / "config" / "era_tr_v5_delta_t393.json").read_text())["changed"]
    v4_md5 = {ln.split("  ", 1)[1]: ln.split("  ", 1)[0] for ln in (V4 / "MANIFEST.md5").read_text().splitlines()}
    table_, meta, raw_idx = st1.load_tier1(), t384.load_meta(), t384.raw_stooq_index()
    yf = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_2026_11_11/yf")
    for t in ("HPE", "IBM", "APD", "KO", "DHR"):
        seam = pd.Timestamp(meta[t]["seam_date"])
        raw = et.read_raw_stooq(raw_idx[t])
        px, dv = et.read_yf(t, yf)
        ref = et.analyse_reference(t, raw, px, dv, seam)
        header, lines = t384.read_cache_text(t)
        frame = t384.read_cache_frame(t)
        rows = table_.rows_for(t)
        guard = pd.DatetimeIndex(ref.labels.loc[ref.labels["refused"].to_numpy(dtype=bool), "day"]) if len(ref.labels) else None
        changes = st1.changes_for_file(t, rows, pd.DatetimeIndex(frame["Date"]), seam, guard) if rows else None
        got = hashlib.md5(et.build_file(t, meta[t], header, lines, frame, raw, ref, changes=changes).text.encode()).hexdigest()
        want = d["changed"][t]["tier1_md5"] if t in d["changed"] else (
            v5[t]["v5_md5"] if t in v5 else v4_md5[f"processed/{t}_1d.csv"])
        assert got == want, t
