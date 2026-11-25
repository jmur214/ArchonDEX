"""T-418: the intraday options capture wrapper (scripts/run_options_intraday.sh).

Driven for real under the launchd PATH with a stub interpreter, aws and osascript: the
in-window capture, a failed capture's alarm, a late firing (a miss, never an email), the
hard bound, and the drill. The plist and the launchd registry are checked against each other.
"""
from __future__ import annotations

import os
import plistlib
import stat
import subprocess
import time
from pathlib import Path

import pytest

from scripts.launchd_canon import LIVE_JOBS

REPO = Path(__file__).resolve().parent.parent
WRAPPER = REPO / "scripts/run_options_intraday.sh"
PLIST = REPO / "scripts/launchd/com.archondex.options-intraday.plist"
LABEL = "com.archondex.options-intraday"


def _run(tmp_path: Path, body: str, now_et: str, *, drill: bool = False,
         timeout_s: str = "30") -> tuple[str, str]:
    repo, stubs = tmp_path / "repo", tmp_path / "stubs"
    (repo / ".venv/bin").mkdir(parents=True)
    stubs.mkdir()
    calls = tmp_path / "calls.txt"
    calls.write_text("")
    py = repo / ".venv/bin/python"
    py.write_text(f'#!/bin/bash\necho "PY $*" >> "{calls}"\n{body}\n')
    for name in ("aws", "osascript"):
        (stubs / name).write_text(f'#!/bin/bash\necho "{name.upper()} $*" >> "{calls}"\n')
    for f in (py, stubs / "aws", stubs / "osascript"):
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    src = WRAPPER.read_text()
    real_repo = 'REPO="/Users/jacksonmurphy/Dev/trading_machine-2"'
    assert src.count(real_repo) == 1
    copy = src.replace(real_repo, f'REPO="{repo}"')
    for p in ("/opt/homebrew/bin/aws", "/usr/local/bin/aws", "/usr/bin/aws"):
        copy = copy.replace(p, str(stubs / "aws"))
    wrapper = tmp_path / "wrapper.sh"
    wrapper.write_text(copy)
    env = {**os.environ, "PATH": f"{stubs}:/usr/bin:/bin:/usr/sbin:/sbin",
           "ARCHONDEX_OPTIONS_TIMEOUT_S": timeout_s, "ARCHONDEX_INTRADAY_NOW_ET": now_et}
    env.pop("ARCHONDEX_ALARM_DRILL", None)
    if drill:
        env["ARCHONDEX_ALARM_DRILL"] = "1"
    subprocess.run(["/bin/bash", str(wrapper)], env=env, check=True, timeout=60)
    logs = list((repo / "data/macro_data/alt/logs").glob("options_intraday_*.log"))
    assert len(logs) == 1
    return logs[0].read_text(), calls.read_text()


def test_in_the_window_it_runs_the_INTRADAY_slot_and_stays_quiet(tmp_path: Path) -> None:
    log, calls = _run(tmp_path, "exit 0", "1230")
    assert "PY scripts/archive_options_snapshots.py --slot near_close" in calls
    assert "options_intraday=0" in log and "FAILED" not in log and "MISSED" not in log
    assert "AWS" not in calls and "OSASCRIPT" not in calls


@pytest.mark.parametrize("rc", ["1", "2"])
def test_a_failed_capture_alarms_on_both_channels(tmp_path: Path, rc: str) -> None:
    log, calls = _run(tmp_path, f"exit {rc}", "1230")
    assert f"OPTIONS_INTRADAY_FAILED rc={rc}" in log
    assert "AWS sns publish" in calls and f"rc={rc}" in calls and "OSASCRIPT" in calls


@pytest.mark.parametrize("now_et", ["0934", "1256", "1830", "0005"])
def test_a_LATE_firing_is_a_logged_miss_with_no_capture_and_no_email(tmp_path: Path,
                                                                    now_et: str) -> None:
    log, calls = _run(tmp_path, "exit 0", now_et)
    assert "OPTIONS_INTRADAY_MISSED" in log and "FAILED" not in log
    assert "PY " not in calls, "outside the session the archiver must not run"
    assert "AWS" not in calls and "OSASCRIPT" in calls


@pytest.mark.parametrize("now_et", ["0935", "0959", "1255"])
def test_the_window_edges_capture(tmp_path: Path, now_et: str) -> None:
    """0959 also proves a leading zero is not read as octal."""
    log, calls = _run(tmp_path, "exit 0", now_et)
    assert "PY scripts/archive_options_snapshots.py --slot near_close" in calls
    assert "MISSED" not in log


def test_a_HUNG_capture_is_killed_and_alarms(tmp_path: Path) -> None:
    t0 = time.monotonic()
    log, calls = _run(tmp_path, "exec /bin/sleep 45", "1230", timeout_s="1")
    assert time.monotonic() - t0 < 20
    assert "options_intraday=142" in log and "AWS sns publish" in calls


def test_the_drill_takes_the_alarm_branch_and_runs_nothing(tmp_path: Path) -> None:
    log, calls = _run(tmp_path, "exit 0", "1830", drill=True)
    assert "options_intraday=99" in log and "OPTIONS_INTRADAY_FAILED" in log
    assert "PY " not in calls and "AWS sns publish" in calls


def test_the_plist_fires_on_weekdays_inside_every_session_and_is_registered() -> None:
    pl = plistlib.loads(PLIST.read_bytes())
    assert pl["Label"] == LABEL and LABEL in LIVE_JOBS
    assert pl["ProgramArguments"] == ["/bin/bash", str(WRAPPER)]
    slots = pl["StartCalendarInterval"]
    assert sorted(s["Weekday"] for s in slots) == [1, 2, 3, 4, 5]
    # 11:30 Central = 12:30 Eastern: before the 13:00 ET half-day close.
    assert {(s["Hour"], s["Minute"]) for s in slots} == {(11, 30)}
    assert "ARCHONDEX_ALARM_DRILL" not in PLIST.read_text()
    assert "ARCHONDEX_INTRADAY_NOW_ET" not in PLIST.read_text()
