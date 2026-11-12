"""T-383 (B-6) — locks for the repaired 10-K / 10-Q section parser (scripts/lazy_prices/b6_parse.py).

Each fixture reproduces a failure class measured on the T-237 panel (B-6 audit, 2026-11-11):
the runaway carve from an MD&A cross-reference (40% of T-237's "ok" Item 1A), the ToC entry, the
inline-XBRL split word, running page headers, incorporation by reference (the mega-cap Item-7
"failures"), the pre-2006 Item 1A absence, and the 10-Q Part I / Part II item-number reuse.
No network, no data files.
"""
from __future__ import annotations

from scripts.lazy_prices import b6_parse as P

FILLER = " ".join(["The company faces significant competition and regulatory uncertainty."] * 40)
MDA_FILLER = " ".join(["Revenue increased due to higher volumes and improved pricing."] * 40)


def _html(*blocks: str) -> str:
    return "<html><body>" + "".join(f"<p>{b}</p>" for b in blocks) + "</body></html>"


def _tenk(**over: str) -> list[str]:
    parts = {
        "toc": "<table><tr><td>Item 1A.</td><td>Risk Factors</td><td>12</td></tr>"
               "<tr><td>Item 1B.</td><td>Unresolved Staff Comments</td><td>20</td></tr>"
               "<tr><td>Item 7.</td><td>Management's Discussion and Analysis</td><td>30</td></tr>"
               "<tr><td>Item 7A.</td><td>Quantitative and Qualitative Disclosures</td><td>40</td></tr></table>",
        "h1": "PART I", "i1": "Item 1. Business", "b1": FILLER,
        "h1a": "Item 1A. Risk Factors", "b1a": FILLER,
        "h1b": "Item 1B. Unresolved Staff Comments", "b1b": "None.",
        "h2": "Item 2. Properties", "b2": "We lease our headquarters.",
        "h7": "Item 7. Management's Discussion and Analysis of Financial Condition", "b7": MDA_FILLER,
        "h7a": "Item 7A. Quantitative and Qualitative Disclosures About Market Risk", "b7a": "Rates.",
        "h8": "Item 8. Financial Statements and Supplementary Data",
        "aud": "Report of Independent Registered Public Accounting Firm. We have audited.",
        "sig": "Pursuant to the requirements of Section 13 or 15(d) of the Securities Exchange Act",
    }
    parts.update(over)
    return [v for v in parts.values() if v]


def test_clean_10k_carves_both_sections_terminated_by_successor():
    rec = P.parse_document(_html(*_tenk()), "10-K", "2015-12-31")
    assert rec["risk_status"] == "OK" and rec["risk_terminator"] == "1B"
    assert rec["mda_status"] == "OK" and rec["mda_terminator"] == "7A"
    assert "competition" in rec["risk_text"] and "Unresolved" not in rec["risk_text"]
    assert "Revenue increased" in rec["mda_text"] and "Report of Independent" not in rec["mda_text"]


def test_mda_crossref_to_item_1a_cannot_become_the_risk_section():
    """THE T-237 defect: 'Item 1A. Risk Factors' quoted inside MD&A's forward-looking paragraph,
    no terminator after it. The runaway must be rejected and the real section kept."""
    b7 = MDA_FILLER + ' For more, see "Item 1A. Risk Factors" of this report. ' + MDA_FILLER
    rec = P.parse_document(_html(*_tenk(b7=b7)), "10-K", "2015-12-31")
    assert rec["risk_status"] == "OK"
    assert "Revenue increased" not in rec["risk_text"]
    assert "Report of Independent" not in rec["risk_text"]


def test_line_start_crossref_to_item_1a_with_no_terminator_is_rejected():
    """Even a LINE-START 'Item 1A. Risk Factors' (a block quoting the heading) is rejected when the
    next distinct heading is not 1A's structural successor (here 7A)."""
    blocks = _tenk(b7=MDA_FILLER)
    i = blocks.index(MDA_FILLER)
    blocks.insert(i + 1, "Item 1A. Risk Factors")
    blocks.insert(i + 2, MDA_FILLER + " " + MDA_FILLER + " " + MDA_FILLER)
    rec = P.parse_document(_html(*blocks), "10-K", "2015-12-31")
    assert rec["risk_status"] == "OK" and rec["risk_terminator"] == "1B"
    assert "Revenue increased" not in rec["risk_text"]


def test_unterminated_section_fails_closed_never_runs_to_end_of_document():
    blocks = [b for b in _tenk() if not b.startswith(("Item 1B", "Item 2.", "None.", "We lease",
                                                      "Item 7", "Revenue", "Rates", "Item 8"))]
    rec = P.parse_document(_html(*blocks), "10-K", "2015-12-31")
    assert rec["risk_status"] != "OK"          # only the ToC stub is terminated -> TOO_SHORT
    assert rec["risk_text"] == ""
    no_toc = [b for b in blocks if not b.startswith("<table")]
    rec = P.parse_document(_html(*no_toc), "10-K", "2015-12-31")
    assert rec["risk_status"] == "NOT_LOCATED:unterminated"
    assert rec["risk_text"] == ""


def test_inline_xbrl_split_words_and_item_are_rejoined():
    blocks = _tenk(h1a="I<span>TEM</span> 1A. RIS<span>K</span> FACTORS",
                   h7="<span>I</span> TEM 7. MANAGEMENT<span>&#8217;</span>S DISCUSSION AND ANALYSIS")
    rec = P.parse_document(_html(*blocks), "10-K", "2017-06-30")
    assert rec["risk_status"] == "OK" and rec["mda_status"] == "OK"


def test_running_page_header_of_same_item_does_not_terminate():
    b7 = MDA_FILLER + "</p><p>Item 7. Management's Discussion and Analysis (continued)</p><p>" + MDA_FILLER
    rec = P.parse_document(_html(*_tenk(b7=b7)), "10-K", "2015-12-31")
    assert rec["mda_status"] == "OK" and rec["mda_words"] > 700


def test_mda_incorporated_by_reference_is_not_covered_not_a_failure():
    b7 = ("The information required by this item is incorporated herein by reference to the "
          "section captioned Management's Discussion and Analysis in the 2010 Annual Report.")
    rec = P.parse_document(_html(*_tenk(b7=b7)), "10-K", "2010-12-31")
    # the pointer leads outside this document (an Annual Report exhibit): no in-document MD&A
    assert rec["mda_status"] == "NOT_COVERED:incorporated_by_reference_external"
    assert rec["mda_text"] == ""
    assert rec["risk_status"] == "OK"


def test_pre_rule_10k_without_item_1a_is_not_covered():
    blocks = [b for b in _tenk() if not b.startswith(("Item 1A", "<table"))]
    blocks = [b for b in blocks if b != FILLER] + [FILLER]
    rec = P.parse_document(_html(*_tenk(h1a="", b1a="", toc="")), "10-K", "2004-12-31")
    assert rec["risk_status"] == "NOT_COVERED:pre_rule"
    assert rec["mda_status"] == "OK"


def test_10q_part_one_item_2_and_part_two_item_2_are_told_apart_by_title():
    doc = _html(
        "PART I — FINANCIAL INFORMATION", "Item 1. Financial Statements", "Balance sheet text.",
        "Item 2. Management's Discussion and Analysis of Financial Condition", MDA_FILLER,
        "Item 3. Quantitative and Qualitative Disclosures About Market Risk", "Rates.",
        "Item 4. Controls and Procedures", "Effective.",
        "PART II — OTHER INFORMATION", "Item 1. Legal Proceedings", "None.",
        "Item 1A. Risk Factors",
        "There have been no material changes to the risk factors disclosed in our Annual Report.",
        "Item 2. Unregistered Sales of Equity Securities and Use of Proceeds", "None.",
        "Item 6. Exhibits", "31.1 Certification",
        "Pursuant to the requirements of Section 13 or 15(d) of the Securities Exchange Act")
    rec = P.parse_document(doc, "10-Q", "2016-03-31")
    assert rec["mda_status"] == "OK" and rec["mda_terminator"] == "I3"
    assert rec["risk_status"] == "OK" and rec["risk_terminator"] == "II2"
    assert "no material changes" in rec["risk_text"]
    assert "Unregistered" not in rec["risk_text"]


def test_10q_pre_rule_missing_risk_is_not_covered():
    doc = _html("Item 2. Management's Discussion and Analysis", MDA_FILLER,
                "Item 4. Controls and Procedures", "Effective.")
    rec = P.parse_document(doc, "10-Q", "2005-09-30")
    assert rec["risk_status"] == "NOT_COVERED:pre_rule"
    assert rec["mda_status"] == "OK"


def test_plain_text_filing_keeps_its_line_breaks():
    raw = ("<DOCUMENT>\n<TYPE>10-K\n<TEXT>\nPART I\nITEM 1A. RISK FACTORS\n" + FILLER +
           "\nITEM 1B. UNRESOLVED STAFF COMMENTS\nNone.\nITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS\n"
           + MDA_FILLER + "\nITEM 8. FINANCIAL STATEMENTS\n</TEXT>\n</DOCUMENT>")
    rec = P.parse_document(raw, "10-K", "2006-12-31")
    assert rec["risk_status"] == "OK" and rec["mda_status"] == "OK"
    assert rec["mda_terminator"] == "8"


def test_toc_only_section_is_too_short_not_ok():
    """If the body never carries the heading (only the ToC does), the ToC stub must not pass."""
    blocks = _tenk(h1a="", b1a="")
    rec = P.parse_document(_html(*blocks), "10-K", "2015-12-31")
    assert rec["risk_status"] != "OK"
    assert rec["risk_text"] == ""


def test_combined_items_7_and_7a_heading_is_recognised():
    blocks = _tenk(h7="Items 7 and 7A. Management's Discussion and Analysis and Quantitative "
                      "and Qualitative Disclosures", h7a="", b7a="")
    rec = P.parse_document(_html(*blocks), "10-K", "2012-12-31")
    assert rec["mda_status"] == "OK" and rec["mda_terminator"] == "8"


def test_doc_to_text_drops_hidden_xbrl_header_and_scripts():
    raw = ("<html><head><title>x</title></head><body><ix:header><ix:hidden>dei:Secret 123"
           "</ix:hidden></ix:header><script>var a=1;</script><div>Visible text</div></body></html>")
    t = P.doc_to_text(raw)
    assert "Visible text" in t and "Secret" not in t and "var a" not in t


def _xref_index_10k(tail: list[str]) -> str:
    """The 'Form 10-K cross-reference index' layout (ETN, IBM, XOM ...): Item 7 is a pointer and
    the MD&A sits, untitled by item number, in a financial section after the signatures."""
    return _html(*_tenk(
        b7="Information required by this Item is presented in Management's Discussion and "
           "Analysis of this Form 10-K.", aud="", sig=""),
        "SIGNATURES",
        "Pursuant to the requirements of Section 13 or 15(d) of the Securities Exchange Act",
        "REPORT OF INDEPENDENT REGISTERED PUBLIC ACCOUNTING FIRM", "We have audited.",
        "MANAGEMENT’S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS.",
        MDA_FILLER * 3, *tail)


def test_mda_title_fallback_for_the_cross_reference_index_layout():
    rec = P.parse_document(_xref_index_10k(["MARKET RISK DISCLOSURE", "Rates moved."]),
                           "10-K", "2022-12-31")
    assert rec["mda_status"] == "OK" and rec["mda_source"] == "title_fallback"
    assert "Revenue increased" in rec["mda_text"] and "Rates moved" not in rec["mda_text"]
    assert rec["risk_source"] == "item"


def test_mda_title_fallback_accepts_end_of_document_only_when_clean():
    rec = P.parse_document(_xref_index_10k([]), "10-K", "2022-12-31")
    assert rec["mda_status"] == "OK" and rec["mda_source"] == "title_fallback_eof"
    # a MENTION of the auditor's report inside MD&A is not contamination (Boston Scientific 2019)
    mention = _xref_index_10k(["In addition, the Report of Independent Registered Public "
                               "Accounting Firm on the schedules appears below. " + MDA_FILLER])
    assert P.parse_document(mention, "10-K", "2022-12-31")["mda_status"] == "OK"
    # the signature boilerplate inside the carved tail IS (the carve ran past the signatures)
    dirty = _xref_index_10k([MDA_FILLER + " Pursuant to the requirements of Section 13 or 15(d) of "
                             "the Securities Exchange Act of 1934, the registrant has duly caused"])
    rec = P.parse_document(dirty, "10-K", "2022-12-31")
    assert rec["mda_status"] == "NOT_COVERED:incorporated_by_reference_external"
    assert rec["mda_text"] == ""


def test_item_1c_cybersecurity_terminates_risk_factors():
    """FY2023+ filings put Item 1C between 1A and 2. T-237's title map had no 1C, so with a
    quoted 'Item 1A. Risk Factors' in MD&A its carve ran 1A through MD&A and the auditor's report
    (reversion-checked against similarity_t237.extract_sections, 2026-11-11)."""
    blocks = _tenk(h1b="Item 1C. Cybersecurity", b1b="We maintain a program.", h2="", b2="",
                   b7=MDA_FILLER + ' See "Item 1A. Risk Factors." ' + MDA_FILLER)
    rec = P.parse_document(_html(*blocks), "10-K", "2023-12-31")
    assert rec["risk_status"] == "OK" and rec["risk_terminator"] == "1C"
    assert "Revenue increased" not in rec["risk_text"]
    assert "Report of Independent" not in rec["risk_text"]


def test_plain_text_bare_numbered_headings_without_the_word_item():
    """Omnicom's 2005 10-K (.txt) titles its body sections '7. Management's Discussion ...' with no
    'Item'; only its table of contents says 'Item 7.'."""
    raw = ("<TEXT>\nItem 7. Management's Discussion and Analysis....... 8\nItem 7A. Quantitative and "
           "Qualitative Disclosures..... 16\nItem 8. Financial Statements....... 24\n\nPART II\n"
           "7. Management's Discussion and Analysis of Financial Condition and Results of Operations\n"
           + MDA_FILLER + "\n7A. Quantitative and Qualitative Disclosures About Market Risk\nRates.\n"
           "8. Financial Statements and Supplementary Data\n</TEXT>")
    rec = P.parse_document(raw, "10-K", "2004-12-31")
    assert rec["mda_status"] == "OK" and rec["mda_words"] > 300 and rec["mda_source"] == "item"


def test_10q_integrated_layout_mda_by_title_and_absent_item_1a():
    doc = _html("PART I", "Management’s Discussion and Analysis of Financial Condition and Results "
                "of Operations (Item 2)", MDA_FILLER, "CONSOLIDATED BALANCE SHEET", "Assets 100",
                "PART II — OTHER INFORMATION", "Item 1. Legal Proceedings", "None.",
                "Item 2. Unregistered Sales of Equity Securities", "None.", "Item 6. Exhibits", "31.1")
    rec = P.parse_document(doc, "10-Q", "2016-09-30")
    assert rec["mda_status"] == "OK" and rec["mda_source"] == "title_fallback"
    assert rec["risk_status"] == "NOT_COVERED:item_absent"


def test_incorporated_into_this_item_by_reference_is_recognised():
    """WFC 2018: 'That information is incorporated into this item by reference.'"""
    b1a = ("Information in response to this Item 1A can be found in the 2017 Annual Report to "
           "Stockholders under Financial Review. That information is incorporated into this item by "
           "reference.")
    rec = P.parse_document(_html(*_tenk(b1a=b1a)), "10-K", "2017-12-31")
    assert rec["risk_status"] == "NOT_COVERED:incorporated_by_reference"


def test_icfr_reports_at_the_end_of_item_7_are_trimmed_not_contamination():
    """Boston Scientific (2019 10-K) closes Item 7 with management's and the auditor's ICFR
    reports, then Item 7A. The MD&A ends where those reports begin."""
    b7 = (MDA_FILLER + "</p><p>Management's Report on Internal Control over Financial Reporting</p>"
          "<p>Our management is responsible.</p><p>Report of Independent Registered Public "
          "Accounting Firm</p><p>We have audited the internal control.")
    rec = P.parse_document(_html(*_tenk(b7=b7)), "10-K", "2018-12-31")
    assert rec["mda_status"] == "OK" and rec["mda_source"] == "item_trimmed_icfr"
    assert "We have audited" not in rec["mda_text"] and "Revenue increased" in rec["mda_text"]


def test_financial_review_titled_mda_in_a_10q():
    """WFC's 10-Qs title the MD&A 'FINANCIAL REVIEW'; the only 'Item 2' line is in the ToC."""
    doc = _html("Item 2. Management's Discussion and Analysis (Financial Review) 2",
                "Item 3. Quantitative and Qualitative Disclosures About Market Risk 37",
                "FINANCIAL REVIEW", MDA_FILLER,
                "Controls and Procedures", "Disclosure controls are effective.",
                "PART II — OTHER INFORMATION", "Item 1A. Risk Factors",
                "There have been no material changes to the risk factors in our annual report.",
                "Item 6. Exhibits", "31.1")
    rec = P.parse_document(doc, "10-Q", "2023-03-31")
    assert rec["mda_status"] == "OK" and rec["mda_source"] == "title_fallback"
    assert "Revenue increased" in rec["mda_text"]
