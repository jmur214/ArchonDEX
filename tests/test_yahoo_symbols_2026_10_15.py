"""ONE Yahoo symbol table (director ruling 2026-10-15): a share class is a spelling, a rename is an
identity claim, and the script that used to own the table reads the shared one."""
from __future__ import annotations

import pytest

from engines.data_manager import yahoo_symbols as ys


@pytest.mark.parametrize("ticker, expected", [
    ("BRK.B", ("BRK-B", ys.SHARE_CLASS)),        # in the table
    ("BF.B", ("BF-B", ys.SHARE_CLASS)),          # in the table
    ("MOG.A", ("MOG-A", ys.SHARE_CLASS)),        # not in the table: the mechanical rule
    ("AAPL", ("AAPL", None)),
    ("ATVI", ("ATVI", None)),                    # a self-mapping entry maps nothing
])
def test_a_share_class_is_a_SPELLING_and_a_plain_ticker_is_untouched(ticker, expected):
    assert ys.yahoo_symbol(ticker) == expected


@pytest.mark.parametrize("ticker, symbol", [("FRC", "FRCB"), ("SIVB", "SIVBQ")])
def test_a_rename_is_labelled_an_IDENTITY_claim(ticker, symbol):
    assert ys.yahoo_symbol(ticker) == (symbol, ys.RENAME)


def test_the_script_reads_the_ONE_shared_table():
    """Executed, not grepped: the script's name must BE the shared object, not a copy of it."""
    import scripts.fetch_missing_delisted as fmd
    assert fmd.YAHOO_OVERRIDES is ys.YAHOO_OVERRIDES


def test_the_most_rows_fallback_is_NOT_in_the_shared_table_module():
    assert not hasattr(ys, "YAHOO_FALLBACKS"), "the guess stays in the script; the writer never sees it"
