from __future__ import annotations

from typing import Any

from ..client import BingClient
from ._common import fetch, normalise_site

FILTER_FIELDS = (
    "CrawlDateFilter",
    "DiscoveredDateFilter",
    "DocFlagsFilters",
    "HttpCodeFilters",
)


async def url_info(client: BingClient, site_url: str, url: str) -> dict[str, Any]:
    return await fetch(client, "GetUrlInfo", {"siteUrl": normalise_site(site_url), "url": url})


async def url_traffic_info(client: BingClient, site_url: str, url: str) -> dict[str, Any]:
    return await fetch(
        client, "GetUrlTrafficInfo", {"siteUrl": normalise_site(site_url), "url": url}
    )


async def children_url_info(
    client: BingClient,
    site_url: str,
    url: str,
    page: int = 0,
    filter_properties: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    filters = dict.fromkeys(FILTER_FIELDS, 0)
    if filter_properties:
        unknown = set(filter_properties) - set(FILTER_FIELDS)
        if unknown:
            from ..errors import InvalidRequest

            raise InvalidRequest(f"unknown FilterProperties fields: {sorted(unknown)}")
        filters.update(filter_properties)
    body = {
        "siteUrl": normalise_site(site_url),
        "url": url,
        "page": page,
        "filterProperties": filters,
    }
    return await fetch(client, "GetChildrenUrlInfo", body=body)


async def children_url_traffic_info(
    client: BingClient, site_url: str, url: str, page: int = 0
) -> list[dict[str, Any]]:
    return await fetch(
        client,
        "GetChildrenUrlTrafficInfo",
        {"siteUrl": normalise_site(site_url), "url": url, "page": page},
    )


async def crawl_stats(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetCrawlStats", {"siteUrl": normalise_site(site_url)})


async def crawl_issues(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetCrawlIssues", {"siteUrl": normalise_site(site_url)})


async def crawl_settings(client: BingClient, site_url: str) -> dict[str, Any]:
    return await fetch(client, "GetCrawlSettings", {"siteUrl": normalise_site(site_url)})


async def fetched_urls(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetFetchedUrls", {"siteUrl": normalise_site(site_url)})


async def fetched_url_details(client: BingClient, site_url: str, url: str) -> dict[str, Any]:
    return await fetch(
        client, "GetFetchedUrlDetails", {"siteUrl": normalise_site(site_url), "url": url}
    )
