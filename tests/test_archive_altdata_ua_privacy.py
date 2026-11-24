"""Privacy lock (2026-11-17): the alt-data archiver may send the owner's contact address
ONLY to SEC EDGAR hosts (user ruling 2026-11-11). Before the fix its contact User-Agent
went to every host it called. These tests drive every pull function with the network
stubbed and inspect the User-Agent of every request actually built.

No literal address appears here: the SEC header is read from the module's own constant.
"""
from __future__ import annotations

import socket
import urllib.request

import pytest

import scripts.archive_altdata_t136 as m

_PULLS = ("pull_gpr", "pull_epu", "snapshot_polymarket", "snapshot_kalshi", "snapshot_kxfed",
          "pull_fred_rate_path", "snapshot_cef", "pull_form4_index", "pull_usaspending",
          "pull_credit_spread_oas")


class _Resp:
    def __init__(self, body: bytes = b"[]") -> None:
        self._body = body

    def read(self, n: int = -1) -> bytes:
        body, self._body = self._body, b""      # a chunked reader sees the end
        return body

    def __enter__(self) -> "_Resp":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _refuse(*_a: object, **_k: object) -> None:
    raise OSError("network refused by the privacy lock")


def _stub_wire(monkeypatch: pytest.MonkeyPatch, seen: list[tuple[str, str]], body: bytes) -> None:
    """Capture at ``OpenerDirector.open`` — the one method BOTH ``urllib.request.urlopen`` and
    a purpose-built opener (core/sec_http.py, 2026-11-24) go through — and refuse sockets, so a
    transport that bypasses this capture fails here instead of reaching the network. (Stubbing
    ``urlopen`` alone let the SEC transport through to sec.gov the day it was introduced.)"""
    def fake_open(self, fullurl, data=None, timeout=None):  # noqa: ANN001
        req = fullurl if not isinstance(fullurl, str) else urllib.request.Request(fullurl)
        seen.append((req.full_url, req.get_header("User-agent") or ""))
        return _Resp(body)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", fake_open)
    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse)


def _capture(monkeypatch: pytest.MonkeyPatch, tmp_path) -> list[tuple[str, str]]:
    seen: list[tuple[str, str]] = []
    _stub_wire(monkeypatch, seen, b"[]")
    monkeypatch.setattr(m, "OUT_DIR", tmp_path)
    monkeypatch.setattr(m, "_append", lambda *a, **k: None)
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    for name in _PULLS:
        getattr(m, name)()
    return seen


def _violations(seen: list[tuple[str, str]]) -> list[str]:
    bad = []
    for url, ua in seen:
        if m._is_sec_host(url):
            if ua != m.SEC_UA["User-Agent"]:
                bad.append(f"SEC host without the declared UA: {url}")
        elif "@" in ua:
            bad.append(f"contact address sent to a non-SEC host: {url}")
    return bad


def test_contact_address_goes_only_to_sec_hosts(monkeypatch, tmp_path):
    seen = _capture(monkeypatch, tmp_path)
    assert any(m._is_sec_host(u) for u, _ in seen), "no SEC request was exercised"
    assert sum(not m._is_sec_host(u) for u, _ in seen) >= 8, "too few non-SEC requests exercised"
    assert _violations(seen) == []


def test_the_lock_catches_a_contact_ua_on_every_host(monkeypatch, tmp_path):
    """Positive control: the pre-fix behaviour (one contact UA for every host) is caught."""
    monkeypatch.setattr(m, "UA", {"User-Agent": "ArchonDEX research a@b.c"})
    seen = _capture(monkeypatch, tmp_path)
    assert any("non-SEC host" in v for v in _violations(seen))


def _capture_positioning(monkeypatch: pytest.MonkeyPatch, tmp_path, ua=None) -> list[tuple[str, str]]:
    import scripts.archive_positioning_t136 as p
    seen: list[tuple[str, str]] = []
    _stub_wire(monkeypatch, seen, b"")
    monkeypatch.setattr(p, "OUT_DIR", tmp_path)
    monkeypatch.setattr(p, "_append_parquet", lambda *a, **k: 0)
    monkeypatch.setattr(p.time, "sleep", lambda s: None)
    if ua is not None:
        monkeypatch.setattr(p, "UA", ua)
    p.pull_regsho_short_volume(7)
    p.pull_sec_ftd()
    p.pull_naaim()
    p.pull_finra_margin()
    p.pull_finra_short_interest()
    return seen


def test_positioning_archiver_sends_the_contact_only_to_sec(monkeypatch, tmp_path):
    import scripts.archive_positioning_t136 as p
    seen = _capture_positioning(monkeypatch, tmp_path)
    assert any(p._is_sec_host(u) for u, _ in seen)
    assert sum(not p._is_sec_host(u) for u, _ in seen) >= 5
    for url, ua in seen:
        if p._is_sec_host(url):
            assert ua == p.SEC_UA["User-Agent"], url
        else:
            assert "@" not in ua, url


def test_positioning_lock_catches_a_contact_ua(monkeypatch, tmp_path):
    import scripts.archive_positioning_t136 as p
    seen = _capture_positioning(monkeypatch, tmp_path, ua={"User-Agent": "x a@b.c"})
    assert any("@" in ua for url, ua in seen if not p._is_sec_host(url))


def test_the_8k_feed_and_the_body_fetch_ask_sec_hosts_only(monkeypatch, tmp_path):
    """T-412: the forward 8-K feed and the filing-body fetch, through the real transport."""
    import intelligence.event_call.eightk_body as eb
    seen: list[tuple[str, str]] = []
    _stub_wire(monkeypatch, seen, b"{}")
    monkeypatch.setattr(m, "OUT_DIR", tmp_path)
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    monkeypatch.setattr(m, "_edgar_cik_map", lambda uni, today: ({1000: "ACME"}, 1.0))
    m.pull_8k_items(["ACME"], as_of="2026-09-17")
    eb.fetch_8k_text(1000, "0000001000-26-000001", primary_document="d.htm")
    # three business-day indexes in the window + one filing body
    assert len(seen) == 4 and all(m._is_sec_host(u) for u, _ in seen), seen
    assert all("@" in ua for _, ua in seen)            # SEC's policy: the declared contact


@pytest.mark.parametrize("modname", [
    "scripts.build_multidecade_substrate_t306",   # FRED, Dartmouth, LBMA — no SEC host
    "scripts.build_membership_panel_t136",        # GitHub raw, Wikipedia — no SEC host
])
def test_non_sec_scripts_carry_no_contact_address(modname):
    import importlib
    mod = importlib.import_module(modname)
    assert "@" not in mod.UA["User-Agent"]


@pytest.mark.parametrize("url,sec", [
    ("https://www.sec.gov/Archives/edgar/daily-index/2026/QTR4/form.20261117.idx", True),
    ("https://data.sec.gov/submissions/CIK0000320193.json", True),
    ("https://efts.sec.gov/LATEST/search-index?q=x", True),
    ("https://gamma-api.polymarket.com/markets", False),
    ("https://api.elections.kalshi.com/trade-api/v2/markets", False),
    ("https://fred.stlouisfed.org/graph/fredgraph.csv?id=EFFR", False),
    ("https://web.archive.org/web/1id_/https://fred.stlouisfed.org/x", False),
    ("https://api.usaspending.gov/api/v2/search/spending_by_award/", False),
    ("https://notsec.gov.example.com/", False),
    ("https://sec.gov.evil.example/", False),
])
def test_headers_route_by_host(url, sec):
    assert m._is_sec_host(url) is sec
    assert (m._headers_for(url) is m.SEC_UA) is sec
    if not sec:
        assert "@" not in m._headers_for(url)["User-Agent"]
