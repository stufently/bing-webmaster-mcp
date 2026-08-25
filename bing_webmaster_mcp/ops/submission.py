from __future__ import annotations

from typing import Any

from ..client import BingClient
from ._common import fetch, normalise_site


async def url_submission_quota(client: BingClient, site_url: str) -> dict[str, Any]:
    return await fetch(client, "GetUrlSubmissionQuota", {"siteUrl": normalise_site(site_url)})


async def content_submission_quota(client: BingClient, site_url: str) -> dict[str, Any]:
    return await fetch(client, "GetContentSubmissionQuota", {"siteUrl": normalise_site(site_url)})
