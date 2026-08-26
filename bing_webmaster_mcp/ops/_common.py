"""Helpers shared by domain operations."""

from __future__ import annotations

import re
from typing import Any

from ..client import BingClient
from ..errors import InvalidRequest
from ..render import sanitize
from ..urls import validate_http_url

_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")


def normalise_site(site_url: str) -> str:
    """Turn operator input into the exact ``siteUrl`` Bing is given.

    The scheme is detected by parsing rather than by a case-sensitive prefix test, so
    ``FTP://x`` and ``HTTPS://x`` are judged on what they are instead of silently
    acquiring a second scheme.
    """
    site = site_url.strip()
    if not site:
        raise InvalidRequest(f"invalid site URL: {site_url!r}")
    if _SCHEME.match(site) is None:
        site = f"https://{site}"
    try:
        parsed, hostname = validate_http_url(site, "site_url")
    except InvalidRequest as exc:
        raise InvalidRequest(f"invalid site URL: {site_url!r}") from exc
    if parsed.query or parsed.fragment:
        raise InvalidRequest(f"invalid site URL: {site_url!r}")
    port = parsed.port
    # urlsplit strips the brackets an IPv6 literal needs to stay a valid authority.
    authority = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        authority = f"{authority}:{port}"
    return f"{parsed.scheme}://{authority}{parsed.path.rstrip('/')}"


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
