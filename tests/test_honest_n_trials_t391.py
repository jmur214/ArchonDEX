"""T-391 locks: the honest-N gate counts standalone-harness trials, and fails closed on the record.

Proposal: docs/Sources/proposal_honest_n_trials_recorder_t391_2026-11-13.md (§1.7 lists these tests).
Every test drives the real code: `mbl_gate` (the gate), `scripts.honest_n_trials` (the recorder + the lint)
and `scripts.honest_n_pin` (the pin's verify/write). The real registry is only ever read from a COPY in
tmp_path, never in place. Each lock is proven by reversion (the proposal's §2 records the harness and the
first failing line per mode).
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

import core.measurement.mbl_gate as mbl
from core.measurement.mbl_gate import HonestNUnavailableError
from scripts import honest_n_trials as hnt
from scripts.honest_n_pin import main as pin_main, write_pin
from tests._honest_n_trials_fixture import FIXTURE_HEADER, fixture_row, write_fixture_trials_record

ROOT = Path(__file__).resolve().parents[1]
REAL_OBS = ROOT / "data" / "observability"
REAL_PIN = ROOT / "config" / "honest_n_pin.json"
REAL_RECORD = ROOT / "config" / "honest_n_trials.json"
RHO, COMP = 0.43, 0.16


# ----------------------------------------------------------------------------- fixtures
def _registry(path: Path, n_plain: int, ledger: dict | None = None) -> Path:
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, snapshot_at TEXT, source TEXT)")
    c.executemany("INSERT INTO runs VALUES (?, NULL, NULL)", [(f"r{i}",) for i in range(n_plain)])
    for lid, k in (ledger or {}).items():
        c.executemany("INSERT INTO runs VALUES (?, '2026-08-06', ?)",
                      [(f"ledger:{lid}:{i}", f"ledger:{lid}") for i in range(k)])
    c.commit(); c.close()
    return path


def _setup(tmp_path: Path, rows: list, ledger: dict | None = None, n_plain: int = 100,
           pin_trials: bool = False):
    obs = tmp_path / "obs"; obs.mkdir()
    cfg = tmp_path / "config"; cfg.mkdir()
    reg = _registry(obs / "run_registry.sqlite", n_plain, ledger)
    art = obs / "n_effective_2026-09-30.json"
    art.write_text(json.dumps({"funnel": {"after_dedupe": 50},
                               "gate_inputs": {"rho_bar": RHO, "onc_compression": COMP}}))
    rec = write_fixture_trials_record(cfg, rows)
    pin = cfg / "honest_n_pin.json"
    write_pin(art.name, artifact_dir=obs, db_path=reg, pin_path=pin,
              trials_path=rec if pin_trials else None)
    return obs, reg, rec, pin


def _gate(obs: Path, reg: Path, pin: Path) -> float:
    return mbl.compute_n_effective_correlated(reg, artifact_dir=obs, pin_path=pin)


def _registry_part(n_raw: int) -> float:
    return max(mbl.n_eff_equicorrelated(n_raw, RHO), max(mbl.N_EFF_FLOOR, min(float(n_raw), n_raw * COMP)))


def _raw_record(path: Path, rows: list, unresolved: list | None = None, **over) -> Path:
    """A record with a CORRECT digest, so the row/shape checks (not the digest) are what is exercised."""
    unresolved = unresolved or []
    rec = {"schema": mbl.TRIALS_SCHEMA, "activation_date": "2026-11-13", "rows": rows,
           "unresolved": unresolved, "rows_sha256": mbl.trials_digest(rows, unresolved)}
    rec.update(over)
    path.write_text(json.dumps(rec))
    return path


# ----------------------------------------------------------------------------- §1.7(1) the real inputs, from COPIES
def test_the_real_record_and_a_COPY_of_the_real_registry_gate_to_registry_plus_53(tmp_path):
    missing = [n for n in ("run_registry.sqlite", "n_effective_2026-09-30.json") if not (REAL_OBS / n).is_file()]
    if missing:
        pytest.skip(f"the pinned honest-N files are not on this host: {missing}")
    obs = tmp_path / "obs"; obs.mkdir()
    cfg = tmp_path / "config"; cfg.mkdir()
    for n in ("run_registry.sqlite", "n_effective_2026-09-30.json"):
        shutil.copyfile(REAL_OBS / n, obs / n)
    shutil.copyfile(REAL_PIN, cfg / REAL_PIN.name)
    shutil.copyfile(REAL_RECORD, cfg / REAL_RECORD.name)
    b = mbl.honest_n_breakdown(obs / "run_registry.sqlite", artifact_dir=obs, pin_path=cfg / REAL_PIN.name)
    assert b["n_raw_registry"] == 231 and b["n_standalone"] == 53 and b["n_raw_total"] == 284
    assert b["n_eff_registry"] == pytest.approx(36.9240, abs=1e-3)
    assert b["n_eff"] == pytest.approx(36.9240 + 53, abs=1e-3)
    assert b["n_eff_ruling_9_2_all"] == pytest.approx(40.2807 + 231 + 53, abs=1e-3)
    assert b["executed_population"] == 252 and b["n_unresolved_items"] == 12
    assert _gate(obs, obs / "run_registry.sqlite", cfg / REAL_PIN.name) == pytest.approx(b["n_eff"])


def test_the_committed_record_is_valid_and_mirrors_exactly_the_registrys_26_ledger_tasks():
    rec = mbl.load_trials_record(REAL_RECORD)
    reg_rows = [r for r in rec["rows"] if r["counted_in"] == "registry_ledger"]
    assert len({r["ledger_id"] for r in reg_rows}) == 26 and sum(r["n_trials"] for r in reg_rows) == 106
    assert mbl.standalone_trials_total(rec) == 53
    assert rec["activation_date"] == "2026-11-13"


# ----------------------------------------------------------------------------- §1.7(2) the record itself
def test_an_ABSENT_record_is_refused_not_read_as_zero(tmp_path):
    obs, reg, rec, pin = _setup(tmp_path, [fixture_row()])
    rec.rename(rec.with_name("moved_aside.json"))
    with pytest.raises(HonestNUnavailableError, match="absent or unreadable"):
        _gate(obs, reg, pin)


def test_an_EMPTY_record_is_refused(tmp_path):
    obs, reg, rec, pin = _setup(tmp_path, [fixture_row()])
    _raw_record(rec, [])
    with pytest.raises(HonestNUnavailableError, match="holds no rows"):
        _gate(obs, reg, pin)


def test_a_wrong_schema_is_refused(tmp_path):
    obs, reg, rec, pin = _setup(tmp_path, [fixture_row()])
    _raw_record(rec, [fixture_row()], schema="honest_n_trials/v0")
    with pytest.raises(HonestNUnavailableError, match="schema"):
        _gate(obs, reg, pin)


def test_a_HAND_EDIT_that_bypasses_the_recorder_is_refused_by_the_digest(tmp_path):
    obs, reg, rec, pin = _setup(tmp_path, [fixture_row(n_trials=3)])
    text = rec.read_text().replace('"n_trials": 3', '"n_trials": 0')      # quietly lower S
    assert text != rec.read_text()
    rec.write_text(text)
    with pytest.raises(HonestNUnavailableError, match="rows_sha256"):
        _gate(obs, reg, pin)


# ----------------------------------------------------------------------------- §1.7(3) malformed rows
@pytest.mark.parametrize("n_trials", [-1, True, 1.0, "2"])
def test_a_malformed_n_trials_is_refused(tmp_path, n_trials):
    obs, reg, rec, pin = _setup(tmp_path, [fixture_row()])
    row = fixture_row(); row["n_trials"] = n_trials
    _raw_record(rec, [row])
    with pytest.raises(HonestNUnavailableError, match="n_trials must be an int"):
        _gate(obs, reg, pin)


def test_an_unknown_counted_in_is_refused(tmp_path):
    obs, reg, rec, pin = _setup(tmp_path, [fixture_row()])
    _raw_record(rec, [fixture_row(counted_in="elsewhere")])
    with pytest.raises(HonestNUnavailableError, match="counted_in"):
        _gate(obs, reg, pin)


def test_a_duplicate_trial_id_is_refused(tmp_path):
    obs, reg, rec, pin = _setup(tmp_path, [fixture_row()])
    _raw_record(rec, [fixture_row("T-1", 1), fixture_row("T-1", 1)])
    with pytest.raises(HonestNUnavailableError, match="duplicate trial_id"):
        _gate(obs, reg, pin)


# ----------------------------------------------------------------------------- §1.7(4) the double-count lock
def test_registry_ledger_rows_are_mirrored_never_summed_again(tmp_path):
    rows = [fixture_row("T-9", 4, "registry_ledger", "T-9"), fixture_row("S-1", 3)]
    obs, reg, _, pin = _setup(tmp_path, rows, ledger={"T-9": 4}, n_plain=100)
    assert _gate(obs, reg, pin) == pytest.approx(_registry_part(104) + 3)


@pytest.mark.parametrize("record_k, registry", [(3, {"T-9": 4}), (5, {"T-9": 4}), (4, {"T-9": 4, "T-10": 1})])
def test_a_record_that_disagrees_with_the_registrys_ledger_rows_is_refused(tmp_path, record_k, registry):
    rows = [fixture_row("T-9", record_k, "registry_ledger", "T-9"), fixture_row("S-1", 3)]
    obs, reg, _, pin = _setup(tmp_path, rows, ledger=registry)
    with pytest.raises(HonestNUnavailableError, match="disagree"):
        _gate(obs, reg, pin)


# ----------------------------------------------------------------------------- §1.7(5) the pin
def test_once_PINNED_a_changed_record_is_refused_until_re_pinned(tmp_path):
    obs, reg, rec, pin = _setup(tmp_path, [fixture_row("S-1", 2)], pin_trials=True)
    assert json.loads(pin.read_text())["schema"] == "honest_n_pin/v2"
    assert _gate(obs, reg, pin) == pytest.approx(_registry_part(100) + 2)
    hnt.write_record(rec, FIXTURE_HEADER, [fixture_row("S-1", 2), fixture_row("S-2", 1)], [])
    with pytest.raises(HonestNUnavailableError, match="does not match its pin"):
        _gate(obs, reg, pin)
    write_pin("n_effective_2026-09-30.json", artifact_dir=obs, db_path=reg, pin_path=pin, replace=True,
              trials_path=rec)                                            # the reviewed re-pin
    assert _gate(obs, reg, pin) == pytest.approx(_registry_part(100) + 3)


def test_write_pin_refuses_a_record_the_gate_could_not_combine(tmp_path):
    rows = [fixture_row("T-9", 3, "registry_ledger", "T-9")]
    with pytest.raises(HonestNUnavailableError, match="disagree"):
        _setup(tmp_path, rows, ledger={"T-9": 4}, pin_trials=True)


def test_verify_exits_3_on_a_planted_byte_in_a_pinned_record(tmp_path, monkeypatch, capsys):
    obs, reg, rec, pin = _setup(tmp_path, [fixture_row("S-1", 2)], pin_trials=True)
    monkeypatch.setattr(mbl, "DEFAULT_ARTIFACT_DIR", obs)
    monkeypatch.setattr(mbl, "DEFAULT_DB_PATH", reg)
    monkeypatch.setattr(mbl, "DEFAULT_PIN_PATH", pin)
    assert pin_main(["--verify"]) == 0 and "matches its pinned sha256" in capsys.readouterr().out
    rec.write_text(rec.read_text() + " ")                                  # one byte, digest unaffected
    assert pin_main(["--verify"]) == 3
    assert "standalone-trials record" in capsys.readouterr().out


def test_verify_exits_3_when_an_unpinned_record_disagrees_with_the_registry(tmp_path, monkeypatch, capsys):
    obs, reg, rec, pin = _setup(tmp_path, [fixture_row("S-1", 2)])
    monkeypatch.setattr(mbl, "DEFAULT_ARTIFACT_DIR", obs)
    monkeypatch.setattr(mbl, "DEFAULT_DB_PATH", reg)
    monkeypatch.setattr(mbl, "DEFAULT_PIN_PATH", pin)
    assert pin_main(["--verify"]) == 0 and "NOT YET PINNED" in capsys.readouterr().out
    hnt.write_record(rec, FIXTURE_HEADER, [fixture_row("T-9", 1, "registry_ledger", "T-9")], [])
    assert pin_main(["--verify"]) == 3 and "disagree" in capsys.readouterr().out


# ----------------------------------------------------------------------------- the production entry points
def test_the_no_argument_production_call_counts_the_record(tmp_path, monkeypatch):
    """Discovery's Gate 8 and check_mbl_gate call compute_n_effective_correlated() with NO arguments."""
    obs, reg, _, pin = _setup(tmp_path, [fixture_row("S-1", 7)])
    monkeypatch.setattr(mbl, "DEFAULT_ARTIFACT_DIR", obs)
    monkeypatch.setattr(mbl, "DEFAULT_DB_PATH", reg)
    monkeypatch.setattr(mbl, "DEFAULT_PIN_PATH", pin)
    want = _registry_part(100) + 7
    assert mbl.compute_n_effective_correlated() == pytest.approx(want)
    assert mbl.check_mbl_gate(t_years=26.0)["n_effective"] == pytest.approx(want, abs=1e-4)
    info = mbl.resolve_cycle_n_trials(3, db_path=reg, artifact_dir=obs, pin_path=pin)
    assert info["n_trials"] == pytest.approx(want) and info["breakdown"]["n_standalone"] == 7


@pytest.mark.parametrize("method", mbl.METHODS)
def test_standalone_trials_enter_at_RAW_under_every_method(tmp_path, method):
    obs, reg, _, pin = _setup(tmp_path, [fixture_row("S-1", 11)])
    b = mbl.honest_n_breakdown(reg, method=method, artifact_dir=obs, pin_path=pin)
    assert b["n_eff"] == pytest.approx(b["n_eff_registry"] + 11)
    assert b["n_eff_ruling_9_2_all"] >= b["n_eff"], "R3 can never be looser than R2"


def test_an_explicit_artifact_path_counts_the_record_only_when_named(tmp_path):
    obs, reg, rec, _ = _setup(tmp_path, [fixture_row("S-1", 5)])
    art = obs / "n_effective_2026-09-30.json"
    assert mbl.compute_n_effective_correlated(reg, artifact_path=art) == pytest.approx(_registry_part(100))
    assert mbl.compute_n_effective_correlated(reg, artifact_path=art, trials_path=rec) == \
        pytest.approx(_registry_part(100) + 5)


def test_the_gate_never_writes_the_registry_or_the_record(tmp_path):
    obs, reg, rec, pin = _setup(tmp_path, [fixture_row("S-1", 1)])
    before = (reg.read_bytes(), rec.read_bytes())
    _gate(obs, reg, pin)
    assert (reg.read_bytes(), rec.read_bytes()) == before


# ----------------------------------------------------------------------------- §1.7(6) the recorder
def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "docs" / "Audit").mkdir(parents=True)
    (root / "docs" / "Audit" / "x_verdict.md").write_text("line 1\nN_trials +2.\n")
    (root / "docs" / "Audit" / "x_prereg.md").write_text("prereg\n")
    return root


def _rec_kwargs(**over):
    kw = dict(trial_id="T-900", task_id="T-900", date="2026-11-14", n_trials=2, family="f", substrate="s",
              prereg="docs/Audit/x_prereg.md", verdict="docs/Audit/x_verdict.md",
              source="docs/Audit/x_verdict.md:2", ledger_id="T-900")
    kw.update(over)
    return kw


def test_the_recorder_appends_ONE_row_the_gate_then_counts(tmp_path):
    obs, reg, rec, pin = _setup(tmp_path, [fixture_row("S-1", 1)])
    root = _repo(tmp_path)
    before = _gate(obs, reg, pin)
    row = hnt.record_trial(record_path=rec, root=root, **_rec_kwargs())
    assert row["counted_in"] == "standalone"
    assert _gate(obs, reg, pin) == pytest.approx(before + 2)
    assert len(mbl.load_trials_record(rec)["rows"]) == 2


@pytest.mark.parametrize("over, match", [
    ({"trial_id": "S-1"}, "already recorded"),
    ({"verdict": "docs/Audit/absent.md"}, "does not exist"),
    ({"prereg": "../outside.md"}, "without '..'"),
    ({"source": "docs/Audit/x_verdict.md:9"}, "outside"),
    ({"source": "docs/Audit/x_verdict.md"}, "path:line"),
    ({"date": "14 Nov 2026"}, "YYYY-MM-DD"),
    ({"n_trials": -1}, "int >= 0"),
])
def test_the_recorder_refuses_what_would_make_the_record_wrong_or_uncitable(tmp_path, over, match):
    _, _, rec, _ = _setup(tmp_path, [fixture_row("S-1", 1)])
    before = rec.read_bytes()
    with pytest.raises(hnt.RecordError, match=match):
        hnt.record_trial(record_path=rec, root=_repo(tmp_path), **_rec_kwargs(**over))
    assert rec.read_bytes() == before


# ----------------------------------------------------------------------------- §1.7(7) the lint
_LEDGER_HEAD = ("| T-ID | date | title | status | cells_attempted | cells_succeeded | outcome | audit doc |\n"
                "|---|---|---|---|---|---|---|---|\n")


def _ledger(tmp_path: Path, *rows: str) -> Path:
    p = tmp_path / "TASK_LEDGER.md"
    p.write_text(_LEDGER_HEAD + "\n".join(rows) + "\n")
    return p


def _row(tid: str, date: str, status: str, outcome: str, doc: str = "`x_verdict.md`") -> str:
    return f"| {tid} | {date} | t | {status} | — | — | {outcome} | {doc} |"


def _lint(tmp_path: Path, rows: list, *ledger_rows: str) -> list:
    rec = _raw_record(tmp_path / "rec.json", rows)
    return hnt.lint(mbl.load_trials_record(rec), hnt.parse_ledger(_ledger(tmp_path, *ledger_rows)))


def test_lint_passes_a_clean_ledger(tmp_path):
    rows = [fixture_row("T-5", 2, ledger_id="T-5"), fixture_row("T-6", 0, ledger_id="T-6")]
    assert _lint(tmp_path, rows,
                 _row("T-5", "2026-11-20", "refuted", "H0. N_trials +2."),
                 _row("T-6", "2026-11-21", "superseded", "closed without running (N_trials 0)"),
                 _row("T-7", "2026-11-22", "done", "infra, no verdict", doc="`proposal_x.md`")) == []


def test_lint_flags_a_declared_N_with_no_record_row(tmp_path):
    f = _lint(tmp_path, [fixture_row()], _row("T-5", "2026-06-01", "refuted", "N += 3"))
    assert any("T-5 declares N_trials 3" in x and "holds 0" in x for x in f)


def test_lint_flags_a_record_that_falls_SHORT_of_the_ledger_but_allows_more(tmp_path):
    f = _lint(tmp_path, [fixture_row("T-5", 1, ledger_id="T-5")], _row("T-5", "2026-06-01", "refuted", "N+=2"))
    assert any("holds 1" in x for x in f)
    assert _lint(tmp_path, [fixture_row("T-5", 6, ledger_id="T-5")],
                 _row("T-5", "2026-06-01", "refuted", "n_trials_consumed 4")) == []


def test_lint_forward_rule_a_verdict_must_STATE_N(tmp_path):
    f = _lint(tmp_path, [fixture_row("T-5", 1, ledger_id="T-5")],
              _row("T-5", "2026-11-20", "refuted", "H0, nothing said about trials"))
    assert any("without stating N_trials" in x for x in f)


def test_lint_forward_rule_a_verdict_needs_a_record_row_even_at_zero(tmp_path):
    f = _lint(tmp_path, [fixture_row()], _row("T-5", "2026-11-20", "done", "N_trials 0", doc="`prereg_x.md`"))
    assert any("has no trials-record row" in x for x in f)


def test_lint_grandfathers_pre_activation_rows_that_state_no_N(tmp_path):
    assert _lint(tmp_path, [fixture_row()], _row("T-5", "2026-07-02", "refuted", "H0, no N line")) == []


def test_lint_flags_a_dangling_ledger_id(tmp_path):
    f = _lint(tmp_path, [fixture_row("T-5", 1, ledger_id="T-404")], _row("T-5", "2026-06-01", "done", "x"))
    assert any("T-404" in x and "no TASK_LEDGER.md row" in x for x in f)


def test_the_lint_passes_on_the_REAL_ledger_and_the_REAL_record(capsys):
    """The enforcement: the full suite fails the day a ledger row declares N the record lacks, or a forward
    verdict closes without stating N. (The registry cross-check runs read-only where the registry exists.)"""
    assert hnt.check() == 0, capsys.readouterr().out
