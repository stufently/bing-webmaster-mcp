from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from fakes import bing_transport, fake_settings

from bing_webmaster_mcp.client import BingClient
from bing_webmaster_mcp.ops import (
    blocking,
    crawl,
    geo,
    keywords,
    links,
    params,
    sitemaps,
    sites,
    submission,
    traffic,
)
from bing_webmaster_mcp.ops._common import normalise_site


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("example.com", "https://example.com"),
        ("https://example.com/", "https://example.com"),
        ("http://example.com", "http://example.com"),
        ("  https://example.com  ", "https://example.com"),
    ],
)
def test_site_normalisation(raw: str, expected: str) -> None:
    assert normalise_site(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "https://",
        "http://",
        "ftp://example.com",
        "FTP://example.com",
        "mailto:a@b.example",
        "[abc",
        "https://example.com?a=1",
        "https://a b.example",
        "https://-bad.example",
        "https://a_example",
        "https://a.example/shop/../admin",
        "https://a.example/shop/%2e%2e/admin",
    ],
)
def test_unusable_site_urls_are_rejected(raw: str) -> None:
    from bing_webmaster_mcp.errors import InvalidRequest

    with pytest.raises(InvalidRequest):
        normalise_site(raw)


def test_uppercase_scheme_is_normalised_not_prefixed() -> None:
    assert normalise_site("HTTPS://Example.com") == "https://example.com"


SITE_READS = [
    (sites.site_roles, "GetSiteRoles", ()),
    (sites.site_moves, "GetSiteMoves", ()),
    (traffic.query_stats, "GetQueryStats", ()),
    (traffic.query_traffic_stats, "GetQueryTrafficStats", ("shoes",)),
    (traffic.query_page_stats, "GetQueryPageStats", ("shoes",)),
    (
        traffic.query_page_detail_stats,
        "GetQueryPageDetailStats",
        ("shoes", "https://a.example/p"),
    ),
    (traffic.page_stats, "GetPageStats", ()),
    (traffic.page_query_stats, "GetPageQueryStats", ("https://a.example/p",)),
    (traffic.rank_and_traffic_stats, "GetRankAndTrafficStats", ()),
    (crawl.url_info, "GetUrlInfo", ("https://a.example/p",)),
    (crawl.url_traffic_info, "GetUrlTrafficInfo", ("https://a.example/p",)),
    (crawl.children_url_traffic_info, "GetChildrenUrlTrafficInfo", ("https://a.example/d",)),
    (crawl.crawl_stats, "GetCrawlStats", ()),
    (crawl.crawl_issues, "GetCrawlIssues", ()),
    (crawl.crawl_settings, "GetCrawlSettings", ()),
    (crawl.fetched_urls, "GetFetchedUrls", ()),
    (crawl.fetched_url_details, "GetFetchedUrlDetails", ("https://a.example/p",)),
    (submission.url_submission_quota, "GetUrlSubmissionQuota", ()),
    (submission.content_submission_quota, "GetContentSubmissionQuota", ()),
    (sitemaps.feeds, "GetFeeds", ()),
    (sitemaps.feed_details, "GetFeedDetails", ("https://a.example/sitemap.xml",)),
    (blocking.blocked_urls, "GetBlockedUrls", ()),
    (blocking.page_preview_blocks, "GetActivePagePreviewBlocks", ()),
    (blocking.deep_link_blocks, "GetDeepLinkBlocks", ()),
    (params.query_parameters, "GetQueryParameters", ()),
    (geo.country_region_settings, "GetCountryRegionSettings", ()),
    (links.link_counts, "GetLinkCounts", ()),
    (links.url_links, "GetUrlLinks", ("https://a.example/p",)),
    (links.connected_pages, "GetConnectedPages", ()),
]


@pytest.mark.parametrize(("function", "method", "args"), SITE_READS)
async def test_site_scoped_reads_route_exactly(
    tmp_path, function, method: str, args: tuple
) -> None:
    transport = bing_transport({method: []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await function(client, "a.example/", *args)
    request = transport.calls[0]
    assert request.url.path.endswith(f"/{method}")
    if request.method == "GET":
        assert request.url.params["siteUrl"] == "https://a.example"
    else:
        assert b'"siteUrl":"https://a.example"' in request.content


async def test_get_user_sites_has_no_site_parameter(tmp_path) -> None:
    transport = bing_transport({"GetUserSites": []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        assert await sites.list_sites(client) == []
    assert "siteUrl" not in transport.calls[0].url.params


async def test_children_url_info_is_a_post_with_verified_default_filters(tmp_path) -> None:
    transport = bing_transport({"GetChildrenUrlInfo": []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await crawl.children_url_info(client, "a.example", "https://a.example/d")
    request = transport.calls[0]
    assert request.method == "POST"
    assert b'"filterProperties"' in request.content
    assert all(f'"{name}":0'.encode() in request.content for name in crawl.FILTER_FIELDS)


async def test_exact_special_parameter_names(tmp_path) -> None:
    routes = {"GetSiteRoles": [], "GetUrlLinks": []}
    transport = bing_transport(routes)
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await sites.site_roles(client, "a.example", include_all_subdomains=True)
        await links.url_links(client, "a.example", "https://a.example/p", page=2)
    assert transport.calls[0].url.params["includeAllSubdomains"] == "true"
    assert transport.calls[1].url.params["link"] == "https://a.example/p"
    assert transport.calls[1].url.params["page"] == "2"


@pytest.mark.parametrize(
    ("function", "method", "args"),
    [
        (keywords.keyword, "GetKeyword", (date(2026, 8, 1), date(2026, 8, 25))),
        (keywords.keyword_stats, "GetKeywordStats", ()),
        (
            keywords.related_keywords,
            "GetRelatedKeywords",
            (date(2026, 8, 1), date(2026, 8, 25)),
        ),
    ],
)
async def test_keyword_reads_are_standalone(tmp_path, function, method: str, args: tuple) -> None:
    transport = bing_transport({method: []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await function(client, "shoes", "US", "en-US", *args)
    request = transport.calls[0]
    assert "siteUrl" not in request.url.params
    assert request.url.params["q"] == "shoes"


async def test_read_results_are_sanitized(tmp_path) -> None:
    transport = bing_transport({"GetCrawlIssues": [{"Url": "x\u202eevil", "Message": "m\x00"}]})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        rows: list[dict[str, Any]] = await crawl.crawl_issues(client, "a.example")
    assert rows[0]["Url"] == {"value": "xevil", "untrusted": True}
    assert rows[0]["Message"] == {"value": "m", "untrusted": True}


def test_site_url_with_an_unparsable_port_is_rejected() -> None:
    from bing_webmaster_mcp.errors import InvalidRequest

    with pytest.raises(InvalidRequest):
        normalise_site("https://example.com:notaport")


def test_ipv6_site_keeps_its_brackets() -> None:
    assert normalise_site("https://[2001:db8::1]/") == "https://[2001:db8::1]"
    assert normalise_site("https://[2001:db8::1]:8443/p") == "https://[2001:db8::1]:8443/p"


def test_bare_host_with_a_port_is_not_read_as_a_scheme() -> None:
    assert normalise_site("example.com:8443") == "https://example.com:8443"
