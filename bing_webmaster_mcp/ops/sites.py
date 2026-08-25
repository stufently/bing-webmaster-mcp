from __future__ import annotations

from typing import Any

from ..client import BingClient
from ._common import bool_param, fetch, normalise_site


async def list_sites(client: BingClient) -> list[dict[str, Any]]:
    return await fetch(client, "GetUserSites")


async def site_roles(
    client: BingClient, site_url: str, include_all_subdomains: bool = False
) -> list[dict[str, Any]]:
    return await fetch(
        client,
        "GetSiteRoles",
        {
            "siteUrl": normalise_site(site_url),
            "includeAllSubdomains": bool_param(include_all_subdomains),
        },
    )


async def site_moves(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetSiteMoves", {"siteUrl": normalise_site(site_url)})


async def show_site(client: BingClient, site_url: str) -> dict[str, Any] | None:
    wanted = normalise_site(site_url).casefold()
    for site in await list_sites(client):
        url = site.get("Url")
        if isinstance(url, dict):
            url = url.get("value")
        if isinstance(url, str) and url.rstrip("/").casefold() == wanted:
            return site
    return None
