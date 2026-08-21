"""T-326 — ThesisBook: the report-only virtual book for D's thesis desk.

Instance #3 of the shadow-desk parameterization. Verifies the three mechanics that differ
from the fixed-horizon desks (falsifier-triggered exit, SPY-matched twin, multi-leg
baskets), the CHANNEL FIREWALL (machine vs user_seeded never blend), fail-closed parking,
and that scoring defers to D's own T-324 bar rather than a second standard.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.event_shadow_book import MAX_WEIGHT  # noqa: E402
from paper_trader.thesis_book import (  # noqa: E402
    CONVICTION_FLOOR, MACHINE_DESK, MAX_THESIS_GROSS, USER_DESK, ThesisBook)


def _thesis(tid="T1", origin="machine", conv=0.8, hz=60, legs=None, fals=None,
            theme="picks_and_shovels", as_of="2026-07-27"):
    return {"schema_version": "thesis_call/v1", "thesis_id": tid, "as_of": as_of,
            "origin": origin, "theme_class": theme, "conviction": conv, "horizon_days": hz,
            "instruments": legs if legs is not None else
            [{"symbol": "AAA", "role": "primary", "weight_hint": 0.6, "mapping_reason": "r"},
             {"symbol": "BBB", "role": "second_order", "weight_hint": 0.4, "mapping_reason": "r"}],
            "falsifiers": fals if fals is not None else
            [{"kind": "qualitative", "statement": "s", "check_by": "2027-01-01"}]}


# ---------- multi-leg basket ----------
def test_basket_holds_multiple_legs_at_thesis_weights(tmp_path):
    b = ThesisBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"AAA": 10.0, "BBB": 20.0, "SPY": 600.0},
             theses=[_thesis()])
    pos = b._state()["open"][0]
    assert set(pos["weights"]) == {"AAA", "BBB"}
    # the thesis's OWN 60/40 proportions are preserved (rounded to 5dp)
    assert pos["weights"]["AAA"] / pos["weights"]["BBB"] == pytest.approx(0.6 / 0.4, rel=1e-4)
    # sizing binds on whichever cap is tighter — here the per-name cap on the 60% leg
    assert pos["weights"]["AAA"] == pytest.approx(MAX_WEIGHT, rel=1e-4)
    assert sum(pos["weights"].values()) <= MAX_THESIS_GROSS + 1e-9


def test_no_weight_hints_equal_weights_the_legs(tmp_path):
    b = ThesisBook(root=str(tmp_path))
    legs = [{"symbol": s, "role": "primary", "weight_hint": 0.0, "mapping_reason": "r"}
            for s in ("AAA", "BBB", "CCC")]
    b.record("2026-07-28", closes={"AAA": 1.0, "BBB": 1.0, "CCC": 1.0, "SPY": 600.0},
             theses=[_thesis(legs=legs)])
    w = b._state()["open"][0]["weights"]
    assert w["AAA"] == pytest.approx(w["BBB"]) == pytest.approx(w["CCC"])


def test_sizing_respects_both_caps_by_construction(tmp_path):
    """`weight_hint` is a within-basket PROPORTION, so absolute size is the book's rule:
    a concentrated basket is sized DOWN to the per-name cap rather than rejected — and no
    constructed basket may ever breach either cap."""
    b = ThesisBook(root=str(tmp_path))
    legs = [{"symbol": "AAA", "role": "primary", "weight_hint": 1.0, "mapping_reason": "r"}]
    b.record("2026-07-28", closes={"AAA": 10.0, "SPY": 600.0},
             theses=[_thesis(conv=1.0, legs=legs)])
    w = b._state()["open"][0]["weights"]
    assert w["AAA"] == pytest.approx(MAX_WEIGHT)          # sized to the per-name cap
    # and a lopsided multi-leg basket also stays within BOTH caps
    b2 = ThesisBook(root=str(tmp_path / "b2"))
    legs2 = [{"symbol": "AAA", "role": "primary", "weight_hint": 0.9, "mapping_reason": "r"},
             {"symbol": "BBB", "role": "hedge", "weight_hint": 0.1, "mapping_reason": "r"}]
    b2.record("2026-07-28", closes={"AAA": 10.0, "BBB": 5.0, "SPY": 600.0},
              theses=[_thesis(conv=1.0, legs=legs2)])
    w2 = b2._state()["open"][0]["weights"]
    assert max(w2.values()) <= MAX_WEIGHT + 1e-9
    assert sum(w2.values()) <= MAX_THESIS_GROSS + 1e-9


# ---------- falsifier-triggered exit ----------
def test_applied_scale_is_ON_THE_RECORD_when_per_name_binds(tmp_path):
    """Director ruling: a down-sized basket must be VISIBLE in the book's history —
    never reconstructed by archaeology."""
    b = ThesisBook(root=str(tmp_path))
    # 60/40 hints at conviction 0.8 → per-name cap binds (0.6 × 0.48 > 0.20)
    b.record("2026-07-28", closes={"AAA": 10.0, "BBB": 20.0, "SPY": 600.0},
             theses=[_thesis(conv=0.8)])
    pos = b._state()["open"][0]
    assert pos["downsized"] is True
    assert pos["binding_cap"] == "per_name"
    assert pos["sizing_scale"] == pytest.approx(MAX_WEIGHT / 0.6, rel=1e-4)
    assert pos["unconstrained_scale"] == pytest.approx(MAX_THESIS_GROSS * 0.8, rel=1e-4)
    assert pos["sizing_scale"] < pos["unconstrained_scale"]          # the down-size is legible
    # and it is announced in the day's reasons, not silent
    assert any("sized to" in r and "not silent" in r
               for r in b._state()["days"][-1]["reasons"])


def test_applied_scale_records_gross_binding_when_basket_is_diversified(tmp_path):
    """A well-spread basket is bound by gross × conviction, not the per-name cap —
    and that is stamped too, so 'which cap bound it' is always answerable."""
    b = ThesisBook(root=str(tmp_path))
    legs = [{"symbol": s, "role": "primary", "weight_hint": 0.25, "mapping_reason": "r"}
            for s in ("AAA", "BBB", "CCC", "DDD")]
    b.record("2026-07-28", closes={s: 10.0 for s in ("AAA", "BBB", "CCC", "DDD")}
             | {"SPY": 600.0}, theses=[_thesis(conv=0.6, legs=legs)])
    pos = b._state()["open"][0]
    assert pos["downsized"] is False
    assert pos["binding_cap"] == "gross_x_conviction"
    assert pos["sizing_scale"] == pytest.approx(MAX_THESIS_GROSS * 0.6, rel=1e-4)


def test_scale_provenance_survives_onto_the_closed_record(tmp_path):
    """The sizing must remain legible AFTER exit — that is where archaeology would bite."""
    b = ThesisBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"AAA": 100.0, "BBB": 100.0, "SPY": 600.0},
             theses=[_thesis(conv=0.8, hz=1)])
    b.record("2026-07-29", closes={"AAA": 110.0, "BBB": 110.0, "SPY": 612.0})
    c = b._state()["closed"][0]
    assert c["downsized"] is True and c["binding_cap"] == "per_name"
    assert c["sizing_scale"] == pytest.approx(MAX_WEIGHT / 0.6, rel=1e-4)


def test_falsifier_firing_closes_at_next_close_and_marks_falsified(tmp_path):
    b = ThesisBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"AAA": 10.0, "BBB": 20.0, "SPY": 600.0},
             theses=[_thesis(hz=250)])
    b.record("2026-07-29", closes={"AAA": 11.0, "BBB": 21.0, "SPY": 606.0},
             falsifiers_fired={"T1": True})
    st = b._state()
    assert st["open"] == [] and len(st["closed"]) == 1
    c = st["closed"][0]
    assert c["killed_by_falsifier"] is True and c["held_days"] == 1
    assert c["held_days"] < c["horizon_days"]        # closed EARLY, by the falsifier


def test_falsifier_past_check_by_is_fail_closed(tmp_path):
    b = ThesisBook(root=str(tmp_path))
    fals = [{"kind": "resolver", "statement": "s", "check_by": "2026-07-29", "resolver": {}}]
    b.record("2026-07-28", closes={"AAA": 10.0, "BBB": 20.0, "SPY": 600.0},
             theses=[_thesis(hz=250, fals=fals)])
    b.record("2026-07-30", closes={"AAA": 10.0, "BBB": 20.0, "SPY": 600.0})   # past check_by
    c = b._state()["closed"][0]
    assert c["killed_by_falsifier"] is True
    assert "fail-closed" in c["exit_reason"]          # unresolved past deadline ≠ benign


def test_thesis_without_falsifier_is_parked_as_a_story(tmp_path):
    b = ThesisBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"AAA": 10.0, "BBB": 20.0, "SPY": 600.0},
             theses=[_thesis(fals=[])])
    st = b._state()
    assert st["open"] == []
    assert any("story, not a position" in r for r in st["days"][-1]["reasons"])


# ---------- horizon exit + SPY twin ----------
def test_horizon_exit_scores_against_spy_over_matched_window(tmp_path):
    b = ThesisBook(root=str(tmp_path))
    # T-343: the horizon clock runs from the FILING date (as_of 2026-07-27), not from the
    # session count — so hz=2 matures on 07-29, the second day after filing, regardless of
    # when the basket could actually be opened.
    b.record("2026-07-28", closes={"AAA": 100.0, "BBB": 100.0, "SPY": 600.0},
             theses=[_thesis(hz=2)])
    b.record("2026-07-29", closes={"AAA": 110.0, "BBB": 110.0, "SPY": 612.0})
    c = b._state()["closed"][0]
    assert c["exit_reason"] == "horizon" and c["killed_by_falsifier"] is False
    assert c["gross_ret"] == pytest.approx(0.10)              # both legs +10%
    assert c["net_ret"] == pytest.approx(0.10 - 2 * 0.0025)   # every leg costed both sides
    assert c["twin_ret"] == pytest.approx(0.02)               # SPY over the SAME window
    assert c["excess_vs_twin"] == pytest.approx(0.10 - 0.005 - 0.02)


def test_missing_leg_price_at_exit_holds_degraded(tmp_path):
    b = ThesisBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"AAA": 100.0, "BBB": 100.0, "SPY": 600.0},
             theses=[_thesis(hz=1)])
    b.record("2026-07-29", closes={"AAA": 105.0, "SPY": 606.0})     # BBB missing
    st = b._state()
    assert len(st["open"]) == 1 and st["closed"] == []              # held, not fabricated
    assert st["days"][-1]["degraded"] is True


def test_low_conviction_parked(tmp_path):
    b = ThesisBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"AAA": 10.0, "BBB": 20.0, "SPY": 600.0},
             theses=[_thesis(conv=CONVICTION_FLOOR - 0.01)])
    assert b._state()["open"] == []


# ---------- the CHANNEL FIREWALL ----------
def test_channel_sub_books_never_blend(tmp_path):
    m = ThesisBook(cfg=MACHINE_DESK, root=str(tmp_path))
    u = ThesisBook(cfg=USER_DESK, root=str(tmp_path))
    assert type(m) is type(u) and m._file() != u._file()      # one machinery, two records
    assert m.origin == "machine" and u.origin == "user_seeded"
    both = [_thesis(tid="M1", origin="machine"), _thesis(tid="U1", origin="user_seeded")]
    closes = {"AAA": 10.0, "BBB": 20.0, "SPY": 600.0}
    # each book filters the SHARED feed to its own channel
    m.record("2026-07-28", closes=closes,
             theses=[t for t in both if t["origin"] == "machine"])
    u.record("2026-07-28", closes=closes,
             theses=[t for t in both if t["origin"] == "user_seeded"])
    assert [p["thesis_id"] for p in m._state()["open"]] == ["M1"]
    assert [p["thesis_id"] for p in u._state()["open"]] == ["U1"]


def test_loader_filters_by_origin(tmp_path):
    d = tmp_path / "data" / "intel"
    d.mkdir(parents=True)
    import json as _j
    (d / "thesis_calls.jsonl").write_text(
        "\n".join(_j.dumps(t) for t in [_thesis(tid="M1", origin="machine", as_of="2026-07-27"),
                                        _thesis(tid="U1", origin="user_seeded", as_of="2026-07-27")]))
    m = ThesisBook(cfg=MACHINE_DESK, root=str(tmp_path))
    got, why = m._load_theses("2026-07-27")
    assert why == "ok" and [g["thesis_id"] for g in got] == ["M1"]   # firewall holds


# ---------- scoring defers to D's bar ----------
def test_promotion_uses_D_t324_bar_and_never_passes_prematurely(tmp_path):
    b = ThesisBook(root=str(tmp_path))
    st = b._state()
    st["closed"] = [{"thesis_id": f"T{i}", "theme_class": "picks_and_shovels",
                     "conviction": 0.7, "net_ret": 0.05, "twin_ret": 0.01,
                     "excess_vs_twin": 0.04, "killed_by_falsifier": False}
                    for i in range(5)]                      # « the ≥20 bar
    b._write(st)
    g = b.promotion_gates()
    assert "D/T-324" in g["standard"]
    assert g["per_theme_class"]["picks_and_shovels"]["PROMOTED"] is False
    assert g["promote_any"] is False


def test_outcomes_feed_Ds_scoring_interface(tmp_path):
    b = ThesisBook(root=str(tmp_path))
    st = b._state()
    st["closed"] = [{"thesis_id": "T1", "theme_class": "regulatory_shift", "conviction": 0.6,
                     "net_ret": 0.20, "twin_ret": 0.05, "excess_vs_twin": 0.15,
                     "killed_by_falsifier": True}]
    b._write(st)
    o = b.outcomes()[0]
    assert o.thesis_id == "T1" and o.ret == 0.20 and o.twin_ret == 0.05
    assert o.killed_by_falsifier is True and o.resolved is True


def test_idempotent_per_date(tmp_path):
    b = ThesisBook(root=str(tmp_path))
    for _ in range(2):
        b.record("2026-07-28", closes={"AAA": 10.0, "BBB": 20.0, "SPY": 600.0},
                 theses=[_thesis()])
    assert len(b._state()["open"]) == 1 and len(b._state()["days"]) == 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))


# ---------- T-343: the price fetch FOLLOWS the book ----------
def test_never_seen_ticker_is_requested_by_the_price_fetch(tmp_path):
    """The dispatch bar: a thesis naming a ticker nobody pre-listed must have its price
    FETCHED. Nobody can enumerate what the machine will pick (FN and AMTM proved it), so
    the symbol list has to be derived from the book, never from a static universe."""
    b = ThesisBook(root=str(tmp_path))
    legs = [{"symbol": s, "role": "primary", "weight_hint": 0.5, "mapping_reason": "r"}
            for s in ("FN", "AMTM")]
    # file on the 28th (a session the book has seen) — the 29th run consumes it
    b.record("2026-07-28", closes={"SPY": 600.0}, theses=[])
    import json
    src = tmp_path / "data/intel/thesis_calls.jsonl"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(json.dumps(_thesis(tid="TZ", legs=legs, as_of="2026-07-28")) + "\n")
    syms = b.pending_symbols("2026-07-29")
    assert "FN" in syms and "AMTM" in syms, "unseen legs must reach the fetch"
    assert "SPY" in syms, "the twin is always armed"


def test_missing_price_parks_with_a_reason_and_is_retried_not_lost(tmp_path):
    """Fail-closed stays: no price → PENDING with the reason naming the leg, never a
    fabricated fill. But the thesis must SURVIVE the park — the old code skipped it and
    the loader only ever looks at the prior session, so it was silently LOST."""
    b = ThesisBook(root=str(tmp_path))
    # AAA priced, BBB absent → parks
    st = b.record("2026-07-28", closes={"AAA": 10.0, "SPY": 600.0}, theses=[_thesis()])
    assert st["n_open"] == 0 and st["n_pending"] == 1
    assert any("missing price for BBB" in r and "PENDING" in r
               for r in b._state()["days"][-1]["reasons"])
    # the parked leg is still demanded by the next fetch...
    assert "BBB" in b.pending_symbols("2026-07-29")
    # ...and once it prices, the thesis OPENS rather than having been dropped
    st2 = b.record("2026-07-29", closes={"AAA": 10.0, "BBB": 20.0, "SPY": 606.0})
    assert st2["n_open"] == 1 and st2["n_pending"] == 0
    pos = b._state()["open"][0]
    assert pos["filed_date"] == "2026-07-27" and pos["entry_date"] == "2026-07-29"
    assert pos["days_pending"] == 1          # the delay is ON THE RECORD, not erased
