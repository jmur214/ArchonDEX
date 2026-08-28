"""paper_trader/artifact_paths.py — T-348: ONE declaration per dated artifact.

THE DISEASE THIS CURES, stated as its own case history:

  * T-331 — `eval_harness` globbed `analyst_note_*.json` while the pulse wrote
    `note_<date>.json`. The analyst pool was ALWAYS EMPTY; nothing had ever been
    scored; G1's >=150-resolved bar could not accrue.
  * T-346 — `news_month_pushed` built the S3 date-partitioned key and looked for it
    on local disk, where the layout is flat. It reported "partition missing" every
    day of its life.
  * T-348 — `analyst_note_written` matched `<date>*.json` against files actually
    named `note_<date>.json`. It had NEVER been able to advance, and that permanent
    false alarm HID A REAL MISS: no constrained note exists for 2026-08-27, and
    nobody could see it inside a clock that was already crying wolf daily.

Three instances, one disease: **a reader encoding a writer's naming independently of
the writer.** Each was fixed locally, and the next consumer reintroduced it, because
nothing made the naming a single shared fact. Fixing instances does not cure a class.

THE RULE: a dated artifact is DECLARED here once. Writers ask for the path they
should write; readers ask for the pattern they should match. Neither spells it out.
A future consumer that wants to watch an artifact must add it here or import an
existing entry — it cannot quietly invent a third spelling, because there is nowhere
to put one.

Deliberately dependency-free and I/O-free: this module is imported by both the live
write path and the read-only census, so it must never be able to fail either.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple


@dataclass(frozen=True)
class DatedArtifact:
    """A directory of per-day files whose NAME encodes the day.

    `template` is the single source of truth for the filename; `extra_globs` exists
    only to keep pre-existing or externally-archived spellings readable (the T-331
    fix's reasoning), never to sanction a new one.
    """
    key: str
    directory: str
    template: str = "note_{as_of}.json"
    extra_globs: Tuple[str, ...] = field(default_factory=tuple)

    def path_for(self, root: Path, as_of: str) -> Path:
        """Where a writer must write this artifact for `as_of`."""
        return Path(root) / self.directory / self.template.format(as_of=as_of)

    def names_for(self, as_of: str) -> Tuple[str, ...]:
        """Every filename that legitimately represents this artifact on `as_of`.

        The canonical spelling first; the tolerated ones after. `as_of` may be "*" to
        get the reader's glob patterns."""
        return tuple(t.format(as_of=as_of)
                     for t in (self.template,) + tuple(self.extra_globs))

    def globs(self) -> Tuple[str, ...]:
        """Every filename pattern a reader may legitimately match."""
        return self.names_for("*")

    def exists_for(self, root: Path, as_of: str) -> bool:
        """Did the artifact for `as_of` land? Readers ask THIS, never a bare glob."""
        d = Path(root) / self.directory
        if not d.is_dir():
            return False
        return any((d / n).is_file() for n in self.names_for(as_of))


ANALYST_NOTE = DatedArtifact(
    key="analyst_note",
    directory="data/intel/analyst_notes",
    extra_globs=("analyst_note_{as_of}.json",),   # T-331's archived spelling
)

ANALYST_NOTE_AGENTIC = DatedArtifact(
    key="analyst_note_agentic",
    directory="data/intel/analyst_notes_agentic",
    extra_globs=("analyst_note_{as_of}.json",),
)

REGISTRY: Dict[str, DatedArtifact] = {
    a.key: a for a in (ANALYST_NOTE, ANALYST_NOTE_AGENTIC)
}
