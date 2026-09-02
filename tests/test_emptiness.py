from __future__ import annotations

from typing import Any

import pytest

from bing_webmaster_mcp.emptiness import (
    EMPTY_RESPONSE_NOTE,
    empty_response_report,
    returned_no_rows,
)


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"result": []},
        # GetLinkCounts for a site whose GetCrawlStats reported 1700 inbound links.
        {"Links": [], "TotalPages": 0},
        # The bing_crawl_issues summary for a site with 4 crawl errors in GetCrawlStats.
        {"total": 0, "categories": {}, "http_codes": {}, "issues": []},
    ],
)
def test_a_response_carrying_no_rows_is_recognised_as_silence(payload: Any) -> None:
    assert returned_no_rows(payload) is True


@pytest.mark.parametrize(
    "payload",
    [
        [{"Url": "https://a.example"}],
        [None],
        [0],
        {"Links": [{"Url": "https://a.example"}], "TotalPages": 0},
        {"total": 1, "categories": {"http_404": 1}, "http_codes": {}, "issues": [{"a": 1}]},
    ],
)
def test_a_response_carrying_rows_is_a_measurement(payload: Any) -> None:
    assert returned_no_rows(payload) is False


@pytest.mark.parametrize(
    "payload",
    [
        # A single record has no rows to be empty of, and its zeros are real readings.
        {"HttpStatus": 0, "IsPage": True},
        {"DailyQuota": 0, "MonthlyQuota": 0},
        {},
        None,
        0,
        "",
    ],
)
def test_a_record_without_row_collections_is_never_called_empty(payload: Any) -> None:
    assert returned_no_rows(payload) is False
    assert empty_response_report(payload) is None


def test_the_report_states_that_nothing_was_measured() -> None:
    report = empty_response_report([])
    assert report == {"rows_returned": 0, "measured": False, "note": EMPTY_RESPONSE_NOTE}


def test_the_note_forbids_reading_silence_as_a_clean_bill_of_health() -> None:
    note = EMPTY_RESPONSE_NOTE.casefold()
    assert "not a measurement" in note
    assert "no problems found" in note
