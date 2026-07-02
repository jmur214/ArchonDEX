"""
fetch_shiller_ie_data — download Robert Shiller's `ie_data` workbook and cache
the monthly equity valuation series to `data/macro/shiller_ie_data.csv`.

Shiller's "Irrational Exuberance" data spreadsheet is the canonical free source
for the U.S. equity dividend yield and earnings yield back to 1871 — the missing
equity leg for a cross-asset carry construction (bonds/FX/commodities carry are
already sourced; the equity carry = dividend yield + earnings yield needs this).

The workbook's "Data" sheet has a multi-row header block (title, author, wrapped
column labels) and a trailing footnote row, so we parse by POSITIONAL column
index rather than by header text — the header text wraps across rows 6-7 and is
not a reliable single-row key. Columns consumed (0-indexed on the Data sheet):

    col 0  -> Date      (encoded YYYY.MM as a float, e.g. 1871.01 = Jan 1871)
    col 1  -> P         (S&P Composite price)
    col 2  -> D         (dividend)
    col 3  -> E         (earnings)
    col 12 -> CAPE      (cyclically-adjusted P/E, a.k.a. P/E10)

Output schema (`data/macro/shiller_ie_data.csv`):

    date        (ISO YYYY-MM-01, month-start)
    price       (float)
    dividend    (float)
    earnings    (float)
    cape        (float; NaN in the earliest decade where P/E10 is undefined)

Usage:
    python scripts/fetch_shiller_ie_data.py

Notes:
- Two mirrors are tried in order (wsimg CDN first — it is the more frequently
  updated copy — then the classic Yale econ host as a fallback). If both fail
  the script exits non-zero and writes NOTHING, rather than emitting a partial
  or stale file that would read as a real (but wrong) measurement.
- Reading .xls requires the `xlrd` engine (already a project dependency).
"""
from __future__ import annotations

import argparse
import io
import urllib.request
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MACRO_DIR = ROOT / "data" / "macro"
OUT_PATH = MACRO_DIR / "shiller_ie_data.csv"

# Primary then fallback mirror. wsimg is Shiller's current CDN host; the Yale
# econ URL is the long-standing classic location.
URLS = (
    "https://img1.wsimg.com/blobby/go/e5e77e0b-59d1-44d9-ab25-4763ac982e53/downloads/ie_data.xls",
    "http://www.econ.yale.edu/~shiller/data/ie_data.xls",
)

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# Positional columns on the "Data" sheet (see module docstring).
_COL_DATE = 0
_COL_PRICE = 1
_COL_DIV = 2
_COL_EARN = 3
_COL_CAPE = 12


def _download(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted host)
        data = resp.read()
    if not data:
        raise RuntimeError(f"empty response body from {url}")
    # A genuine .xls is an OLE2 compound doc: magic D0 CF 11 E0. Guard against an
    # HTML error page silently masquerading as the file.
    if data[:4] != b"\xd0\xcf\x11\xe0":
        raise RuntimeError(
            f"{url} did not return an .xls (bad magic {data[:4]!r}); refusing to parse"
        )
    return data


def _fetch_workbook() -> bytes:
    last_err: Optional[Exception] = None
    for url in URLS:
        try:
            print(f"[fetch] {url}")
            return _download(url)
        except Exception as exc:  # noqa: BLE001 — try next mirror, remember why
            print(f"[warn] {url} failed: {type(exc).__name__}: {exc}")
            last_err = exc
    raise RuntimeError(f"all Shiller mirrors failed; last error: {last_err}")


def _decode_shiller_date(raw: pd.Series) -> pd.Series:
    """Convert Shiller's YYYY.MM float encoding to a month-start Timestamp.

    1871.01 -> 1871-01-01, 2024.10 -> 2024-10-01. Values that are not a clean
    YYYY.MM (footnote rows, blanks) become NaT and are dropped by the caller.
    Uses rounding on the *month* component because the float encoding is not
    exact (e.g. 2024.10 may store as 2024.0999999).
    """
    num = pd.to_numeric(raw, errors="coerce")
    year = np.floor(num).astype("Float64")
    # month = round((frac) * 100); .01->1 ... .12->12
    month = ((num - np.floor(num)) * 100).round().astype("Float64")
    ok = year.notna() & month.between(1, 12)
    out = pd.Series(pd.NaT, index=raw.index, dtype="datetime64[ns]")
    if ok.any():
        y = year[ok].astype(int).astype(str)
        m = month[ok].astype(int).astype(str).str.zfill(2)
        out.loc[ok] = pd.to_datetime(y + "-" + m + "-01", format="%Y-%m-%d")
    return out


def parse_data_sheet(xls_bytes: bytes) -> pd.DataFrame:
    xls = pd.ExcelFile(io.BytesIO(xls_bytes))
    if "Data" not in xls.sheet_names:
        raise RuntimeError(f"workbook has no 'Data' sheet; sheets={xls.sheet_names}")
    raw = pd.read_excel(xls, sheet_name="Data", header=None)

    ncols = raw.shape[1]
    for c in (_COL_DATE, _COL_PRICE, _COL_DIV, _COL_EARN, _COL_CAPE):
        if c >= ncols:
            raise RuntimeError(
                f"Data sheet has only {ncols} cols; expected column index {c}. "
                "Shiller may have re-laid-out the workbook — parser needs review."
            )

    out = pd.DataFrame(
        {
            "date": _decode_shiller_date(raw.iloc[:, _COL_DATE]),
            "price": pd.to_numeric(raw.iloc[:, _COL_PRICE], errors="coerce"),
            "dividend": pd.to_numeric(raw.iloc[:, _COL_DIV], errors="coerce"),
            "earnings": pd.to_numeric(raw.iloc[:, _COL_EARN], errors="coerce"),
            "cape": pd.to_numeric(raw.iloc[:, _COL_CAPE], errors="coerce"),
        }
    )
    # Drop header/footnote rows (no valid date) and require a price so we don't
    # keep pure-junk rows. CAPE is legitimately NaN in the first decade.
    out = out[out["date"].notna() & out["price"].notna()].copy()
    out = out.sort_values("date").reset_index(drop=True)

    if out.empty:
        raise RuntimeError("parsed zero valid rows from Data sheet")
    if not out["date"].is_monotonic_increasing:
        raise RuntimeError("parsed dates not monotonic — parser/layout mismatch")
    if out["date"].iloc[0].year > 1871:
        raise RuntimeError(
            f"first parsed date is {out['date'].iloc[0].date()}, expected 1871 — "
            "header offset likely wrong"
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        default=str(OUT_PATH),
        help=f"Output CSV path (default {OUT_PATH}).",
    )
    args = ap.parse_args()

    MACRO_DIR.mkdir(parents=True, exist_ok=True)
    xls_bytes = _fetch_workbook()
    df = parse_data_sheet(xls_bytes)

    out_path = Path(args.out)
    df.to_csv(out_path, index=False, date_format="%Y-%m-%d")

    print("\n=== summary ===")
    print(f"  wrote {out_path}")
    print(f"  rows={len(df)}  {df['date'].iloc[0].date()} -> {df['date'].iloc[-1].date()}")
    print(f"  cape non-null: {int(df['cape'].notna().sum())} / {len(df)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
