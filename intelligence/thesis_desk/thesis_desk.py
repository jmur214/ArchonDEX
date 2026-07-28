"""T-324 — the thesis desk: the user-seeded channel + the machine-originated scan + the forward ledger.

TWO channels, ONE standard (both produce a `thesis_call/v1` that must validate, falsifiers and all):
  (a) USER-SEEDED — the user drops a few lines into `data/coordination/thesis_inbox.md`; the agentic
      analyst (E/T-321) researches it across our stores and formalizes it (adding the falsifiers + the
      second-order map). The user's instinct gets a research desk and an honest scorekeeper.
  (b) MACHINE-ORIGINATED — a weekly thematic scan on the strong tier over the news panel + events +
      rate-path: "what themes are emerging, who benefits second-order, write the theses."

Forward-only BY NECESSITY: a backtested thesis is memorization (the model knows how the story ended).
The desk REFUSES to file a thesis whose `as_of` is materially in the past — same hard guard as the
event-interpreter's `run_forward`.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

ROOT = pathlib.Path(__file__).resolve().parents[2]
THESIS_INBOX = ROOT / "data" / "coordination" / "thesis_inbox.md"
THESIS_LEDGER = ROOT / "data" / "intel" / "thesis_calls.jsonl"
DEFAULT_MAX_LAG_DAYS = 5          # forward-only guard (mirrors run_forward)

ModelCall = Callable[[str, str, int], Dict[str, Any]]


@dataclass
class SeedThesis:
    """A raw user seed — deliberately unstructured. A few lines of narrative + optional tickers."""
    raw: str
    narrative: str
    tickers: List[str] = field(default_factory=list)
    seed_id: str = ""


_TICKER_RE = re.compile(r"\$([A-Z][A-Z0-9.\-]{0,9})\b|\b([A-Z]{2,5})\b")
_STOP = {"AI", "THE", "AND", "FOR", "USD", "CEO", "IPO", "ETF", "USA", "GDP", "API", "NOT", "BUT", "ALL"}


def parse_seeds(text: str) -> List[SeedThesis]:
    """Parse `thesis_inbox.md`. Format is deliberately dead-simple — one seed per `## ` block:

        ## AI picks-and-shovels
        The obvious AI winners are priced. The suppliers of the compute...
        tickers: VRT, ETN

    Everything after the heading is narrative; an optional `tickers:` line names instruments. Explicit
    `$TICKER` mentions anywhere also count. If no tickers are given the desk maps them itself.
    """
    seeds: List[SeedThesis] = []
    for block in re.split(r"^##\s+", text, flags=re.M)[1:]:
        lines = block.strip().splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        body_lines, tickers = [], []
        for ln in lines[1:]:
            m = re.match(r"\s*tickers?\s*:\s*(.+)$", ln, flags=re.I)
            if m:
                tickers += [t.strip().upper().lstrip("$") for t in re.split(r"[,\s]+", m.group(1)) if t.strip()]
            else:
                body_lines.append(ln)
        body = "\n".join(body_lines).strip()
        for m in _TICKER_RE.finditer(body):
            t = (m.group(1) or m.group(2) or "").upper()
            if m.group(1) or (t and t not in _STOP and len(t) >= 2):
                if m.group(1):                       # only $-prefixed are unambiguous in prose
                    tickers.append(t)
        seeds.append(SeedThesis(raw=block.strip(), narrative=f"{title}\n{body}".strip(),
                                tickers=sorted(set(tickers)), seed_id=title.lower().replace(" ", "_")[:64]))
    return seeds


def load_seeds(path: pathlib.Path = THESIS_INBOX) -> List[SeedThesis]:
    return parse_seeds(path.read_text()) if path.exists() else []


def load_filed(ledger: pathlib.Path = THESIS_LEDGER) -> set:
    """Idempotency: thesis_ids already filed (one thesis per seed, ever)."""
    out = set()
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            try:
                out.add(json.loads(line)["thesis_id"])
            except Exception:
                continue
    return out


def build_seed_bundle(seed: SeedThesis, *, as_of: str, context: Optional[dict] = None) -> dict:
    """Deterministic, secret-free bundle for ONE seed. `context` is whatever research the agentic
    analyst attached (news/events/rate-path excerpts) — the desk does not fetch it itself."""
    return {"as_of": as_of, "origin": "user_seeded", "seed_id": seed.seed_id,
            "narrative_seed": seed.narrative, "user_tickers": seed.tickers,
            "research_context": context or {}}


def file_thesis(payload: dict, *, ledger: pathlib.Path = THESIS_LEDGER) -> "tuple[Optional[dict], Optional[str]]":
    """Validate + append. Returns (record, None) or (None, reason) — a bad thesis is NEVER filed."""
    from intelligence.thesis_desk.thesis_schema import validate_thesis_call
    call, err = validate_thesis_call(payload)
    if call is None:
        return None, err
    rec = call.model_dump()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")
    return rec, None


def assert_forward_only(as_of: str, *, today: Optional[_dt.date] = None,
                        max_lag_days: int = DEFAULT_MAX_LAG_DAYS) -> None:
    """[NN-AI-GATE]: refuse to file a thesis dated materially in the past (or the future).
    A thesis written about a period the model already knows the outcome of is memorization, not judgement."""
    today = today or _dt.date.today()
    d = _dt.date.fromisoformat(str(as_of)[:10])
    if d > today or (today - d).days > max_lag_days:
        raise ValueError(f"[NN-AI-GATE] refused: as_of {d} is not forward "
                         f"(today {today}, max_lag {max_lag_days}d) — a backtested thesis is memorization")
