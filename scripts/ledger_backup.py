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
import sqlite3
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple

BUCKET = os.getenv("ARCHONDEX_RESULTS_BUCKET", "archondex-results-407539788432")
PROFILE = os.getenv("AWS_PROFILE", "archondex")
KEY_CANON = "ops/phase6/autonomy_ledger.jsonl"
KEY_DAILY_FMT = "ops/phase6/daily/autonomy_ledger_{date}.jsonl"

OK_FIRST = "FIRST_PUSH"
OK_SAME = "ALREADY_CURRENT"
OK_EXTEND = "APPEND_ONLY_EXTENSION"
REFUSE = "REFUSED"
DEFERRED = "DEFERRED"        # the network was not reachable — try again next run

# The host is a LAPTOP. The 03:00 job fires on time (03:07, 03:07, 03:14 on
# 09-24/25/26) but Wi-Fi has not associated yet, so the first S3 call fails with
# "Could not connect to the endpoint". That is not a broken backup and must not be
# reported as one: an alarm that fires every night the laptop wakes slowly is the
# cry-wolf failure this program keeps closing. Retry briefly, then DEFER — the next
# run's verify() catches a remote that is genuinely behind.
NET_RETRIES = 3
NET_BACKOFF_S = 20


@dataclass
class PushVerdict:
    status: str
    detail: str

    @property
    def ok(self) -> bool:
        """DEFERRED counts as ok: a transient network is not a backup failure.
        The next run's verify() is what catches a remote that is really behind."""
        return self.status not in (REFUSE,)

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


def _read_remote_retrying(key: str) -> Tuple[Optional[bytes], str]:
    """read_remote with the laptop's wake-time retry: an unreachable network is retried
    NET_RETRIES times before the caller DEFERS (never collapsed into 'absent')."""
    remote, why = None, ""
    for attempt in range(1, NET_RETRIES + 1):
        remote, why = read_remote(key)
        if not (remote is None and why.startswith("unreachable")):
            break
        if attempt < NET_RETRIES:
            time.sleep(NET_BACKOFF_S)
    return remote, why


def sync(local_path: Path, allow_rewrite: bool = False,
         as_of: Optional[str] = None) -> PushVerdict:
    """Guarded push of the ledger to the canonical key AND a dated key."""
    if not local_path.exists():
        return PushVerdict(REFUSE, f"no local ledger at {local_path}")
    local = local_path.read_bytes()
    remote, why = _read_remote_retrying(KEY_CANON)
    if remote is None and why.startswith("unreachable"):
        # DEFER, not FAIL. The record is not at risk from one missed push: the local
        # file is intact and append-only, and the next run's verify() reports a remote
        # that is genuinely behind. What IS at risk from a nightly false alarm is
        # anyone still reading the alarms.
        return PushVerdict(DEFERRED,
                           f"network unreachable after {NET_RETRIES} attempts ({why}); "
                           f"local record intact, next run will carry it")

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


# ── data/observability: RR-3's fail-closed honest-N inputs (T-356b, 2026-10-13) ───────
#
# The same single-copy exposure as the ledger, in a different shape. Since RR-3 these
# files ARE Discovery's N: the run registry (N_raw) and the dated ρ̄ artifact
# (`gate_inputs`). Both are gitignored, one copy on one machine.
#
# THE REGISTRY IS JUDGED ON WHAT THE GATE COUNTS, NOT ON BYTES. It is SQLite, and every
# rebuild rewrites the file, so the ledger's byte-extension rule cannot apply. The rule
# is on the set of `run_id`s: a local registry that lacks ANY run the remote holds is
# REFUSED. That is precisely the rebuild-after-loss D's census names — `rebuild()`
# re-reads whatever sits in local trade_logs that day, and 125 run rows' directories
# exist nowhere, so the rebuilt N is SMALLER and the gate LOOSER, with no alarm. The
# backup must not be the thing that publishes that smaller N over the good copy.
#
# THE ρ̄ ARTIFACTS ARE IMMUTABLE BY NAME. `n_effective_<date>.json` is a dated
# measurement: a first copy is pushed, an identical one is current, a CHANGED one is
# REFUSED (regenerate under a new date, or review and allow the rewrite).
#
# The registry is pushed as a CONSISTENT SNAPSHOT (SQLite's backup API, source opened
# read-only), never the live file: a copy taken mid-write would be a torn database.

OBS_PREFIX = "ops/observability"
OBS_REGISTRY = "run_registry.sqlite"
KEY_REGISTRY = f"{OBS_PREFIX}/{OBS_REGISTRY}"
KEY_REGISTRY_DAILY_FMT = f"{OBS_PREFIX}/daily/run_registry_{{date}}.sqlite"
KEY_ARTIFACT_FMT = f"{OBS_PREFIX}/{{name}}"
ARTIFACT_GLOB = "n_effective_*.json"


def classify_registry(local_ids: Set[str], remote_ids: Optional[Set[str]],
                      same_content: bool) -> PushVerdict:
    """Is pushing the local registry over the remote one safe for the gate's N?

    Pure and total, like classify_push: the rule that protects N is tested without S3.
    """
    if not local_ids:
        return PushVerdict(REFUSE, "local run registry has NO rows — refusing to publish an empty N")
    if remote_ids is None:
        return PushVerdict(OK_FIRST, f"no remote yet — first push of {len(local_ids)} run(s)")
    if same_content:
        return PushVerdict(OK_SAME, f"remote registry already current ({len(local_ids)} runs)")
    lost = remote_ids - local_ids
    if lost:
        return PushVerdict(
            REFUSE,
            f"local registry LACKS {len(lost)} run(s) the remote holds ({len(local_ids)} local "
            f"vs {len(remote_ids)} remote) — a rebuild after loss hands the gate a SMALLER N; "
            f"pushing would overwrite the only copy of those rows")
    added = len(local_ids - remote_ids)
    if added:
        return PushVerdict(OK_EXTEND, f"registry extended: {len(remote_ids)} -> {len(local_ids)} runs")
    return PushVerdict(OK_EXTEND, f"registry rewritten with the same {len(local_ids)} runs "
                                  f"(row values changed; N unchanged)")


def classify_artifact(name: str, local: bytes, remote: Optional[bytes]) -> PushVerdict:
    """A dated ρ̄ artifact: pushed once, then immutable by name."""
    if local == b"":
        return PushVerdict(REFUSE, f"{name} is EMPTY locally — refusing to publish it")
    if remote is None:
        return PushVerdict(OK_FIRST, f"{name}: first push")
    if local == remote:
        return PushVerdict(OK_SAME, f"{name}: remote current")
    return PushVerdict(REFUSE, f"{name} CHANGED since it was backed up — a dated ρ̄ artifact is "
                               f"immutable by name; regenerate under a NEW date, or review and "
                               f"allow the rewrite explicitly")


def _registry_ids(db: Path) -> Set[str]:
    """run_ids, read through a READ-ONLY connection: the backup never writes the gate's input."""
    con = sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)
    try:
        return {r[0] for r in con.execute("SELECT run_id FROM runs")}
    finally:
        con.close()


def _content_digest(db: Path) -> str:
    """sha256 of the database's SQL dump. Compared instead of file bytes, so a SQLite
    library upgrade (different page layout, same rows) is not mistaken for a change."""
    import hashlib
    con = sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)
    try:
        return hashlib.sha256("\n".join(con.iterdump()).encode()).hexdigest()
    finally:
        con.close()


def _read_blob(blob: bytes) -> Optional[Tuple[Set[str], str]]:
    """(run_ids, content digest) of a registry held as bytes (the remote copy), or None
    if it is unreadable as SQLite."""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "remote.sqlite"
        f.write_bytes(blob)
        try:
            return _registry_ids(f), _content_digest(f)
        except sqlite3.DatabaseError:
            return None


def _snapshot(db: Path, dest: Path) -> None:
    """A consistent copy of a possibly-live SQLite file (backup API; source read-only)."""
    src = sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)
    dst = sqlite3.connect(str(dest))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _combine(verdicts: List[PushVerdict]) -> PushVerdict:
    """One verdict for the janitor row: any REFUSE refuses; then any DEFERRED defers."""
    detail = "; ".join(v.detail for v in verdicts)
    statuses = [v.status for v in verdicts]
    for status in (REFUSE, DEFERRED, OK_FIRST, OK_EXTEND):
        if status in statuses:
            return PushVerdict(status, detail)
    return PushVerdict(OK_SAME, detail)


def _put(local: Path, key: str) -> Optional[str]:
    r = _aws(["s3", "cp", str(local), f"s3://{BUCKET}/{key}"])
    if r.returncode != 0:
        return f"push to {key} FAILED: {(r.stderr or b'').decode(errors='replace')[:160]}"
    return None


def _sync_registry(db: Path, allow_rewrite: bool, as_of: Optional[str]) -> PushVerdict:
    if not db.exists():
        return PushVerdict(REFUSE, f"no local run registry at {db} — any remote copy is now the only one")
    remote, why = _read_remote_retrying(KEY_REGISTRY)
    if remote is None and why.startswith("unreachable"):
        return PushVerdict(DEFERRED, f"registry: network unreachable ({why}); next run will carry it")
    with tempfile.TemporaryDirectory() as d:
        snap = Path(d) / OBS_REGISTRY
        _snapshot(db, snap)
        remote_ids, remote_digest = None, None
        if remote is not None:
            parsed = _read_blob(remote)
            if parsed is None:
                return PushVerdict(REFUSE, "remote registry copy is unreadable as SQLite — "
                                           "not overwriting it without review")
            remote_ids, remote_digest = parsed
        v = classify_registry(_registry_ids(snap), remote_ids,
                              same_content=(_content_digest(snap) == remote_digest))
        if not v.ok and not allow_rewrite:
            return v
        if not v.ok:
            v = PushVerdict(OK_EXTEND, f"REWRITE ALLOWED explicitly: {v.detail}")
        if v.status == OK_SAME:
            return v
        date = as_of or datetime.now().strftime("%Y-%m-%d")
        for key in (KEY_REGISTRY, KEY_REGISTRY_DAILY_FMT.format(date=date)):
            err = _put(snap, key)
            if err:
                return PushVerdict(REFUSE, err)
        return v


def _sync_artifact(path: Path, allow_rewrite: bool) -> PushVerdict:
    key = KEY_ARTIFACT_FMT.format(name=path.name)
    remote, why = _read_remote_retrying(key)
    if remote is None and why.startswith("unreachable"):
        return PushVerdict(DEFERRED, f"{path.name}: network unreachable ({why})")
    v = classify_artifact(path.name, path.read_bytes(), remote)
    if not v.ok and not allow_rewrite:
        return v
    if not v.ok:
        v = PushVerdict(OK_EXTEND, f"REWRITE ALLOWED explicitly: {v.detail}")
    if v.status == OK_SAME:
        return v
    err = _put(path, key)
    return PushVerdict(REFUSE, err) if err else v


def sync_observability(obs_dir: Path, allow_rewrite: bool = False,
                       as_of: Optional[str] = None) -> PushVerdict:
    """Guarded push of the honest-N inputs. Never `allow_rewrite` on the nightly path."""
    verdicts = [_sync_registry(obs_dir / OBS_REGISTRY, allow_rewrite, as_of)]
    artifacts = sorted(obs_dir.glob(ARTIFACT_GLOB))
    if not artifacts:
        verdicts.append(PushVerdict(REFUSE, f"no {ARTIFACT_GLOB} in {obs_dir} — the gate's ρ̄ "
                                            f"input is missing locally"))
    verdicts += [_sync_artifact(p, allow_rewrite) for p in artifacts]
    return _combine(verdicts)


def verify_observability(obs_dir: Path) -> PushVerdict:
    """Start-of-run check: does a readable remote copy of each honest-N input exist and
    hold everything local does? Absent remote = single-copy = NOT ok (as for the ledger)."""
    db = obs_dir / OBS_REGISTRY
    verdicts: List[PushVerdict] = []
    if not db.exists():
        verdicts.append(PushVerdict(REFUSE, f"no local run registry at {db}"))
    else:
        remote, why = read_remote(KEY_REGISTRY)
        if remote is None:
            verdicts.append(PushVerdict(REFUSE, f"no readable remote registry ({why}) — single copy"))
        else:
            parsed = _read_blob(remote)
            if parsed is None:
                verdicts.append(PushVerdict(REFUSE, "remote registry copy unreadable as SQLite"))
            else:
                remote_ids = parsed[0]
                local_ids = _registry_ids(db)
                lost = remote_ids - local_ids
                if lost:
                    verdicts.append(PushVerdict(REFUSE, f"local registry LACKS {len(lost)} run(s) "
                                                        f"the remote holds — N would shrink"))
                elif local_ids - remote_ids:
                    verdicts.append(PushVerdict(OK_EXTEND, f"remote registry behind by "
                                                           f"{len(local_ids - remote_ids)} run(s)"))
                else:
                    verdicts.append(PushVerdict(OK_SAME, f"remote registry holds all {len(local_ids)} runs"))
    for p in sorted(obs_dir.glob(ARTIFACT_GLOB)):
        remote, why = read_remote(KEY_ARTIFACT_FMT.format(name=p.name))
        if remote is None:
            verdicts.append(PushVerdict(REFUSE, f"{p.name}: no readable remote copy ({why}) — single copy"))
        elif remote != p.read_bytes():
            verdicts.append(PushVerdict(REFUSE, f"{p.name}: local differs from its remote copy"))
        else:
            verdicts.append(PushVerdict(OK_SAME, f"{p.name}: remote current"))
    return _combine(verdicts)
