"""RETIRED 2026-07-30 (T-335) — the GDELT daily-tone collector.

Archived per `[NN-ARCHIVE]`; NOT deleted. Retired for USELESSNESS, not brokenness:

  * NO CONSUMER. Zero code references to the series anywhere in the repo (verified by
    grep across *.py/*.yml/*.json); the only mention is one May-2026 spec doc. It
    violated the consumer-less-archiving rule retroactively (T-136 lineage).
  * THE ARCHIVED FORM CANNOT SERVE THE PROPOSED USE. What it collected is a DAILY
    AGGREGATE tone index over 3 fixed macro queries. The only use ever proposed was
    per-name event-tape breadth, which this shape cannot supply at any history depth.

CORRECTION TO THE TRIAGE PREMISE (stated for the record): the collector was NOT
permanently broken. D/T-335b reported the parquet stale to 2026-06-11; at retirement the
main store reached **20260729** (1,128 rows) — i.e. the intermittent GDELT 503s had
cleared and the daily job was collecting again. So retirement rests on the consumer
argument alone. Had a consumer existed, this would have been a FIX.

If a consumer ever materializes, GDELT-as-event-tape needs a PURPOSE-BUILT collector
(per-name/per-event granularity, GDELT v2 events or BigQuery bulk — not the doc-API tone
timeline). The existing parquet (data/macro_data/alt/gdelt_tone_timelines.parquet) is
kept as-is; nothing is thrown away.
"""
# --- the retired collector, verbatim as it ran (needs the module's _get/_append/UA) ---
def pull_gdelt_timelines() -> str:
    got = []
    for bucket, query in [
        ("geopolitics", '"geopolitical risk"'),
        ("fed_policy", '"federal reserve"'),
        ("recession", "recession"),
    ]:
        try:
            url = ("https://api.gdeltproject.org/api/v2/doc/doc?query="
                   + urllib.request.quote(query)
                   + "&mode=timelinetone&timespan=12m&format=json")
            data = json.loads(_get(url, timeout=60))
            series = data["timeline"][0]["data"]
            df = pd.DataFrame(series)
            df["bucket"] = bucket
            df["archive_vintage"] = SNAP_DATE
            _append(df, OUT_DIR / "gdelt_tone_timelines.parquet",
                    ["date", "bucket"])
            got.append(f"{bucket}({len(df)})")
        except Exception as e:
            got.append(f"{bucket} FAILED ({type(e).__name__})")
        time.sleep(6.0)  # GDELT fair-use: one request per 5 seconds (429 otherwise)
    return ("gdelt: " + ", ".join(got)
            + " | NOTE: 1979+ BULK events = BigQuery/bulk job, flagged follow-up")

