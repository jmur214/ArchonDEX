"""
scripts/_xlsx_min.py — minimal stdlib .xlsx reader (T-136).

openpyxl/xlrd are NOT installed and new deps are propose-first (CLAUDE.md).
An .xlsx is a ZIP of XML; for the flat single-sheet tables our archivers pull
(NAAIM exposure, EPU monthly), a stdlib parse is sufficient and dependency-free.
NOT a general Excel reader: first worksheet only, no styles, shared-string +
inline-string + numeric cells, dates left as Excel serials for the caller.
Legacy binary .xls (BIFF) is NOT supported — callers must flag those sources.
"""
from __future__ import annotations

import re
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

import pandas as pd

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _col_to_idx(ref: str) -> int:
    s = re.match(r"[A-Z]+", ref).group(0)
    out = 0
    for ch in s:
        out = out * 26 + (ord(ch) - 64)
    return out - 1


def read_xlsx_first_sheet(blob: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(BytesIO(blob)) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter(
                    "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")))
        sheet_name = next(n for n in z.namelist()
                          if re.fullmatch(r"xl/worksheets/sheet1\.xml", n)) \
            if "xl/worksheets/sheet1.xml" in z.namelist() else \
            sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
        root = ET.fromstring(z.read(sheet_name))

    rows: list[dict[int, object]] = []
    for row in root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
        vals: dict[int, object] = {}
        for c in row:
            ref = c.attrib.get("r", "")
            if not ref:
                continue
            idx = _col_to_idx(ref)
            ctype = c.attrib.get("t", "n")
            v = c.find("m:v", NS)
            if ctype == "inlineStr":
                is_el = c.find("m:is", NS)
                vals[idx] = "".join(t.text or "" for t in is_el.iter(
                    "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")) \
                    if is_el is not None else None
            elif v is None:
                vals[idx] = None
            elif ctype == "s":
                vals[idx] = shared[int(v.text)]
            else:
                try:
                    vals[idx] = float(v.text)
                except (TypeError, ValueError):
                    vals[idx] = v.text
        if vals:
            rows.append(vals)
    if not rows:
        return pd.DataFrame()
    width = max(max(r) for r in rows) + 1
    table = [[r.get(i) for i in range(width)] for r in rows]
    header = [str(h) if h is not None else f"col{i}" for i, h in enumerate(table[0])]
    return pd.DataFrame(table[1:], columns=header)


def excel_serial_to_datetime(s: pd.Series) -> pd.Series:
    return pd.to_datetime(pd.to_numeric(s, errors="coerce"),
                          unit="D", origin="1899-12-30")
