# core/sec_http.py
"""One GET for sec.gov hosts, with the two properties the standard library does not give.

1. IT NEVER LEAVES sec.gov. SEC's fair-access policy asks for a declared contact in the
   User-Agent, and the owner approved that contact for SEC hosts only. ``urllib`` (and
   ``requests``) copy a request's headers onto a redirect, so a redirect from sec.gov to
   any other host would carry the contact there. A redirect off sec.gov — or down from
   https — is refused.
2. IT HAS A TOTAL DEADLINE. A socket timeout bounds each READ, not the request: a server
   that trickles two bytes a second held a "1 second" request open for 20 seconds. These
   fetches now run before the paper run's main state push, so the whole request is bounded:
   ``timeout`` seconds, plus at most half of it again for a read already in progress.

The caller supplies the headers; this module holds no contact details.
"""
from __future__ import annotations

import io
import time
import urllib.error
import urllib.request
from typing import Any, Mapping, Optional
from urllib.parse import urlparse

MAX_BYTES = 64 * 1024 * 1024      # no SEC document this project reads is near this
_CHUNK = 64 * 1024


class SecHttpError(OSError):
    """The request was refused or abandoned; the message says why."""


def is_sec_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "sec.gov" or host.endswith(".sec.gov")


class _StayOnSec(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to another https sec.gov URL."""

    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> Optional[urllib.request.Request]:
        if not (is_sec_host(newurl) and urlparse(newurl).scheme == "https"):
            raise SecHttpError(f"refused a redirect off sec.gov (to "
                               f"{urlparse(newurl).hostname!r}): the contact user agent "
                               f"goes to SEC hosts only")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _read_all(resp: Any, deadline: float, clock: Any) -> bytes:
    buf = io.BytesIO()
    read = getattr(resp, "read1", None) or resp.read       # read1 returns as data arrives
    while True:
        if clock() > deadline:
            raise SecHttpError("total deadline exceeded while reading the response")
        chunk = read(_CHUNK)
        if not chunk:
            return buf.getvalue()
        buf.write(chunk)
        if buf.tell() > MAX_BYTES:
            raise SecHttpError(f"response larger than {MAX_BYTES} bytes")


def fetch(url: str, headers: Mapping[str, str], *, timeout: float,
          allow_non_sec_for_test: bool = False, clock: Any = time.monotonic) -> bytes:
    """GET ``url`` from a sec.gov host within ``timeout`` seconds in total (see the module
    docstring for the one read that can overrun it). Raises on any failure: an HTTP error
    status, a refused redirect, the deadline."""
    if not (is_sec_host(url) or allow_non_sec_for_test):
        raise SecHttpError(f"not a sec.gov URL: {urlparse(url).hostname!r}")
    deadline = clock() + float(timeout)
    opener = urllib.request.build_opener(_StayOnSec())
    with opener.open(urllib.request.Request(url, headers=dict(headers)),
                     timeout=max(float(timeout) / 2.0, 0.1)) as resp:
        return _read_all(resp, deadline, clock)
