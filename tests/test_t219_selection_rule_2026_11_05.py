"""The T-219 cap-at-delist SELECTION RULE (owed before re-pin #2; the execution reviewer's F1 of
2026-11-05) — what `--from-snapshot` WRITES and what it SKIPS, with the reason.

The defect it closes (measured at D1, docs/Measurements/2026-11/repin1_d1_shares_snapshot_recompute_diff
_2026-11-05.md): `cap_at_delist` keys its 12-month window on the price file's LAST BAR, so for a name
that still trades it is a trailing median, not a cap at leaving the index — the bare recompute would
have replaced the 55 cohort names carrying a current-snapshot cap and moved the 8 still-trading
`delist_shares` entries by ≤ 1.5%. June's `main()` skipped names already carrying a cap; the rewrite
had dropped that.

The rule (scripts/build_pit_cap_history_t219.py, module docstring): a name is written only when
  (2) its current entry may be overwritten — absent, `source == "delist_shares"`, or a NULL placeholder
      (no cap to keep); a cap with no `source` is a current-snapshot cap, kept byte-for-byte
      (reason `current_snapshot_kept`; checked FIRST — rule 2 wins over rule 1); AND
  (1) the cache says it is delisted — its last bar is STRICTLY before `cache_end` − 5 trading days,
      `cache_end` = the last-bar date shared by the MAJORITY of the price files (reason `still_trading`
      otherwise).

Every lock drives the real `main()` / `recompute_from_snapshot` on a planted checkout under tmp_path
(`--root`); yfinance is a stub whose Ticker RAISES, installed for every test (the C4 idiom). Nothing
writes under data/: the real-data test reads the pinned files read-only and writes to tmp_path. The
two POSITIVE CONTROLS revert one rule each in-process and show the matching lock's subject flips.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

from scripts import build_pit_cap_history_t219 as t219

REPO = Path(__file__).resolve().parent.parent
CACHE_END = pd.Timestamp("2022-12-30")        # the planted cache's bulk end (a Friday)
BOUND = pd.Timestamp("2022-12-23")            # CACHE_END − 5 business days: delisted = last bar BEFORE this
DELISTED_END = pd.Timestamp("2021-11-25")     # 400 days before CACHE_END
SHARES = 1e9                                  # every planted series; Close 10.0 → cap 1e10 → "large"

# the planted tiers file: what the recompute finds
CURRENT = {
    "BIGCO": {"marketCap": 3e12, "tier": "mega"},                                            # live, not in the snapshot
    "TRD": {"marketCap": 1.0, "tier": "micro", "asof": "2021-01-01", "source": "delist_shares"},  # still trades, our own
    "EAR": {"marketCap": 5e9, "tier": "mid"},                                                # live, file ends early
    "DCS": {"marketCap": 7e9, "tier": "mid"},                                                # delisted, current-snapshot cap
    "NUL": {"marketCap": None, "tier": None},                                                # the T-210 null placeholder
    "KEP": {"marketCap": 2e9, "tier": "mid", "asof": "2026-06-18", "source": "delist_shares"},   # ours; snapshot lacks it
}
# the planted price files: name → last bar (every file starts 2019-01-01)
ENDS = {
    "SPY": CACHE_END, "LV1": CACHE_END, "LV2": CACHE_END, "LV3": CACHE_END, "LV4": CACHE_END,
    "LV5": CACHE_END, "LV6": CACHE_END, "LV7": CACHE_END,            # the bulk: 8 live files
    "TRD": CACHE_END,                                                # still trading, ends with the bulk
    "DEL": DELISTED_END,                                             # delisted, no entry
    "EAR": pd.Timestamp("2022-06-30"),                               # live name whose file ends early
    "DCS": DELISTED_END,                                             # delisted, current-snapshot cap
    "NUL": DELISTED_END,                                             # delisted, null placeholder
    "ATB": BOUND,                                                    # ends AT the bound: not strictly before
    "BLB": pd.Timestamp("2022-12-22"),                               # one trading day before the bound
    "WAL": DELISTED_END,                                             # delisted; the snapshot has no overlap
}
SNAPSHOT_NAMES = ("TRD", "DEL", "EAR", "DCS", "NUL", "ATB", "BLB", "WAL", "NPF")   # NPF has no price file


@pytest.fixture(autouse=True)
def _yfinance_must_never_be_constructed(monkeypatch):
    stub = types.ModuleType("yfinance")

    class Ticker:
        def __init__(self, t):
            raise AssertionError(f"yfinance.Ticker({t!r}) constructed on --from-snapshot, which must never fetch")
    stub.Ticker = Ticker
    monkeypatch.setitem(sys.modules, "yfinance", stub)


def _csv(root: Path, t: str, end: pd.Timestamp, close: float = 10.0) -> None:
    days = pd.bdate_range("2019-01-01", end)
    pd.DataFrame({"Date": days, "Open": close, "Close": close, "Volume": 1}).to_csv(
        root / f"data/processed/{t}_1d.csv", index=False)


def _plant(tmp_path: Path) -> tuple:
    """The checkout, the snapshot path and the planted tiers TEXT (for byte comparisons)."""
    root = tmp_path / "root"
    (root / "data/universe").mkdir(parents=True)
    (root / "data/processed").mkdir(parents=True)
    for t, end in ENDS.items():
        _csv(root, t, end)
    text = json.dumps(CURRENT, indent=0)
    (root / t219.TIERS_REL).write_text(text)
    rows = []
    for t in SNAPSHOT_NAMES:
        if t == "WAL":
            rows.append((t, pd.Timestamp("2012-01-01"), 7e7))          # before any bar: no overlap
        else:
            rows += [(t, pd.Timestamp("2019-01-02"), SHARES), (t, CACHE_END, SHARES)]
    snap = tmp_path / "delist_shares_snapshot.parquet"
    pd.DataFrame(rows, columns=["ticker", "date", "shares"]).to_parquet(snap, index=False)
    return root, snap, text


def _run(tmp_path: Path, capsys) -> tuple:
    """The real main() to an explicit --out: (new tiers, stdout, the planted tiers text, root)."""
    root, snap, text = _plant(tmp_path)
    out = tmp_path / "out" / "tiers.json"
    rc = t219.main(["--from-snapshot", str(snap), "--root", str(root), "--out", str(out)])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert (root / t219.TIERS_REL).read_text() == text, "the checkout's tiers file was written"
    return json.loads(out.read_text()), captured.out, out.read_text(), root


def _entry_text(text: str, t: str) -> str:
    """The entry's own serialization inside a tiers file written with indent=0."""
    m = re.search(rf'"{t}": \{{[^}}]*\}}', text)
    assert m, f"{t} not in the file"
    return m.group(0)


def _written(t: str, asof: pd.Timestamp) -> dict:
    return {"marketCap": 10.0 * SHARES, "tier": "large", "asof": str(asof.date()), "source": "delist_shares"}


# ═══════════════════════════════════════════════════════════════════════════════
# the locks
# ═══════════════════════════════════════════════════════════════════════════════

def test_LOCK_a_delisted_name_with_no_entry_is_WRITTEN_with_source_delist_shares(tmp_path, capsys):
    new, out, _, _ = _run(tmp_path, capsys)
    assert new["DEL"] == _written("DEL", DELISTED_END)
    assert "written (3): BLB, DEL, NUL" in out


def test_LOCK_a_still_trading_name_owning_a_delist_shares_entry_is_SKIPPED_still_trading_and_unchanged(tmp_path, capsys):
    """TRD's file ends WITH the bulk; its entry is this script's own (source delist_shares) and would
    be rewritten as a trailing median — rule (1) refuses: a name the cache still trades is not at
    its delisting. The 8 real names of D1 (JEF, KBH, KMX, LW, NWL, RRC, SE, SUN) are this case."""
    new, out, out_text, _ = _run(tmp_path, capsys)
    assert new["TRD"] == CURRENT["TRD"]
    assert _entry_text(out_text, "TRD") == _entry_text(json.dumps(CURRENT, indent=0), "TRD")
    assert "skipped still_trading (2): ATB, TRD" in out


def test_LOCK_an_early_ending_live_name_with_a_current_snapshot_cap_is_SKIPPED_current_snapshot_kept_byte_unchanged(
        tmp_path, capsys):
    """EAR's file ends six months before the bulk (the baked-at-write-time class: a LIVE name whose
    file ends early) — rule (1) alone would call it delisted. Its entry carries a cap and no
    `source`: the T-210/T-215 current-snapshot shape. Rule (2) keeps it, byte for byte."""
    new, out, out_text, _ = _run(tmp_path, capsys)
    assert new["EAR"] == CURRENT["EAR"] and "source" not in new["EAR"]
    assert _entry_text(out_text, "EAR") == _entry_text(json.dumps(CURRENT, indent=0), "EAR")
    assert "skipped current_snapshot_kept (2): DCS, EAR" in out


def test_LOCK_a_delisted_name_with_a_current_snapshot_cap_is_SKIPPED_rule_2_wins(tmp_path, capsys):
    """DCS is delisted by the cache (its file ends 400 days before the bulk) AND carries a
    current-snapshot cap. Rule (2) wins: a current-snapshot cap is NEVER replaced by this script,
    whatever the cache says — the reason is `current_snapshot_kept`, never `still_trading`, and the
    entry is byte-unchanged. (The 55 real names of D1 are this case or EAR's.)"""
    new, out, out_text, _ = _run(tmp_path, capsys)
    assert new["DCS"] == CURRENT["DCS"]
    assert _entry_text(out_text, "DCS") == _entry_text(json.dumps(CURRENT, indent=0), "DCS")
    assert "DCS" in out.split("skipped current_snapshot_kept")[1].split("\n")[0]
    assert "DCS" not in out.split("skipped still_trading")[1].split("\n")[0]


def test_LOCK_stats_counts_and_reason_lists_are_exact_and_resolved_equals_written(tmp_path, capsys):
    root, snap, _ = _plant(tmp_path)
    new, stats = t219.recompute_from_snapshot(snap, root=root)
    counts = {k: v for k, v in stats.items() if not isinstance(v, list)}
    assert counts == {
        "snapshot_names": 9, "resolved": 3, "wall": 1, "no_price_file": 1,
        "skipped_still_trading": 2, "skipped_current_snapshot_kept": 2,
        "changed_vs_current": 1, "new_vs_current": 2, "kept_absent_from_snapshot": 1,
        "cache_end": "2022-12-30", "cache_end_files": "9/16", "delisted_bound": "2022-12-23", "tolerance_bdays": 5}
    assert stats["written_names"] == ["BLB", "DEL", "NUL"]
    assert stats["skipped_still_trading_names"] == ["ATB", "TRD"]
    assert stats["skipped_current_snapshot_kept_names"] == ["DCS", "EAR"]
    assert stats["wall_names"] == ["WAL"] and stats["no_price_file_names"] == ["NPF"]
    assert stats["kept_absent_from_snapshot_names"] == ["KEP"]
    assert stats["resolved"] == len(stats["written_names"]) == sum(1 for t in new if t not in CURRENT or new[t] != CURRENT[t])
    assert (stats["resolved"] + stats["wall"] + stats["no_price_file"] + stats["skipped_still_trading"]
            + stats["skipped_current_snapshot_kept"]) == stats["snapshot_names"]
    assert stats["changed_vs_current"] + stats["new_vs_current"] == stats["resolved"] - 0   # every write here differs


def test_the_delisted_bound_is_STRICT_at_five_trading_days(tmp_path, capsys):
    """ATB ends exactly at cache_end − 5 trading days: at the bound is still trading. BLB ends one
    trading day earlier: delisted, written."""
    new, out, _, _ = _run(tmp_path, capsys)
    assert "ATB" not in new and new["BLB"] == _written("BLB", pd.Timestamp("2022-12-22"))
    assert t219.CACHE_END_TOLERANCE_BDAYS == 5
    assert t219.delisted_by_cache(BOUND, CACHE_END) is False
    assert t219.delisted_by_cache(BOUND - pd.offsets.BDay(), CACHE_END) is True
    assert t219.delisted_by_cache(CACHE_END, CACHE_END) is False
    assert t219.delisted_by_cache(CACHE_END + pd.offsets.BDay(3), CACHE_END) is False   # ends AFTER the bulk: trading


def test_a_null_placeholder_entry_carries_no_cap_and_is_overwritten_as_June_did(tmp_path, capsys):
    """June's `main()` took a name as unresolved when `not entry.get("marketCap")` — a null
    placeholder (the T-210 ADV-fallback shape) was what T-219 exists to fill. Rule (2) keeps that."""
    new, _, _, _ = _run(tmp_path, capsys)
    assert new["NUL"] == _written("NUL", DELISTED_END)
    assert t219.may_overwrite(None) and t219.may_overwrite({}) and t219.may_overwrite({"marketCap": None, "tier": None})
    assert t219.may_overwrite({"marketCap": 1.0, "tier": "micro", "source": "delist_shares"})
    assert not t219.may_overwrite({"marketCap": 5e9, "tier": "mid"})
    assert not t219.may_overwrite({"marketCap": 5e9, "tier": "mid", "source": "fast_info"})   # not ours, has a cap


def test_cache_end_is_the_MAJORITY_last_bar_with_the_evidence_both_ways_and_refuses_without_one(tmp_path, capsys):
    """The literal maximum is refuted on the real cache (five files end after the bulk); SPY is itself
    an early-ender there. The majority date is the bulk refresh; its share, the latest end and its
    holders, and SPY's own last bar are all returned. A tie takes the EARLIER date (fewer names classed
    delisted). Below 50% — or with no files — the cache has no end: CacheEndUnresolved, exit 2."""
    d = pd.Timestamp
    ends = {"A": d("2026-04-24"), "B": d("2026-04-24"), "C": d("2026-04-24"), "SPY": d("2026-04-17"),
            "AGG": d("2026-05-21"), "X": d("2021-01-05")}
    ce = t219.cache_end_from(ends)
    assert ce["cache_end"] == d("2026-04-24") and ce["n_at_end"] == 3 and ce["n_files"] == 6 and ce["share"] == 0.5
    assert ce["latest_end"] == d("2026-05-21") and ce["latest_names"] == ["AGG"]
    assert ce["reference"] == "SPY" and ce["reference_last_bar"] == d("2026-04-17")
    assert ce["delisted_bound"] == d("2026-04-17") and ce["tolerance_bdays"] == 5
    tie = t219.cache_end_from({"A": d("2026-04-24"), "B": d("2026-04-17")})
    assert tie["cache_end"] == d("2026-04-17")
    assert t219.cache_end_from({"A": d("2026-04-24")})["reference_last_bar"] is None
    with pytest.raises(t219.CacheEndUnresolved, match="no last-bar date is shared by 50%"):
        t219.cache_end_from({"A": d("2026-04-24"), "B": d("2026-04-17"), "C": d("2026-04-10")})
    with pytest.raises(t219.CacheEndUnresolved, match="no \\*_1d.csv"):
        t219.cache_end_from({})
    # the real main() on a cache without a majority: exit 2, nothing written, the reason on stderr
    root = tmp_path / "root"
    (root / "data/universe").mkdir(parents=True)
    (root / "data/processed").mkdir(parents=True)
    for t, end in (("A", "2022-12-30"), ("B", "2022-06-30"), ("C", "2021-11-25")):
        _csv(root, t, d(end))
    (root / t219.TIERS_REL).write_text("{}")
    snap = tmp_path / "s.parquet"
    pd.DataFrame({"ticker": ["A"], "date": [d("2019-01-02")], "shares": [1e9]}).to_parquet(snap, index=False)
    out = tmp_path / "never.json"
    assert t219.main(["--from-snapshot", str(snap), "--root", str(root), "--out", str(out)]) == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err and "no established end" in err and not out.exists()


def test_names_the_snapshot_lacks_stay_as_they_are_and_our_own_are_counted(tmp_path, capsys):
    new, out, out_text, _ = _run(tmp_path, capsys)
    assert new["KEP"] == CURRENT["KEP"] and new["BIGCO"] == CURRENT["BIGCO"]
    assert "kept, absent from the snapshot (1): KEP" in out
    assert "delist_shares entries in the output: 5 = written 3 + carried 2" in out     # KEP + TRD
    assert list(new) == list(CURRENT) + ["BLB", "DEL"]                                 # order kept; new names appended


def test_a_price_file_whose_last_line_is_not_a_dated_bar_HALTS_the_recompute_naming_it(tmp_path):
    root, snap, _ = _plant(tmp_path)
    (root / "data/processed/BAD_1d.csv").write_text("Date,Open,Close,Volume\n")          # header only
    with pytest.raises(ValueError, match="BAD_1d.csv.*not a dated bar"):
        t219.recompute_from_snapshot(snap, root=root)
    assert t219.last_bar_date(root / "data/processed/DEL_1d.csv") == DELISTED_END
    # an unsorted file: the tail read is proven against the loaded frame for every name that is loaded
    days = pd.bdate_range("2019-01-01", DELISTED_END)
    pd.DataFrame({"Date": days[::-1], "Open": 10.0, "Close": 10.0, "Volume": 1}).to_csv(
        root / "data/processed/DEL_1d.csv", index=False)
    (root / "data/processed/BAD_1d.csv").write_text("Date,Open,Close,Volume\n2019-01-02,1,1,1\n")
    with pytest.raises(ValueError, match="DEL: the file's last line .* is not its latest bar"):
        t219.recompute_from_snapshot(snap, root=root)


# ═══════════════════════════════════════════════════════════════════════════════
# the REAL-DATA first artifact: on the pinned pair (cache, tiers) the recompute is the identity
# ═══════════════════════════════════════════════════════════════════════════════

PINNED_SNAPSHOT = REPO / "data/universe/delist_shares_snapshot.parquet"
PINNED_TIERS = REPO / t219.TIERS_REL


def test_REAL_DATA_the_recompute_on_the_pinned_snapshot_EQUALS_the_pinned_tiers_file(tmp_path, capsys):
    """The rule's invariant on an UNCHANGED cache: `--from-snapshot` on the pinned snapshot reproduces
    `data/universe/market_cap_tiers.json` exactly (json-equal: 0 changed, 0 new) — every one of D1's
    55 + 8 is skipped, and what is written rewrites identically. The pinned files are read through
    the checkout's data/ (read-only: their bytes are asserted unchanged); the output goes to tmp_path.
    NOT a cutover detector: the identity also holds on the step-1 cutover copy (the next test) —
    the writer writes only what the provider serves, so what it wrote ends at the bulk (kept) and
    what it did not write is June's input (rewritten identically). Skipped where the pinned files
    are not on the host."""
    missing = [p for p in (PINNED_SNAPSHOT, PINNED_TIERS) if not p.is_file()]
    if missing:
        pytest.skip(f"the pinned T-219 files are not on this host: {[str(p) for p in missing]}")
    if not list((REPO / "data/processed").glob("*_1d.csv")):
        pytest.skip("no price cache on this host")
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (PINNED_SNAPSHOT, PINNED_TIERS)}
    out = tmp_path / "market_cap_tiers_recomputed.json"
    rc = t219.main(["--from-snapshot", str(PINNED_SNAPSHOT), "--out", str(out)])
    printed = capsys.readouterr().out
    assert rc == 0, printed
    pinned = json.loads(PINNED_TIERS.read_text())
    recomputed = json.loads(out.read_text())
    _, stats = t219.recompute_from_snapshot(PINNED_SNAPSHOT, root=REPO)
    counts = {k: v for k, v in stats.items() if not isinstance(v, list)}
    print(f"\n[REAL DATA] {counts}")
    print(f"[REAL DATA] written: {stats['written_names']}")
    print(f"[REAL DATA] kept, absent from the snapshot: {stats['kept_absent_from_snapshot_names']}")
    print(f"[REAL DATA] wall: {stats['wall_names']}")
    differ = sorted(t for t in set(pinned) | set(recomputed) if pinned.get(t) != recomputed.get(t))
    assert differ == [], f"{len(differ)} entries differ from the pinned tiers file: {differ[:20]}"
    assert recomputed == pinned and list(recomputed) == list(pinned)
    assert stats["changed_vs_current"] == 0 and stats["new_vs_current"] == 0
    assert stats["resolved"] == len(stats["written_names"])
    assert (stats["resolved"] + stats["wall"] + stats["no_price_file"] + stats["skipped_still_trading"]
            + stats["skipped_current_snapshot_kept"]) == stats["snapshot_names"]
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before} == before, "a pinned file CHANGED"


# ═══════════════════════════════════════════════════════════════════════════════
# POSITIVE CONTROLS — each rule reverted in-process flips the subject of its lock
# ═══════════════════════════════════════════════════════════════════════════════

def test_POSITIVE_CONTROL_reverting_rule_1_WRITES_the_still_trading_name(tmp_path, capsys, monkeypatch):
    """With `delisted_by_cache` always True (the bare D1 recompute), TRD — still trading, our own
    entry — is rewritten as a trailing median: the still_trading lock's subject flips."""
    monkeypatch.setattr(t219, "delisted_by_cache", lambda last_bar, cache_end, tolerance_bdays=5: True)
    new, out, _, _ = _run(tmp_path, capsys)
    assert new["TRD"] == _written("TRD", CACHE_END) and new["TRD"] != CURRENT["TRD"]
    assert "ATB" in new
    assert "skipped still_trading (0): -" in out
    assert new["EAR"] == CURRENT["EAR"] and new["DCS"] == CURRENT["DCS"]       # rule 2 still holds alone


def test_POSITIVE_CONTROL_reverting_rule_2_OVERWRITES_the_current_snapshot_caps(tmp_path, capsys, monkeypatch):
    """With `may_overwrite` always True, EAR (early-ending live name) and DCS (delisted) lose their
    current-snapshot caps to trailing medians: the current_snapshot_kept locks' subjects flip."""
    monkeypatch.setattr(t219, "may_overwrite", lambda current_entry: True)
    new, out, _, _ = _run(tmp_path, capsys)
    assert new["EAR"] == _written("EAR", pd.Timestamp("2022-06-30")) and new["EAR"] != CURRENT["EAR"]
    assert new["DCS"] == _written("DCS", DELISTED_END) and new["DCS"] != CURRENT["DCS"]
    assert "skipped current_snapshot_kept (0): -" in out
    assert new["TRD"] == CURRENT["TRD"]                                           # rule 1 still holds alone


CUTOVER_COPY = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/cutover_copy_2026_10_22")


def test_REAL_DATA_the_recompute_on_the_CUTOVER_COPY_also_EQUALS_the_pinned_tiers_file(tmp_path):
    """The reviewer's measurement of 2026-11-05, locked: on the step-1 cutover copy (648 of 730 files
    rewritten by the pass, ending 2026-10-22) the recompute from the pinned snapshot still reproduces the
    pinned tiers file exactly — 0 changed, 0 new — so re-pin #2's whole-file diff is EMPTY by construction.
    A scratch root whose data/processed IS the copy (a symlink; read-only) and whose data/universe is the
    pinned dir. Skipped where the copy or the pinned files are absent (another host)."""
    missing = [p for p in (PINNED_SNAPSHOT, PINNED_TIERS) if not p.is_file()]
    if missing or not CUTOVER_COPY.is_dir() or not list(CUTOVER_COPY.glob("*_1d.csv")):
        pytest.skip("the cutover copy or the pinned T-219 files are not on this host")
    root = tmp_path / "root"
    (root / "data").mkdir(parents=True)
    (root / "data" / "processed").symlink_to(CUTOVER_COPY, target_is_directory=True)
    (root / "data" / "universe").symlink_to(PINNED_TIERS.parent, target_is_directory=True)
    before = (PINNED_TIERS.read_bytes(), PINNED_SNAPSHOT.read_bytes())
    new, stats = t219.recompute_from_snapshot(PINNED_SNAPSHOT, root=root)
    pinned = json.loads(PINNED_TIERS.read_text())
    assert new == pinned, {"changed": stats["changed_vs_current"], "new": stats["new_vs_current"]}
    assert list(new.keys()) == list(pinned.keys())
    assert stats["changed_vs_current"] == 0 and stats["new_vs_current"] == 0
    assert str(stats["cache_end"]).startswith("2026-10-22"), stats["cache_end"]   # the copy's bulk end, not April's
    assert (PINNED_TIERS.read_bytes(), PINNED_SNAPSHOT.read_bytes()) == before    # read-only on the pinned files
