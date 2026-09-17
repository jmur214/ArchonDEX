"""The loud-failure channels must be able to RUN — launchd PATH resolution.

The archiver's SNS alarm is the channel meant to catch silent capture loss. It fires
only when an archiver fails, so it had never been exercised on the scheduled path —
and a bare `aws` resolves to nothing under launchd's PATH. The alarm was dead for as
long as it had existed, and nothing could have revealed that except a real failure,
which is the worst possible moment to find out.

Measured, not inferred (2026-09-16, under `env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin`):
  bare `aws sns publish`            -> "command not found", rc=127
  /opt/homebrew/bin/aws sts ...     -> rc=0
  the real wrapper, drill-forced    -> SNS MessageId 493c50f6-a141-5145-835a-33d3eb9f1058
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LAUNCHD_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
WRAPPERS = ("scripts/run_altdata_archivers.sh", "scripts/run_janitor_nightly.sh")


def _resolvable_under_launchd(cmd: str) -> bool:
    return shutil.which(cmd, path=LAUNCHD_PATH) is not None


@pytest.mark.parametrize("wrapper", WRAPPERS)
def test_no_wrapper_invokes_aws_by_BARE_NAME(wrapper):
    """The whole class, in one assertion."""
    sh = (REPO / wrapper).read_text()
    code = "\n".join(l for l in sh.splitlines() if not l.lstrip().startswith("#"))
    assert not re.search(r"(^|[\s;&|(])aws\s+(sns|s3|sts)\b", code), \
        f"{wrapper} invokes aws by bare name; launchd PATH is {LAUNCHD_PATH}"
    assert '"$AWS"' in code, f"{wrapper} must use the resolved binary"


@pytest.mark.parametrize("wrapper", WRAPPERS)
def test_each_wrapper_resolves_aws_absolutely_with_a_homebrew_fallback(wrapper):
    sh = (REPO / wrapper).read_text()
    assert 'AWS="$(command -v aws' in sh
    assert "/opt/homebrew/bin/aws" in sh, "the actual install location must be a fallback"


def test_aws_is_genuinely_NOT_on_the_launchd_path():
    """The premise of all of the above. If this ever fails, the fix is still correct
    but the URGENCY has changed and the reasoning should be re-read."""
    if shutil.which("aws") is None:
        pytest.skip("aws CLI not installed in this environment")
    assert not _resolvable_under_launchd("aws"), \
        "aws now resolves under launchd PATH — re-read the alarm-channel reasoning"


@pytest.mark.parametrize("cmd", ["git", "osascript", "launchctl", "date", "shasum"])
def test_the_other_binaries_the_launchd_surface_uses_DO_resolve(cmd):
    """The sweep's result, pinned: `aws` was the only offender in the launchd-invoked
    surface — two instances of one class, and no third."""
    assert _resolvable_under_launchd(cmd), f"{cmd} does not resolve under launchd PATH"


def test_the_archiver_alarm_can_be_DRILLED_without_a_real_failure():
    """An alarm you cannot exercise is the defect. This channel was dead for months
    precisely because testing it required something to break first, so nobody ever
    did — the hook makes a drill possible on an ordinary Tuesday."""
    sh = (REPO / "scripts/run_altdata_archivers.sh").read_text()
    assert "ARCHONDEX_ALARM_DRILL" in sh
    assert "archivers NOT run, no data touched" in sh, "a drill must not touch data"
    assert "RC1=99" in sh, "the drill must take the real failure branch, not a fake one"


def test_the_drill_is_OPT_IN_so_a_scheduled_run_never_takes_it():
    sh = (REPO / "scripts/run_altdata_archivers.sh").read_text()
    assert 'if [ -n "${ARCHONDEX_ALARM_DRILL:-}" ]; then' in sh
    assert "ARCHONDEX_ALARM_DRILL" not in (REPO / "ops/com.archondex.janitor.plist").read_text()
