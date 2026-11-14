"""T-393 — locks on the era_tr DISTRIBUTION GUARD (`engines/data_manager/era_tr.py::distribution_guard`).

The rule (`docs/Sources/proposal_era_tr_distribution_guard_t393_2026-11-13.md` §1.1 as amended by §7, a
post-review correction):
  (b) the ONLY refusal: where q ≥ 4σ, an ex-date is refused iff the reference close's best-aligned bar
      (the lowest return of e−1, e, e+1) is nearer "no drop" AND z* > 6; 4 < z* ≤ 6 is added and labelled;
  (a) a measured m > 1.5 is added and LABELLED, never refused;
  a refused ex-date whose Stooq spin-off is unapplied (measured m > 1.5) is REPAIRED from the reference close.
Each case is planted on a synthetic name through the real probe; each lock was proven by REVERSION (the source
string named in its docstring).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engines.data_manager import era_tr as et

E = 300
DATES = pd.bdate_range("2005-01-03", periods=600)


def planted(q: float, close_ret: float, stooq_extra: float = 0.0, sigma: float = 0.01, prev_ret: float = 0.001,
            seed: int = 0):
    """One ex-date at bar E with D/P = q. The reference applies it in adj_close (always); its CLOSE moves
    `close_ret` on the ex-day and `prev_ret` on the bar before; Stooq moves like the close, less `stooq_extra`
    on the ex-day (a spin-off Stooq left unapplied). Returns (labels, q_log)."""
    rng = np.random.default_rng(seed)
    n = len(DATES)
    rc = rng.normal(0, sigma, n)
    rc[0] = 0.0
    rc[E - 1], rc[E], rc[E + 1] = prev_ret, close_ret, -0.001
    q_log = -np.log1p(-q)
    ra = rc.copy()
    ra[E] += q_log
    rs = rc + rng.normal(0, 2e-5, n)
    rs[E] -= stooq_extra
    j = pd.DataFrame({"stooq": 40 * np.exp(np.cumsum(rs)), "adj_close": 30 * np.exp(np.cumsum(ra)),
                      "close": 50 * np.exp(np.cumsum(rc))}, index=DATES)
    divs = pd.Series([q * j["close"].iloc[E - 1]], index=[DATES[E]])
    return et.label_exdates(et.probe_exdates(j, divs)), q_log


def one(lab: pd.DataFrame) -> pd.Series:
    assert len(lab) == 1
    return lab.iloc[0]


def back_adjustment(lab: pd.DataFrame) -> np.ndarray:
    add = lab[lab["missed"]]
    return et.missed_log_factor(DATES, pd.DatetimeIndex(add["day"]), add["log_f"].to_numpy())


def test_a_pure_double_count_is_refused_recorded_and_adds_nothing():
    """DHR 2016 / ETN 2001: no aligned bar of the close falls, adj_close jumps, Stooq follows the close (m ≈ 1).
    Reversions: `refused = no_drop & (z > DROP_REFUSE_Z)` → `refused = no_drop & (z > np.inf)` (the refusal);
    `added = missed & (~refused | repaired)` → `added = missed` (a refused ex-date must add nothing)."""
    lab, _ = planted(q=0.30, close_ret=+0.03)
    r = one(lab)
    assert r["m"] == pytest.approx(1.0, abs=0.01) and r["label_source"] == "measured"
    assert bool(r["refused"]) and r["refusal_reason"] == et.REFUSED_CLOSE and not bool(r["spinoff_repaired"])
    assert not bool(r["missed"]) and np.allclose(back_adjustment(lab), 0.0)
    row = et._distribution_rows(lab, "refused")[0]                  # LABELLED with what was measured
    assert row["reason"] == et.REFUSED_CLOSE and row["close_move"] == pytest.approx(0.03) and row["z_drop"] > 6
    assert row["repaired"] is False


def test_a_mis_dated_ex_date_is_not_refused():
    """MMM 1996-07-16: the ex-day close barely moves, but the bar BEFORE it fell by the distribution.
    Reversion: `"close_move_best": np.minimum(np.minimum(r_close[pos - 1], r_close[pos]),` →
    `"close_move_best": np.minimum(np.minimum(r_close[pos], r_close[pos]),` (test the ex-day bar only)."""
    r = one(planted(q=0.0375, close_ret=-0.004, prev_ret=-0.0458, sigma=0.0085)[0])
    assert bool(r["missed"]) and not bool(r["refused"]) and not bool(r["unresolved"])


def test_a_marginal_no_drop_is_added_and_labelled_not_refused():
    """SRE 2006-09-06: D/P 5 %, the close moves 0.00 % (z* between 4 and 6). A marginal case is never refused.
    Reversion: `DROP_REFUSE_Z = 6.0` → `DROP_REFUSE_Z = 4.0`."""
    lab, q_log = planted(q=0.0504, close_ret=0.0, sigma=0.009)
    r = one(lab)
    assert et.DROP_MARGINAL_Z < r["z_drop"] <= et.DROP_REFUSE_Z
    assert bool(r["missed"]) and not bool(r["refused"])
    assert bool(r["unresolved"]) and r["unresolved_reason"] == et.UNRESOLVED_MARGINAL
    assert r["log_f"] == pytest.approx(-q_log)


def test_m_above_the_band_is_added_and_labelled_never_refused():
    """ADM 2006 / TGT 2007 / CNP 2002: m > 1.5 where the close cannot decide. Rule (a) LABELS; it does not refuse.
    Reversion: `reason = np.where(above & ~refused, UNRESOLVED_M,` → `reason = np.where(above & refused, UNRESOLVED_M,`."""
    lab, q_log = planted(q=0.02, close_ret=+0.004, stooq_extra=0.033)
    r = one(lab)
    assert r["m"] > et.MISSED_M_MAX and r["label_source"] == "measured"
    assert bool(r["missed"]) and not bool(r["refused"]) and not bool(r["spinoff_repaired"])
    assert bool(r["unresolved"]) and r["unresolved_reason"] == et.UNRESOLVED_M
    assert r["log_f"] == pytest.approx(-q_log)                      # the dividend itself, as v4 added it
    assert et._distribution_rows(lab, "unresolved")[0]["reason"] == "added; " + et.UNRESOLVED_M


def test_a_refused_distribution_with_an_unapplied_stooq_spin_off_is_repaired_from_the_close():
    """XRX 2017-01-03: the close does not fall (the dividend is refused) and Stooq fell 40 % (m ≈ 4). The
    Stooq step against the CLOSE is applied in the same step; the dividend's own factor is not.
    Reversion: `repaired = refused & above & np.isfinite(step) & (step < 0)` → `repaired = refused & ~refused`
    (refuse without repairing: the file would be left worse than v4)."""
    lab, q_log = planted(q=0.13, close_ret=+0.03, stooq_extra=0.40)
    r = one(lab)
    assert r["m"] > 3 and bool(r["refused"]) and bool(r["spinoff_repaired"]) and bool(r["missed"])
    assert r["log_f"] == pytest.approx(-0.40, abs=2e-3)             # Stooq − close over the probe window
    assert r["log_f_dividend"] == pytest.approx(-q_log)             # recorded, NOT applied
    f = back_adjustment(lab)
    assert f[E - 1] == pytest.approx(-0.40, abs=2e-3) and f[E] == 0.0
    row = et._distribution_rows(lab, "spinoff_repaired")[0]
    assert row["log_step"] == pytest.approx(-0.40, abs=2e-3) and "reference close" in row["sized_from"]
    assert et._distribution_rows(lab, "refused")[0]["repaired"] is True


def test_the_repair_is_sized_from_the_close_not_from_adj_close():
    """Reversion: `step = (out["y_lvl"].to_numpy(dtype=float) - out["x_lvl"].to_numpy(dtype=float)` →
    `step = (-out["x_lvl"].to_numpy(dtype=float) - 0 * out["y_lvl"].to_numpy(dtype=float)` (Stooq − adj_close)."""
    lab, q_log = planted(q=0.13, close_ret=+0.03, stooq_extra=0.40)
    assert one(lab)["log_f"] > -(0.40 + q_log / 2)                  # −0.40, not −(0.40 + q_log)


def test_an_ordinary_missed_dividend_is_added_even_on_a_strong_up_day():
    """The control. A 0.6 % dividend with every aligned bar up ≥ 5σ: a bare z-test "rejects" the drop, but the
    close cannot decide a dividend this small — it stays ADDED, unlabelled.
    Reversion: `no_drop = missed & (snr >= DROP_TESTABLE_SIGMA) & (r > -q / 2)` → `… (snr >= 0.0) …`."""
    lab, q_log = planted(q=0.006, close_ret=-0.006)
    r = one(lab)
    assert bool(r["missed"]) and not bool(r["refused"]) and not bool(r["unresolved"])
    rng_free = planted(q=0.006, close_ret=+0.07, prev_ret=+0.07)[0].copy()
    r2 = one(rng_free)
    assert r2["close_move_best"] > -0.002 and (r2["close_move_best"] + q_log) / r2["close_sigma"] < 6
    up = pd.DataFrame([r2]).assign(close_move_best=0.07)           # every aligned bar +7σ
    g = one(et.distribution_guard(up.assign(log_f=r2["log_f_dividend"], missed=True)))
    assert bool(g["missed"]) and not bool(g["refused"]) and not bool(g["unresolved"])


def test_a_real_large_distribution_whose_close_falls_is_added():
    r = one(planted(q=0.10, close_ret=-0.105)[0])
    assert bool(r["missed"]) and not bool(r["refused"]) and not bool(r["unresolved"])


def test_a_partial_drop_is_added_and_labelled_never_refused():
    """PEP 1997 / AN 1995: the close fell about half of D/P — nearer the drop than no drop, though the full drop
    is rejected. Real cash specials sit in the same band.
    Reversion: `no_drop = missed & (snr >= DROP_TESTABLE_SIGMA) & (r > -q / 2)` → `… & (r > -np.inf)`."""
    lab, q_log = planted(q=0.20, close_ret=-0.125)
    r = one(lab)
    assert r["z_drop"] > et.DROP_REFUSE_Z and r["close_move_best"] < -q_log / 2
    assert bool(r["missed"]) and not bool(r["refused"])
    assert bool(r["unresolved"]) and r["unresolved_reason"] == et.UNRESOLVED_PARTIAL


def test_label_exdates_always_runs_the_guard():
    """Reversion: the non-empty `return distribution_guard(out)` in label_exdates → `return out`."""
    lab, _ = planted(q=0.006, close_ret=-0.006)
    cols = {"refused", "refusal_reason", "unresolved", "unresolved_reason", "spinoff_repaired", "z_drop"}
    assert cols <= set(lab.columns) and cols <= set(et.empty_labels().columns)


# ── the declared v5 bytes (the T-387 identity "the writer equals v4", restated) ──────────────────────────

DELTA = Path(__file__).resolve().parents[1] / "config" / "era_tr_v5_delta_t393.json"
V4 = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_v4_2026_11_11")


def test_the_declared_v5_delta_is_three_files_each_with_a_refused_ex_date():
    d = json.loads(DELTA.read_text())
    assert d["files"] == 575 and d["unchanged_md5_equal_v4"] + len(d["changed"]) == 575
    assert d["v4_processed_aggregate_md5"] == "2cee41ef7d2e0bd8fa858d500f99dda2"
    assert set(d["changed"]) == {"DHR", "ETN", "XRX"}
    for t, row in d["changed"].items():
        assert row["refused"] and row["v4_md5"] != row["v5_md5"], t
    assert d["changed"]["XRX"]["repaired"] and not d["changed"]["DHR"]["repaired"]


@pytest.mark.skipif(not (V4 / "MANIFEST.md5").exists(), reason="the v4 candidate is not on this machine")
def test_the_writer_reproduces_v4_on_unaffected_files_and_the_declared_bytes_on_affected_ones():
    """UNAFFECTED files are v4's bytes — including the ex-dates the superseded rule wrongly refused (MMM, ADM,
    SRE); AFFECTED files are the declared new bytes. (All 575: `scripts/era_tr_v5_delta_t393.py run`.)"""
    import hashlib
    from scripts import drip_fix_candidate_t384 as t384
    d = json.loads(DELTA.read_text())
    v4_md5 = {ln.split("  ", 1)[1]: ln.split("  ", 1)[0] for ln in (V4 / "MANIFEST.md5").read_text().splitlines()}
    meta, raw_idx = t384.load_meta(), t384.raw_stooq_index()
    yf = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_2026_11_11/yf")
    for t in ("KO", "MMM", "ADM", "SRE", "DHR", "XRX"):
        raw = et.read_raw_stooq(raw_idx[t])
        px, dv = et.read_yf(t, yf)
        ref = et.analyse_reference(t, raw, px, dv, pd.Timestamp(meta[t]["seam_date"]))
        header, lines = t384.read_cache_text(t)
        res = et.build_file(t, meta[t], header, lines, t384.read_cache_frame(t), raw, ref)
        got = hashlib.md5(res.text.encode()).hexdigest()
        if t in d["changed"]:
            assert got == d["changed"][t]["v5_md5"] != v4_md5[f"processed/{t}_1d.csv"], t
            assert [r["reason"] for r in res.record["refused_distributions"]] == [et.REFUSED_CLOSE]
            assert bool(res.record["stooq_spinoff_repaired"]) == (t == "XRX")
        else:
            assert got == v4_md5[f"processed/{t}_1d.csv"], t
            assert res.record["refused_distributions"] == [] and res.record["stooq_spinoff_repaired"] == []
