# paper_trader/_jsonl.py
"""Append-only JSONL store — the durability primitive for the order
journal, the ledger, and the reconcile log.

Append-only on purpose: an order/position history must never be
rewritten in place (that is how live books lose the audit trail that
reconciliation depends on). Each line is one JSON record; reads replay
the whole file. A crash mid-append truncates at most the last line,
which ``read_all`` skips (a half-written final line is treated as
absent — the journal is the source of truth for what we BELIEVE, and a
record that didn't fully land never happened).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List


class JsonlStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: Dict[str, Any]) -> None:
        line = json.dumps(record, separators=(",", ":"), sort_keys=True)
        # Single write call + flush + fsync so the record is durable
        # before we act on it (an order we believe submitted MUST be on
        # disk before we poll/reconcile, else a crash loses it).
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            import os
            os.fsync(fh.fileno())

    def read_all(self) -> List[Dict[str, Any]]:
        return list(self._iter())

    def _iter(self) -> Iterator[Dict[str, Any]]:
        if not self.path.exists():
            return
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # A torn final line from a crash mid-append — stop
                    # here; everything before it is intact.
                    return

    def exists(self) -> bool:
        return self.path.exists()
