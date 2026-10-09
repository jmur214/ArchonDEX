"""The HIGH-row anchor lint — its contract, per the user's approval (2026-09-29):
NO FRICTION WITHOUT AN EXIT.

  1. a failure states EXACTLY how to resolve — close the row, or deliberately
     update the quoted anchor;
  2. open HIGH rows only;
  3. an innocently-moved line is a one-line deliberate fix, never a mystery — and
     never a silent pass (matching is not widened to make it one).
"""
from __future__ import annotations

import json

import pytest

from scripts import doc_lint as dl
from scripts import janitor_nightly as jn

WITNESS = "return self.portfolio.capital"


def _row(tag: str = "HIGH", title: str = "a defect", flagged: str = "2026-09-30",
         anchors: tuple = ()) -> str:
    lines = [f"### [{tag}] {title}", f"- First flagged: {flagged}", "- Status: OPEN"]
    lines += list(anchors)
    return "\n".join(lines) + "\n"


def _health(*rows: str, after: str = "") -> str:
    return ("# Code Health Tracker\n\n## Active Issues\n\n### HIGH\n\n"
            + "\n".join(rows) + "\n## Resolved (last 90 days)\n\n" + after)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A throwaway repo root holding one anchored source file."""
    monkeypatch.setattr(dl, "REPO", tmp_path)
    src = tmp_path / "pkg" / "mod.py"
    src.parent.mkdir()
    src.write_text("def f():\n    x = 1\n    " + WITNESS + "\n")
    return tmp_path


def _check(repo, text: str) -> dl.CheckResult:
    hc = repo / "health_check.md"
    hc.write_text(text)
    return dl.check_high_row_anchors(hc)


ANCHOR = f"- Anchor: `pkg/mod.py:3` contains `{WITNESS}`"


# ── the anchor holds / breaks ────────────────────────────────────────────────

def test_an_anchor_that_still_holds_passes(repo):
    r = _check(repo, _health(_row(anchors=(ANCHOR,))))
    assert r.severity == "PASS", r.details
    assert "1 anchor(s)" in r.summary


def test_a_FIXED_defect_fails_and_says_close_the_row(repo):
    """The case the lint exists for: the witnessing line changed and the text is
    gone — the row must be closed (or deliberately re-quoted)."""
    (repo / "pkg" / "mod.py").write_text("def f():\n    x = 1\n    return self.equity()\n")
    r = _check(repo, _health(_row(anchors=(ANCHOR,))))
    assert r.severity == "FAIL"
    text = "\n".join(r.details)
    assert "close the row" in text and "## Resolved" in text
    assert "(b) not available" in text, "no move to offer — the text appears nowhere"
    assert "line 3 now reads: `return self.equity()`" in text
    assert "health_check.md:10" in text, "the fix must name the exact anchor line to edit"


def test_a_MOVED_line_still_FAILS_but_names_the_one_line_fix(repo):
    """Constraint 3: an innocent move is a deliberate one-line edit — the lint names
    the new line; it does NOT quietly pass because the text exists elsewhere."""
    (repo / "pkg" / "mod.py").write_text("# header\ndef f():\n    x = 1\n    " + WITNESS + "\n")
    r = _check(repo, _health(_row(anchors=(ANCHOR,))))
    assert r.severity == "FAIL", "a moved anchor must not silently pass"
    text = "\n".join(r.details)
    assert "IF the line only MOVED" in text, "a same-text match must not be asserted as a move"
    assert "the same text is at `pkg/mod.py:4` (only there)" in text
    assert "change `:3` to `:4`" in text
    assert "not proof of a move" in text


def test_a_text_that_appears_several_times_lists_them_and_asks_for_the_witness(repo):
    (repo / "pkg" / "mod.py").write_text(f"{WITNESS}\nx = 1\ny = 2\n{WITNESS}\n")
    r = _check(repo, _health(_row(anchors=(ANCHOR,))))
    text = "\n".join(r.details)
    assert r.severity == "FAIL" and "lines 1, 4" in text
    assert "which ONE still witnesses the defect" in text


def test_a_missing_file_fails_with_the_rename_exit(repo):
    r = _check(repo, _health(_row(anchors=("- Anchor: `pkg/gone.py:3` contains `x`",))))
    text = "\n".join(r.details)
    assert r.severity == "FAIL" and "does not exist" in text
    assert "RENAMED" in text and "close the row" in text


def test_a_path_escaping_the_repo_is_not_followed(repo):
    r = _check(repo, _health(_row(anchors=("- Anchor: `../outside.py:1` contains `x`",))))
    assert r.severity == "FAIL" and "does not exist" in "\n".join(r.details)


def test_a_symlinked_repo_root_still_finds_its_files(repo, tmp_path, monkeypatch):
    """Found by the retro-drill: a temp root under macOS's /var -> /private/var
    symlink made EVERY anchor read as 'does not exist'."""
    link = tmp_path.parent / (tmp_path.name + "_link")
    link.symlink_to(repo, target_is_directory=True)
    monkeypatch.setattr(dl, "REPO", link)
    assert _check(repo, _health(_row(anchors=(ANCHOR,)))).severity == "PASS"


def test_a_line_past_end_of_file_fails(repo):
    r = _check(repo, _health(_row(anchors=(f"- Anchor: `pkg/mod.py:99` contains `{WITNESS}`",))))
    assert r.severity == "FAIL" and "(file has 3 lines)" in "\n".join(r.details)


# ── format: fail closed on anything unreadable ──────────────────────────────

def test_a_malformed_anchor_FAILS_rather_than_silently_checking_nothing(repo):
    r = _check(repo, _health(_row(anchors=("- Anchor: pkg/mod.py line 3",))))
    text = "\n".join(r.details)
    assert r.severity == "FAIL" and "not a readable anchor" in text
    assert dl.ANCHOR_FORMAT in text, "the failure must show the exact format"


def test_anchor_none_with_a_reason_is_an_accepted_declaration(repo):
    r = _check(repo, _health(_row(flagged="2026-10-05",
                                  anchors=("- Anchor: none — a doc-only finding",))))
    assert r.severity == "PASS", r.details


def test_anchor_none_WITHOUT_a_reason_is_not_an_exit(repo):
    r = _check(repo, _health(_row(anchors=("- Anchor: none",))))
    assert r.severity == "FAIL", "an opt-out with no reason is a silent opt-out"


def test_a_trailing_note_is_allowed(repo):
    r = _check(repo, _health(_row(anchors=(ANCHOR + " — (1) RR-1",))))
    assert r.severity == "PASS", r.details


# ── scope: open HIGH rows in Active Issues only ─────────────────────────────

BROKEN = "- Anchor: `pkg/mod.py:1` contains `not there`"


@pytest.mark.parametrize("tag", ["HIGH → RESOLVED 2026-08-26", "HIGH → SUPERSEDED 2026-05-09",
                                 "HIGH → CLOSED 2026-04-28", "HIGH NEW → RESOLVED 2026-05-01"])
def test_closed_rows_are_not_checked(repo, tag):
    assert _check(repo, _health(_row(tag=tag, anchors=(BROKEN,)))).severity == "PASS"


def test_a_HISTORICAL_title_closes_the_row(repo):
    r = _check(repo, _health(_row(title="(HISTORICAL — superseded)", anchors=(BROKEN,))))
    assert r.severity == "PASS"


def test_PARTIALLY_RESOLVED_is_still_open(repo):
    r = _check(repo, _health(_row(tag="HIGH → PARTIALLY RESOLVED 2026-05-09", anchors=(BROKEN,))))
    assert r.severity == "FAIL"


def test_medium_and_low_rows_are_out_of_scope(repo):
    r = _check(repo, _health(_row(tag="MEDIUM", anchors=(BROKEN,)),
                             _row(tag="LOW 2026-05-23 by code-health", anchors=(BROKEN,))))
    assert r.severity == "PASS"


def test_rows_outside_active_issues_are_out_of_scope(repo):
    r = _check(repo, _health(after=_row(anchors=(BROKEN,))))
    assert r.severity == "PASS"


# ── unanchored rows: forward-only, WARN, with the exact line to add ─────────

def test_a_new_unanchored_HIGH_row_warns_with_the_line_to_add(repo):
    r = _check(repo, _health(_row(flagged=dl.ANCHOR_ACTIVATION)))
    assert r.severity == "WARN"
    assert dl.ANCHOR_FORMAT in r.details[0] and "Anchor: none" in r.details[0]


def test_old_unanchored_rows_are_grandfathered_silently(repo):
    r = _check(repo, _health(_row(flagged="2026-06-11")))
    assert r.severity == "PASS" and "1 pre-" in r.summary


def test_an_undated_row_cannot_prove_its_age_and_warns(repo):
    text = _health("### [HIGH] no date anywhere\n- Status: OPEN\n")
    assert _check(repo, text).severity == "WARN"


def test_a_title_date_dates_the_row_even_beside_a_data_date(repo):
    """health_check.md:41 on 2026-09-30: no First-flagged line; its title quotes a
    data date (2020-05-08) and ends with the flag date (2026-08-26)."""
    text = _health("### [HIGH] The HMM is BLIND before 2020-05-08 (2026-08-26)\n- Status: x\n")
    assert _check(repo, text).severity == "PASS"


# ── integration: the real entrypoint runs it; the janitor never auto-fixes it ──

def test_main_runs_the_anchor_check(repo, monkeypatch, capsys):
    """Driven through `main()`, not by calling the function: a check that is written
    but unregistered enforces nothing."""
    hc = repo / "health_check.md"
    monkeypatch.setattr(dl, "HEALTH_CHECK", hc)
    hc.write_text(_health(_row(anchors=(BROKEN,))))
    dl.main(["--json"])
    res = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    assert res[dl.ANCHOR_CHECK_NAME]["severity"] == "FAIL"
    hc.write_text(_health(_row(anchors=(ANCHOR,))))
    dl.main(["--json"])
    res = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    assert res[dl.ANCHOR_CHECK_NAME]["severity"] == "PASS"


class _R:
    def __init__(self, out: str, rc: int = 1):
        self.stdout, self.returncode = out, rc


def test_the_janitor_never_treats_a_broken_anchor_as_mechanical(monkeypatch):
    """A broken anchor asks 'fixed or moved?' — a judgment. Handing it to the fix
    phase would let an autonomous session re-point anchors or close HIGH rows."""
    out = (f"[  ok] something: fine\n"
           f"[FAIL] {dl.ANCHOR_CHECK_NAME}: 1 anchor(s) on open HIGH rows no longer hold\n")
    monkeypatch.setattr(jn, "_run", lambda cmd, **kw: _R(out))
    c = jn.check_doc_lint()
    assert not c.ok and not c.mechanical


def test_other_doc_drift_stays_mechanical(monkeypatch):
    out = "[FAIL] TASK_LEDGER rows have all required columns: 1 bad row\n"
    monkeypatch.setattr(jn, "_run", lambda cmd, **kw: _R(out))
    c = jn.check_doc_lint()
    assert not c.ok and c.mechanical
