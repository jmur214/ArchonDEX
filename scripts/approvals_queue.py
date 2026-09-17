"""The approvals queue — Phase-6 rung 0, the gate the ferry does NOT retire.

Every judgment gate the human holds today, they still hold — asynchronously. That is
the constitution's promise, and this is its mechanism: a scheduled pass never decides
anything a human decides today; it PREPARES the decision, with its evidence attached,
so answering costs one action instead of a relay.

TRACKED, BY RULING: a gitignored gate is an uninspectable gate. Entries live in
`ops/approvals/` inside git, so what was asked, when, on what evidence, and what was
answered are all in history rather than in one machine's filesystem.

ONE FILE PER DECISION, deliberately. A single queue file makes every answer a
conflict-prone edit of shared state and makes "what changed" unreadable in a diff.
One file per item means the diff IS the audit trail: creation is the ask, the status
line is the answer.

THIS MODULE IS GATE-SHAPED and therefore on the janitor's denylist — an autonomous
session may not add, answer, or withdraw its own approvals.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

PENDING, APPROVED, DECLINED, WITHDRAWN = "pending", "approved", "declined", "withdrawn"
VALID = (PENDING, APPROVED, DECLINED, WITHDRAWN)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class Approval:
    ident: str
    status: str
    kind: str
    title: str
    body: str = ""
    path: Optional[Path] = None

    @property
    def is_open(self) -> bool:
        return self.status == PENDING


def slugify(text: str, maxlen: int = 48) -> str:
    s = _SLUG_RE.sub("-", text.lower()).strip("-")
    return (s[:maxlen].rstrip("-") or "item")


def render(ident: str, kind: str, title: str, asked_by: str,
           evidence: List[str], body: str, as_of: Optional[str] = None) -> str:
    """The on-disk form. Evidence is REQUIRED and rendered as its own block: an
    approval request without evidence is a request to rubber-stamp."""
    as_of = as_of or datetime.now().strftime("%Y-%m-%d")
    lines = [
        "---",
        f"id: {ident}",
        f"status: {PENDING}",
        f"kind: {kind}",
        f"asked_by: {asked_by}",
        f"asked_on: {as_of}",
        "---",
        "",
        f"# {title}",
        "",
        body.strip(),
        "",
        "## Evidence",
    ]
    lines += [f"- {e}" for e in evidence] or ["- (none supplied — this is itself a reason to decline)"]
    lines += [
        "",
        "## To answer",
        f"Set `status:` to `{APPROVED}` or `{DECLINED}` in the frontmatter above and commit.",
        "The pass that raised this never acts on it — answering is the action.",
        "",
    ]
    return "\n".join(lines)


def parse(text: str, path: Optional[Path] = None) -> Optional[Approval]:
    """Read an entry. Returns None if it is not a well-formed approval file — a
    malformed gate entry must never be silently treated as answered."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fields = {}
    for line in text[3:end].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    if "id" not in fields or fields.get("status") not in VALID:
        return None
    title = ""
    for line in text[end:].splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return Approval(ident=fields["id"], status=fields["status"],
                    kind=fields.get("kind", "unknown"), title=title,
                    body=text, path=path)


def load_all(root: Path) -> List[Approval]:
    out = []
    for p in sorted(root.glob("*.md")):
        if p.name.upper() == "README.MD":
            continue
        a = parse(p.read_text(), p)
        if a is not None:
            out.append(a)
    return out


def open_items(root: Path) -> List[Approval]:
    return [a for a in load_all(root) if a.is_open]


def already_asked(root: Path, ident: str) -> bool:
    """Has this exact decision been raised before, in ANY state?

    Includes answered and withdrawn entries on purpose: re-asking a question the
    human already declined is how an automated queue becomes something people stop
    reading.
    """
    return any(a.ident == ident for a in load_all(root))
