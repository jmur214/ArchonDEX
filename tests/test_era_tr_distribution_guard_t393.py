"""T-393 — locks on the era_tr DISTRIBUTION GUARD (`engines/data_manager/era_tr.py::distribution_guard`).

The rule (pre-declared, `docs/Sources/proposal_era_tr_distribution_guard_t393_2026-11-13.md` §1.1): a missed
reference dividend is ADDED only if (a) its measured m is ≤ 1.5 and (b) the reference's own close does not
contradict the drop (testable where q ≥ 4σ: refused iff the close is nearer "no drop" AND the drop is rejected
at 4σ). Each named real case is planted on a synthetic name through the real probe; each lock was proven by
REVERSION (the source string named in its docstring).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engines.data_manager import era_tr as et

E = 300


def planted(q: float, close_ret: float, stooq_extra: float = 0.0, sigma: float = 0.01, seed: int = 0):
    """One ex-date at bar E with D/P = q. The reference applies it in adj_close (always); its CLOSE moves
    `close_ret` on the ex-day; Stooq moves like the close, less `stooq_extra` (a spin-off Stooq left
    unapplied). Returns (labels, q_log)."""
    rng = np.random.default_rng(seed)
    n = 600
    dates = pd.bdate_range("2005-01-03", periods=n)
    rc = rng.normal(0, sigma, n)
    rc[0] = 0.0
    rc[E - 1], rc[E + 1] = 0.001, -0.001
    rc[E] = close_ret
    q_log = -np.log1p(-q)
    ra = rc.copy()
    ra[E] += q_log
    rs = rc + rng.normal(0, 2e-5, n)
    rs[E] -= stooq_extra
    j = pd.DataFrame({"stooq": 40 * np.exp(np.cumsum(rs)), "adj_close": 30 * np.exp(np.cumsum(ra)),
                      "close": 50 * np.exp(np.cumsum(rc))}, index=dates)
    divs = pd.Series([q * j["close"].iloc[E - 1]], index=[dates[E]])
    return et.label_exdates(et.probe_exdates(j, divs)), q_log


def one(lab: pd.DataFrame) -> pd.Series:
    assert len(lab) == 1
    return lab.iloc[0]


def test_a_pure_double_count_is_refused_and_recorded_not_added():
    """DHR 2016 / ETN 2001: the close does not fall, adj_close jumps, Stooq follows the close (m ≈ 1).
    Reversion: `& (r > -q / 2) & (z > DROP_REJECT_Z)` → `& (r > -q / 2) & (z > np.inf)`."""
    lab, _ = planted(q=0.30, close_ret=+0.03)
    r = one(lab)
    assert r["m"] == pytest.approx(1.0, abs=0.01) and r["label_source"] == "measured"
    assert bool(r["refused"]) and r["refusal_reason"] == et.REFUSED_CLOSE
    assert not bool(r["missed"])                                   # nothing is added …
    rows = et._distribution_rows(lab, "refused")                    # … and it is LABELLED with what was measured
    assert rows[0]["reason"] == et.REFUSED_CLOSE and rows[0]["close_move"] == pytest.approx(0.03)
    assert rows[0]["m"] == pytest.approx(1.0, abs=0.01) and rows[0]["z_drop"] > 4


def test_a_refused_ex_date_adds_no_back_adjustment():
    """Reversion: `out["missed"] = missed & ~refused` → `out["missed"] = missed`."""
    lab, _ = planted(q=0.30, close_ret=+0.03)
    add = lab[lab["missed"]]
    dates = pd.bdate_range("2005-01-03", periods=600)
    f = et.missed_log_factor(dates, pd.DatetimeIndex(add["day"]), add["log_f"].to_numpy())
    assert np.allclose(f, 0.0)


def test_a_zero_move_day_is_refused_at_any_size():
    """SRE 2006-09-06: D/P 5 %, the close moves 0.00 %. No size cutoff is involved (σ 0.9 %, q = 5.7σ).
    Reversion: `& (r > -q / 2) & (z > DROP_REJECT_Z)` → `& (r > -q / 2) & (z > np.inf)`."""
    r = one(planted(q=0.0504, close_ret=0.0, sigma=0.009)[0])
    assert bool(r["refused"]) and r["refusal_reason"] == et.REFUSED_CLOSE


def test_a_mis_sized_spin_off_is_refused_by_the_m_band_alone():
    """CNP 2002: Stooq left the spin-off unapplied (m ≫ 1) and the close cannot decide (q = 2σ).
    Reversion: `(out["m"].to_numpy(dtype=float) > MISSED_M_MAX)` → `(… > np.inf)`."""
    lab, q_log = planted(q=0.02, close_ret=+0.004, stooq_extra=0.033)
    r = one(lab)
    assert r["m"] > et.MISSED_M_MAX and r["label_source"] == "measured"
    assert q_log / r["close_sigma"] < et.DROP_TESTABLE_SIGMA       # (b) has no say here
    assert bool(r["refused"]) and r["refusal_reason"] == et.REFUSED_M and not bool(r["missed"])


def test_an_ordinary_missed_dividend_is_added_even_on_a_strong_up_day():
    """The control. A 0.6 % dividend on a day the close rises 5σ: the drop is "rejected" by a bare z-test,
    but the close cannot decide a dividend this small — it must stay ADDED (27 such in v4).
    Reversion: `missed & (snr >= DROP_TESTABLE_SIGMA)` → `missed & (snr >= 0.0)`."""
    for close_ret in (-0.006, +0.05):
        r = one(planted(q=0.006, close_ret=close_ret)[0])
        assert bool(r["missed"]) and not bool(r["refused"]) and r["refusal_reason"] == ""


def test_a_real_large_distribution_whose_close_falls_is_added():
    r = one(planted(q=0.10, close_ret=-0.105)[0])
    assert bool(r["missed"]) and not bool(r["refused"]) and not bool(r["unresolved"])


def test_a_partial_drop_is_added_and_labelled_unresolved_never_refused():
    """PEP 1997 / AN 1995: the close fell about half of D/P — nearer the drop than no drop, though the full
    drop is rejected at 4σ. Real cash specials sit in the same band, so it is ADDED and LABELLED.
    Reversion: `& (r > -q / 2) & (z > DROP_REJECT_Z)` → `& (z > DROP_REJECT_Z)` (the midpoint)."""
    lab, q_log = planted(q=0.10, close_ret=-0.058)
    r = one(lab)
    assert (r["close_move"] + q_log) / r["close_sigma"] > et.DROP_REJECT_Z and r["close_move"] < -q_log / 2
    assert bool(r["missed"]) and not bool(r["refused"]) and bool(r["unresolved"])
    assert et._distribution_rows(lab, "unresolved")[0]["reason"].startswith("added")


def test_label_exdates_always_runs_the_guard():
    """Reversion: the non-empty `return distribution_guard(out)` in label_exdates → `return out`."""
    lab, _ = planted(q=0.006, close_ret=-0.006)
    assert {"refused", "refusal_reason", "unresolved", "z_drop"} <= set(lab.columns)
    assert {"refused", "refusal_reason", "unresolved"} <= set(et.empty_labels().columns)


# ── the declared v5 bytes (replaces "the writer equals v4 on every file") ────────────────────────────────

DELTA = Path(__file__).resolve().parents[1] / "config" / "era_tr_v5_delta_t393.json"
V4 = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_v4_2026_11_11")


def test_the_declared_v5_delta_names_the_refused_ex_dates_and_nothing_else():
    d = json.loads(DELTA.read_text())
    assert d["files"] == 575 and d["unchanged_md5_equal_v4"] + len(d["changed"]) == 575
    assert d["v4_processed_aggregate_md5"] == "2cee41ef7d2e0bd8fa858d500f99dda2"
    for t, row in d["changed"].items():
        assert row["refused"], f"{t}: a changed file with no refused ex-date"
        assert row["v4_md5"] != row["v5_md5"]
    assert {"DHR", "ETN", "XRX", "CNP", "SRE"} <= set(d["changed"])
    assert not {"PEP", "BAX", "AN"} & set(d["changed"])            # declared: added, not refused


@pytest.mark.skipif(not (V4 / "MANIFEST.md5").exists(), reason="the v4 candidate is not on this machine")
def test_the_writer_reproduces_v4_on_an_unaffected_file_and_the_declared_bytes_on_an_affected_one():
    """The T-387 identity, restated for v5: UNAFFECTED files are v4's bytes; AFFECTED files are the declared
    new bytes. (The full 575-file statement is `scripts/era_tr_v5_delta_t393.py run`.)"""
    import hashlib
    from scripts import drip_fix_candidate_t384 as t384
    d = json.loads(DELTA.read_text())
    v4_md5 = {ln.split("  ", 1)[1]: ln.split("  ", 1)[0] for ln in (V4 / "MANIFEST.md5").read_text().splitlines()}
    meta, raw_idx = t384.load_meta(), t384.raw_stooq_index()
    yf = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_2026_11_11/yf")
    for t in ("KO", "DHR"):
        raw = et.read_raw_stooq(raw_idx[t])
        px, dv = et.read_yf(t, yf)
        ref = et.analyse_reference(t, raw, px, dv, pd.Timestamp(meta[t]["seam_date"]))
        header, lines = t384.read_cache_text(t)
        res = et.build_file(t, meta[t], header, lines, t384.read_cache_frame(t), raw, ref)
        got = hashlib.md5(res.text.encode()).hexdigest()
        if t in d["changed"]:
            assert got == d["changed"][t]["v5_md5"] != v4_md5[f"processed/{t}_1d.csv"]
            assert [r["reason"] for r in res.record["refused_distributions"]] == [et.REFUSED_CLOSE]
        else:
            assert got == v4_md5[f"processed/{t}_1d.csv"]
            assert res.record["refused_distributions"] == []
