"""edges.yml fail-closed unit — proof by reversion: revert ONE fix, run ONLY its locks, require FAIL.

    python scripts/registry_fail_closed_reversion_proof.py     # from the repo root; ~10 s

Each case swaps an exact, count-checked substring in engines/engine_d_discovery/discovery.py,
runs only the locks that should catch it, restores the original BYTES in a `finally` and asserts
the sha256. It never stashes and never touches git. The `why:` line is the first assertion of the
failure — read it: a lock that fails for an unrelated reason bites vacuously.
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

W = Path(__file__).resolve().parents[1]
D = "engines/engine_d_discovery/discovery.py"
T = "tests/test_engine_d_registry_write_fail_closed.py::"

OLD_SAVE_READ = '''        if not self.registry_path.exists():
            existing = {"edges": []}
        else:
            try:
                existing = yaml.safe_load(self.registry_path.read_text()) or {"edges": []}
                if isinstance(existing, list):
                    existing = {"edges": existing}
            except Exception as e:
                print(f"[DISCOVERY] Error reading registry: {e}")
                existing = {"edges": []}
        existing.setdefault("edges", [])
'''

CASES = [
    ("save_candidates: the old read (any failure -> an empty registry)",
     [("        existing = self._read_registry()\n\n        # Deduplicate by ID", OLD_SAVE_READ + "\n        # Deduplicate by ID")],
     [T + "test_an_unreadable_registry_is_REFUSED_and_left_byte_untouched"]),
    ("get_queued_candidates: the old read (any failure -> [])",
     [('        return [e for e in self._read_registry()["edges"] if e.get("status") == status]',
       '        try:\n            return [e for e in self._read_registry()["edges"] if e.get("status") == status]\n'
       '        except Exception as e:\n            print(f"[DISCOVERY] Error reading registry: {e}")\n            return []')],
     [T + "test_get_queued_candidates_refuses_an_unreadable_registry_never_reads_it_as_empty"]),
    ("the old write: open('w') (truncate) BEFORE serialising",
     [('        self._write_registry({**existing, "edges": list(current_map.values())})',
       '        with self.registry_path.open("w") as f:\n'
       '            yaml.dump({**existing, "edges": list(current_map.values())}, f, sort_keys=False)')],
     [T + "test_a_serialisation_failure_never_truncates_the_registry"]),
    ("a non-atomic write: no temp file + rename",
     [('        self._write_registry({**existing, "edges": list(current_map.values())})',
       '        self.registry_path.write_text(yaml.dump({**existing, "edges": list(current_map.values())}, sort_keys=False))')],
     [T + "test_a_failed_rename_leaves_the_registry_untouched"]),
]

env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
ok = True
for name, subs, tests in CASES:
    p = W / D
    orig = p.read_bytes()
    sha = hashlib.sha256(orig).hexdigest()
    text = orig.decode()
    for old, new in subs:
        assert text.count(old) == 1, (name, old[:60], text.count(old))
        text = text.replace(old, new)
    p.write_text(text)
    try:
        r = subprocess.run(["nice", "-n", "19", sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests],
                           cwd=W, env=env, capture_output=True, text=True)
    finally:
        p.write_bytes(orig)
    assert hashlib.sha256(p.read_bytes()).hexdigest() == sha, f"RESTORE FAILED for {D}"
    last = (r.stdout.strip().splitlines() or ["?"])[-1]
    ok &= r.returncode != 0
    why = next((l.strip() for l in r.stdout.splitlines() if l.startswith("E ")), "?")
    print(f"[{'LOCK BITES' if r.returncode != 0 else 'LOCK DID NOT FAIL'}] {name}  ->  {last}\n      why: {why[:170]}")
print("ALL LOCKS BITE" if ok else "SOME LOCK DID NOT FAIL")
