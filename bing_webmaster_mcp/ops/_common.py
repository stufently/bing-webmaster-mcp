"""Helpers shared by domain operations."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import SplitResult, urlsplit

from ..client import BingClient
from ..errors import InvalidRequest
from ..render import sanitize

# Requires "://": "example.com:8443" is a host and a port, not a scheme.
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")


def split_url(value: str, name: str) -> SplitResult:
    """``urlsplit`` inside the error taxonomy.

    ``hostname`` and ``port`` are parsed lazily, so an unbalanced bracket or a
    non-numeric port raises a bare ``ValueError`` from whichever line touches them
    first. Touching both here keeps that a public InvalidRequest.
    """
    try:
        parsed = urlsplit(value)
        _ = parsed.hostname, parsed.port
    except ValueError as exc:
        raise InvalidRequest(f"invalid URL for {name}: {value!r}") from exc
    return parsed


def normalise_site(site_url: str) -> str:
    """Turn operator input into the exact ``siteUrl`` Bing is given.

    The scheme is detected by parsing rather than by a case-sensitive prefix test, so
    ``FTP://x`` and ``HTTPS://x`` are judged on what they are instead of silently
    acquiring a second scheme.
    """
    site = site_url.strip().rstrip("/")
    if _SCHEME.match(site) is None:
        site = f"https://{site}"
    parsed = split_url(site, "site_url")
    hostname, port = parsed.hostname, parsed.port
    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or parsed.username
        or parsed.query
        or parsed.fragment
    ):
        raise InvalidRequest(f"invalid site URL: {site_url!r}")
    # urlsplit strips the brackets an IPv6 literal needs to stay a valid authority.
    authority = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        authority = f"{authority}:{port}"
    return f"{parsed.scheme}://{authority}{parsed.path}"


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
