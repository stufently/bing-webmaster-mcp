"""Helpers shared by domain operations."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from ..client import BingClient
from ..errors import InvalidRequest
from ..render import sanitize


def normalise_site(site_url: str) -> str:
    site = site_url.strip().rstrip("/")
    if not site.startswith(("http://", "https://")):
        site = f"https://{site}"
    parsed = urlsplit(site)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
        raise InvalidRequest(f"invalid site URL: {site_url!r}")
    return site


async def fetch(
    client: BingClient,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    body: dict[str, Any] | None = None,
) -> Any:
    return sanitize(await client.call(method, params, body=body))


def bool_param(value: bool) -> str:
    return "true" if value else "false"
