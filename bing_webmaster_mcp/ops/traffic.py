from __future__ import annotations

from typing import Any

from ..client import BingClient
from ._common import fetch, normalise_site


async def query_stats(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetQueryStats", {"siteUrl": normalise_site(site_url)})


async def query_traffic_stats(
    client: BingClient, site_url: str, query: str
) -> list[dict[str, Any]]:
    return await fetch(
        client, "GetQueryTrafficStats", {"siteUrl": normalise_site(site_url), "query": query}
    )


async def query_page_stats(client: BingClient, site_url: str, query: str) -> list[dict[str, Any]]:
    return await fetch(
        client, "GetQueryPageStats", {"siteUrl": normalise_site(site_url), "query": query}
    )


async def query_page_detail_stats(
    client: BingClient, site_url: str, query: str, page: str
) -> list[dict[str, Any]]:
    return await fetch(
        client,
        "GetQueryPageDetailStats",
        {"siteUrl": normalise_site(site_url), "query": query, "page": page},
    )


async def page_stats(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetPageStats", {"siteUrl": normalise_site(site_url)})


async def page_query_stats(client: BingClient, site_url: str, page: str) -> list[dict[str, Any]]:
    return await fetch(
        client, "GetPageQueryStats", {"siteUrl": normalise_site(site_url), "page": page}
    )


async def rank_and_traffic_stats(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetRankAndTrafficStats", {"siteUrl": normalise_site(site_url)})
