"""Survival for the autonomy ledger — Phase-6 rung 0.

THE GAP (D's T-356 Finding 1): `data/state/autonomy_ledger.jsonl` is the record on
which autonomous authority is granted and demoted. It was gitignored, in no S3 sync,
ONE COPY ON ONE MACHINE, actively accruing. `_canonical_root()` made it SINGLE;
nothing made it SURVIVE. The exposure is T-337's single-copy loss — where Arm-1 run
dirs were deleted and two measurements became permanently un-restampable — not
gradual decay. One `rm -rf`, one disk, and the authority record is gone.

AN APPEND-ONLY RECORD NEEDS AN APPEND-ONLY SYNC. This is the whole design. A naive
mirror (`aws s3 cp local remote`) is a REWRITE PATH wearing a backup's clothes: the
night the local file is truncated, emptied, or reordered, the mirror faithfully
destroys the good remote copy too, and the backup becomes the delivery mechanism for
the loss. So every push is classified first, and a local file that is NOT a byte-exact
extension of the remote is REFUSED.

A legitimate rewrite does exist — the 2026-09-14 reconciliation re-sorted the file to
merge stranded rows — and it is precisely the event that deserves a human's attention
rather than an automatic overwrite. Hence `--allow-rewrite`, never used by the nightly
path.

BUCKET VERSIONING IS NOT ASSUMED. `s3:GetBucketVersioning` is denied to this IAM user,
so whether object versions exist could not be verified. The design therefore does not
rely on them: alongside the canonical key, every sync also writes a DATED key, so a
bad overwrite of the canonical object cannot erase what previous days recorded.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

BUCKET = os.getenv("ARCHONDEX_RESULTS_BUCKET", "archondex-results-407539788432")
PROFILE = os.getenv("AWS_PROFILE", "archondex")
KEY_CANON = "ops/phase6/autonomy_ledger.jsonl"
KEY_DAILY_FMT = "ops/phase6/daily/autonomy_ledger_{date}.jsonl"

OK_FIRST = "FIRST_PUSH"
OK_SAME = "ALREADY_CURRENT"
OK_EXTEND = "APPEND_ONLY_EXTENSION"
REFUSE = "REFUSED"


@dataclass
class PushVerdict:
    status: str
    detail: str

    @property
    def ok(self) -> bool:
        return self.status != REFUSE

    @property
    def needs_push(self) -> bool:
        return self.status in (OK_FIRST, OK_EXTEND)


def classify_push(local: bytes, remote: Optional[bytes]) -> PushVerdict:
    """Is pushing `local` over `remote` an APPEND, or a loss of history?

    Pure and total, so the rule that protects the record can be tested without
    touching S3 — the guard is the thing that must never quietly regress.
    """
    if local == b"":
        return PushVerdict(REFUSE, "local ledger is EMPTY — refusing to publish an empty record")
    if remote is None or remote == b"":
        return PushVerdict(OK_FIRST, f"no remote yet — first push of {_rows(local)} row(s)")
    if local == remote:
        return PushVerdict(OK_SAME, f"remote already current ({_rows(local)} rows)")
    if local.startswith(remote):
        return PushVerdict(OK_EXTEND,
                           f"append-only extension: {_rows(remote)} -> {_rows(local)} rows")
    if remote.startswith(local):
        return PushVerdict(REFUSE,
                           f"local is SHORTER than remote ({_rows(local)} vs {_rows(remote)} rows) "
                           f"— the remote holds history this machine has lost")
    return PushVerdict(REFUSE,
                       f"local DIVERGES from remote (local {_rows(local)} rows, remote "
                       f"{_rows(remote)}) — history was rewritten, not appended; pushing would "
                       f"destroy the remote copy")


def _rows(b: bytes) -> int:
    return len([l for l in b.splitlines() if l.strip()])


def _aws_binary() -> Optional[str]:
    """Absolute path to the aws CLI.

    NEVER a bare "aws". launchd runs with PATH=/usr/bin:/bin:/usr/sbin:/sbin, and
    the CLI lives in /opt/homebrew/bin — so a bare name resolves to nothing at
    03:00 while working perfectly from an interactive shell. That is the same
    interpreter-resolution class as the 2026-07-08 bare-`python` bug and the
    2026-09-10 wrapper bootstrap: it fails ONLY on the scheduled path, which is
    the one nobody watches.
    """
    import shutil
    found = shutil.which("aws")
    if found:
        return found
    for cand in ("/opt/homebrew/bin/aws", "/usr/local/bin/aws", "/usr/bin/aws"):
        if os.path.exists(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _aws(args: list[str], **kw) -> subprocess.CompletedProcess:
    exe = _aws_binary()
    if exe is None:
        return subprocess.CompletedProcess(args, 127, b"", b"aws CLI not found on PATH")
    return subprocess.run([exe, *args, "--profile", PROFILE],
                          capture_output=True, timeout=120, **kw)


def read_remote(key: str = KEY_CANON) -> Tuple[Optional[bytes], str]:
    """Remote object bytes, or (None, why). A MISSING object and an UNREACHABLE
    bucket are different facts and are never collapsed into one."""
    r = _aws(["s3", "cp", f"s3://{BUCKET}/{key}", "-"])
    if r.returncode == 0:
        return r.stdout, "ok"
    err = (r.stderr or b"").decode(errors="replace")
    if "NoSuchKey" in err or "Not Found" in err or "does not exist" in err:
        return None, "absent"
    return None, f"unreachable: {err.strip().splitlines()[-1][:120] if err.strip() else 'unknown'}"


def sync(local_path: Path, allow_rewrite: bool = False,
         as_of: Optional[str] = None) -> PushVerdict:
    """Guarded push of the ledger to the canonical key AND a dated key."""
    if not local_path.exists():
        return PushVerdict(REFUSE, f"no local ledger at {local_path}")
    local = local_path.read_bytes()
    remote, why = read_remote()
    if remote is None and why.startswith("unreachable"):
        return PushVerdict(REFUSE, f"cannot read remote — {why}")

    v = classify_push(local, remote)
    if not v.ok and not allow_rewrite:
        return v
    if not v.ok and allow_rewrite:
        v = PushVerdict(OK_EXTEND, f"REWRITE ALLOWED explicitly: {v.detail}")

    if v.status == OK_SAME:
        return v

    date = as_of or datetime.now().strftime("%Y-%m-%d")
    for key in (KEY_CANON, KEY_DAILY_FMT.format(date=date)):
        r = _aws(["s3", "cp", str(local_path), f"s3://{BUCKET}/{key}"])
        if r.returncode != 0:
            return PushVerdict(REFUSE, f"push to {key} FAILED: "
                                       f"{(r.stderr or b'').decode(errors='replace')[:160]}")
    return v


def verify(local_path: Path) -> PushVerdict:
    """Is the remote copy current with local? Run at the START of a session so a
    FAILED push last night is caught within 24h rather than discovered at loss."""
    if not local_path.exists():
        return PushVerdict(REFUSE, f"no local ledger at {local_path}")
    remote, why = read_remote()
    if remote is None:
        return PushVerdict(REFUSE, f"no readable remote copy ({why}) — the record is single-copy")
    local = local_path.read_bytes()
    if local == remote:
        return PushVerdict(OK_SAME, f"remote copy current ({_rows(local)} rows)")
    v = classify_push(local, remote)
    if v.status == OK_EXTEND:
        return PushVerdict(OK_EXTEND, f"remote is behind by "
                                      f"{_rows(local) - _rows(remote)} row(s) — tonight's sync will carry it")
    return v
