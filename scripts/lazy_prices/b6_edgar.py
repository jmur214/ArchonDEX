"""scripts/lazy_prices/b6_edgar.py
=================================
T-383 (B-6) — the SEC EDGAR access layer: rate-limited, gzip, retrying, fail-closed.

- User-Agent: READ from `ingest_filings_t237.UA` (the user-approved SEC identity, 2026-11-11);
  never duplicated as a literal, and SENT ONLY to SEC hosts — `fetch()` refuses any other host.
- Rate: one request at a time, >= MIN_INTERVAL s apart (<= 4.5 req/s; the SEC ceiling is 10).
- gzip requested and decoded (multi-MB 10-K HTML compresses 5-10x).
- Retries 429 / 5xx / timeouts with backoff; a 403 HALTS the run (`EdgarRefused`) — an
  identity/fair-access refusal is never retried around.
- Every outcome is returned with the provider's own status and reason, unfiltered.
- A disk guard (`disk_free_gb`, `assert_disk`) for the drivers: they check before every batch and
  halt cleanly below the floor.
No `.env`, no other service.
"""
from __future__ import annotations

import gzip
import json
import shutil
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from scripts.lazy_prices.ingest_filings_t237 import UA as _T237_UA

SEC_HOSTS = frozenset({"www.sec.gov", "data.sec.gov"})
MIN_INTERVAL = 0.22
MAX_RETRIES = 4
DISK_FLOOR_GB = 15.0
DISK_PATH = "/System/Volumes/Data"


class EdgarRefused(RuntimeError):
    """403 / identity refusal — halt the run, do not retry."""


class DiskFloor(RuntimeError):
    """Free disk under the floor — halt cleanly."""


@dataclass
class FetchResult:
    ok: bool
    body: bytes | None
    status: int | None
    reason: str
    url: str
    seconds: float
    attempts: int


_last_request = [0.0]
stats = {"requests": 0, "bytes": 0, "retries": 0, "failures": 0}


def _headers() -> dict[str, str]:
    h = dict(_T237_UA)
    h["Accept-Encoding"] = "gzip, deflate"
    return h


def _decode_body(raw: bytes, encoding: str | None) -> bytes:
    if encoding == "gzip" or raw[:2] == b"\x1f\x8b":
        return gzip.decompress(raw)
    if encoding == "deflate":
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw


def fetch(url: str, timeout: float = 60.0) -> FetchResult:
    """GET one SEC URL. Refuses non-SEC hosts (the UA must never leave the SEC)."""
    host = urlparse(url).hostname or ""
    if host not in SEC_HOSTS:
        raise ValueError(f"refusing non-SEC host {host!r}: the SEC User-Agent is SEC-only")
    t0 = time.time()
    last_status, last_reason = None, ""
    for attempt in range(1, MAX_RETRIES + 1):
        wait = MIN_INTERVAL - (time.time() - _last_request[0])
        if wait > 0:
            time.sleep(wait)
        _last_request[0] = time.time()
        stats["requests"] += 1
        try:
            req = urllib.request.Request(url, headers=_headers())
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                body = _decode_body(raw, r.headers.get("Content-Encoding"))
                stats["bytes"] += len(raw)
                return FetchResult(True, body, r.status, "", url, time.time() - t0, attempt)
        except urllib.error.HTTPError as e:
            last_status, last_reason = e.code, f"HTTPError {e.code} {e.reason}"
            if e.code == 403:
                raise EdgarRefused(f"{url}: {last_reason}") from e
            if e.code == 404:
                break
            if e.code not in (429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last_status, last_reason = None, f"{type(e).__name__} {e}"
        stats["retries"] += 1
        time.sleep(min(30.0, 2.0 ** attempt))
    stats["failures"] += 1
    return FetchResult(False, None, last_status, last_reason, url, time.time() - t0, attempt)


def fetch_json(url: str) -> tuple[dict | None, FetchResult]:
    res = fetch(url, timeout=30.0)
    if not res.ok or res.body is None:
        return None, res
    try:
        return json.loads(res.body), res
    except ValueError as e:
        res.ok, res.reason = False, f"json_decode:{e}"
        return None, res


def disk_free_gb(path: str = DISK_PATH) -> float:
    return shutil.disk_usage(path).free / 1e9


def assert_disk(floor_gb: float = DISK_FLOOR_GB, path: str = DISK_PATH) -> float:
    free = disk_free_gb(path)
    if free < floor_gb:
        raise DiskFloor(f"free disk {free:.2f} GB < floor {floor_gb:.1f} GB — halting cleanly")
    return free


PERIODIC_FORMS = frozenset({"10-K", "10-Q"})
SUBMISSION_FIELDS = ("accessionNumber", "filingDate", "acceptanceDateTime", "reportDate", "form",
                     "primaryDocument", "size")


def periodic_rows(arr: dict) -> list[dict]:
    """10-K / 10-Q rows (exact form match: amendments excluded) from one submissions array."""
    out: list[dict] = []
    forms = arr.get("form", [])
    for i, f in enumerate(forms):
        if f not in PERIODIC_FORMS:
            continue
        row = {k: (arr.get(k, [None] * len(forms))[i] if i < len(arr.get(k, [])) else None)
               for k in SUBMISSION_FIELDS}
        out.append(row)
    return out


def company_periodic_filings(cik: int, shared_raw: Path | None = None
                             ) -> tuple[list[dict], dict, list[FetchResult]]:
    """All 10-K/10-Q rows for a CIK. The 'recent' block is fetched FRESH; older pages are read
    from the shared read-only cache when present (they are immutable), else fetched.
    Returns (rows, meta{name, tickers, former_names}, fetch results)."""
    cik10 = f"CIK{cik:010d}"
    results: list[FetchResult] = []
    sub, res = fetch_json(f"https://data.sec.gov/submissions/{cik10}.json")
    results.append(res)
    if sub is None:
        return [], {}, results
    rows = periodic_rows(sub["filings"]["recent"])
    for older in sub["filings"].get("files", []):
        name = older["name"]
        page = None
        if shared_raw is not None and (shared_raw / name).is_file():
            try:
                page = json.loads((shared_raw / name).read_text())
            except ValueError:
                page = None
        if page is None:
            page, r2 = fetch_json(f"https://data.sec.gov/submissions/{name}")
            results.append(r2)
        if page is not None:
            rows += periodic_rows(page)
    meta = {"name": sub.get("name", ""), "tickers": list(sub.get("tickers", []) or []),
            "former_names": [f.get("name", "") for f in sub.get("formerNames", []) or []]}
    return rows, meta, results


def doc_url(cik: int, accession: str, primary_doc: str) -> str:
    return (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
            f"{accession.replace('-', '')}/{primary_doc}")
