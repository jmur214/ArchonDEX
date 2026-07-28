"""T-324b — the MACHINE-ORIGINATED thematic scan: the desk's PRIMARY engine, with the bias firewall.

Directive correction (user, verbatim intent): *"I DO want the machine to replace me. I want it to find the
themes or ideas it likes and trade those."* So machine-originated generation is the desk's main engine, not a
sidecar — and the user-seeded channel must **never bias it**.

## THE BIAS FIREWALL (the load-bearing guarantee here)
The generator's context may NEVER contain a user-seeded thesis — not in the bundle, not via own-notes
retrieval. User theses live in a SEPARATE NAMESPACE (`origin == "user_seeded"`) that the generator cannot
read. Enforcement is structural, not procedural:
  * `build_scan_bundle` assembles ONLY machine-visible sources (news panel, event calls, rate path) and
    prior MACHINE theses;
  * `assert_bundle_is_blind` re-checks the assembled bundle and RAISES if any user-seeded id/narrative
    leaked in — a fail-closed guard, so a future refactor that widens retrieval trips the test, not the tape.
Both channels are SCORED identically (A's table); only GENERATION is isolated — so the machine's record is
attributable to the machine.

## THE BLIND-SCAN EXPERIMENT (sequencing, provenance-stamped)
The user seeded "AI picks-and-shovels" BEFORE the machine's first scan. That seed is held UNFILED until the
first blind scan completes; both are then filed. The natural experiment: does the machine independently
converge on AI-infrastructure themes, or find different/better ones? Convergence and divergence are both
informative — but ONLY if the first scan is provably blind, so `scan_provenance()` stamps
`blind_scan_ordinal`, `seeds_existed_at_scan_time`, and `firewall_asserted` into every scan's record.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from intelligence.thesis_desk.thesis_desk import THESIS_LEDGER, ModelCall

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCAN_STATE = ROOT / "data" / "intel" / "thesis_scan_state.json"

# Cadence: the PRIMARY engine runs weekly on the strong tier (theses are long-horizon; weekly is frequent
# enough to catch an emerging theme and slow enough that the desk isn't chasing noise).
SCAN_CADENCE_DAYS = 7
SCAN_TIER = "weekly"          # the strong-tier pin in config/llm_settings.json


class FirewallBreach(AssertionError):
    """Raised when user-seeded material is detected in a machine-scan bundle."""


def load_machine_theses(ledger: pathlib.Path = THESIS_LEDGER) -> List[dict]:
    """Prior MACHINE theses only — the generator may see its own record, never the user's."""
    out: List[dict] = []
    if not ledger.exists():
        return out
    for line in ledger.read_text().splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("origin") == "machine":                  # the namespace split
            out.append(r)
    return out


def load_user_seed_fingerprints(ledger: pathlib.Path = THESIS_LEDGER,
                                inbox: Optional[pathlib.Path] = None) -> List[str]:
    """Strings that MUST NOT appear in a scan bundle (ids + narrative text of user-seeded material)."""
    fps: List[str] = []
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("origin") == "user_seeded":
                fps += [str(r.get("thesis_id", "")), str(r.get("narrative", ""))]
    from intelligence.thesis_desk.thesis_desk import THESIS_INBOX, load_seeds
    for s in load_seeds(inbox or THESIS_INBOX):
        fps += [s.seed_id, s.narrative]
    return [f for f in fps if f and len(f.strip()) >= 8]


def assert_bundle_is_blind(bundle: dict, *, fingerprints: Optional[Sequence[str]] = None) -> None:
    """FAIL-CLOSED: raise if any user-seeded id/narrative leaked into the generator's context."""
    fps = list(fingerprints if fingerprints is not None else load_user_seed_fingerprints())
    blob = json.dumps(bundle, default=str).lower()
    for fp in fps:
        f = fp.strip().lower()
        # match on the seed id, or on a distinctive slice of the narrative (first 60 chars)
        probe = f[:60]
        if probe and probe in blob:
            raise FirewallBreach(
                "[BIAS FIREWALL] user-seeded material leaked into a machine-scan bundle "
                f"(probe={probe[:40]!r}). The machine's thematic generation must be blind to user theses; "
                "both channels are scored identically but GENERATION is isolated.")
    if any(t.get("origin") == "user_seeded" for t in bundle.get("prior_machine_theses", [])):
        raise FirewallBreach("[BIAS FIREWALL] a user_seeded thesis appeared in prior_machine_theses")


def build_scan_bundle(as_of: str, *, news: Optional[list] = None, events: Optional[list] = None,
                      rate_path: Optional[dict] = None, universe_hint: Optional[list] = None,
                      ledger: pathlib.Path = THESIS_LEDGER, assert_blind: bool = True) -> dict:
    """Assemble the generator's context from MACHINE-VISIBLE sources ONLY, then assert the firewall."""
    bundle = {
        "as_of": as_of,
        "task": ("Identify emerging THEMES and the second-order beneficiaries. Write theses you believe in, "
                 "each with instruments (incl. second-order legs and the mapping reasoning) and REQUIRED "
                 "falsifiers that can kill the thesis on a date."),
        "news_digest": news or [],
        "event_calls": events or [],
        "rate_path": rate_path or {},
        "universe_hint": universe_hint or [],
        "prior_machine_theses": [
            {"thesis_id": t.get("thesis_id"), "theme_class": t.get("theme_class"),
             "as_of": t.get("as_of"), "origin": t.get("origin")}
            for t in load_machine_theses(ledger)
        ],
    }
    if assert_blind:
        assert_bundle_is_blind(bundle)
    return bundle


# ---------------- scan state / provenance (the blind-scan experiment) ----------------
def _state(path: pathlib.Path = SCAN_STATE) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {"scans": 0, "last_scan": None}


def scan_provenance(as_of: str, *, path: pathlib.Path = SCAN_STATE,
                    inbox: Optional[pathlib.Path] = None) -> dict:
    """Stamp the blind-scan experiment's sequencing into the scan record (BEFORE the scan is recorded)."""
    st = _state(path)
    from intelligence.thesis_desk.thesis_desk import THESIS_INBOX, load_seeds
    seeds = load_seeds(inbox or THESIS_INBOX)
    return {"as_of": as_of, "blind_scan_ordinal": int(st.get("scans", 0)) + 1,
            "is_first_blind_scan": int(st.get("scans", 0)) == 0,
            "seeds_existed_at_scan_time": [s.seed_id for s in seeds],
            "firewall_asserted": True, "tier": SCAN_TIER}


def record_scan(as_of: str, *, n_theses: int, path: pathlib.Path = SCAN_STATE) -> dict:
    st = _state(path)
    st["scans"] = int(st.get("scans", 0)) + 1
    st["last_scan"] = as_of
    st.setdefault("history", []).append({"as_of": as_of, "n_theses": n_theses})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(st, indent=2))
    return st


def due(as_of: str, *, path: pathlib.Path = SCAN_STATE, cadence_days: int = SCAN_CADENCE_DAYS) -> bool:
    """Weekly cadence for the PRIMARY engine."""
    st = _state(path); last = st.get("last_scan")
    if not last:
        return True
    return (_dt.date.fromisoformat(str(as_of)[:10]) - _dt.date.fromisoformat(str(last)[:10])).days >= cadence_days


def seeds_are_held(path: pathlib.Path = SCAN_STATE) -> bool:
    """THE BLIND-SCAN GATE: user seeds stay UNFILED until the machine's first blind scan completes."""
    return int(_state(path).get("scans", 0)) == 0
