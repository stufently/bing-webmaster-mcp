"""Tell "Bing reported none" apart from "Bing reported nothing".

Several of the older endpoints answer some accounts with an empty collection while
another endpoint reports plenty for the same site at the same moment: ``GetLinkCounts``
returned no links for a site whose ``GetCrawlStats`` put ``InLinks`` at 1700 in the same
minute, and ``GetCrawlIssues`` and ``GetFetchedUrls`` were empty for that site too. The
empty answer is not a zero, and nothing in the payload says which of the two it is.

A caller that reads it as a measurement concludes "no problems found" from silence,
which is the one conclusion the data cannot support. So an empty read is labelled: the
label is what makes the difference visible, and there is no way to resolve it from the
response alone.
"""

from __future__ import annotations

from typing import Any

EMPTY_RESPONSE_NOTE = (
    "Bing returned no rows for this read. That is NOT a measurement and does NOT mean "
    "the site has none: this endpoint answers empty both for a site with nothing to "
    "report and for one Bing simply did not report on. Observed on a live account: "
    "bing_link_counts, bing_crawl_issues and bing_fetched_urls all returned empty for a "
    "site whose bing_crawl_stats reported 1700 inbound links and 4 crawl errors at the "
    "same moment. Report this as 'Bing returned nothing', never as 'no problems found', "
    "and corroborate with another read before drawing any conclusion."
)


def _row_containers(value: Any) -> list[list[Any]]:
    """The lists a response uses to carry its rows.

    A bare list is the rows. A mapping is either a single record - ``UrlInfo``, a quota,
    crawl settings, which have no rows and are never called empty - or a container whose
    list-valued fields hold them (``{"Links": [...], "TotalPages": 0}``). A count beside
    those rows is not evidence of its own: ``TotalPages: 0`` is exactly as silent as the
    empty ``Links`` it describes.
    """
    if isinstance(value, list):
        return [value]
    if isinstance(value, dict):
        return [item for item in value.values() if isinstance(item, list)]
    return []


def returned_no_rows(value: Any) -> bool:
    """Whether Bing carried rows in this response and every one of them came back empty."""
    containers = _row_containers(value)
    return bool(containers) and not any(containers)


def empty_response_report(value: Any) -> dict[str, Any] | None:
    """The label for an empty read, or ``None`` when the read actually returned rows."""
    if not returned_no_rows(value):
        return None
    return {"rows_returned": 0, "measured": False, "note": EMPTY_RESPONSE_NOTE}
