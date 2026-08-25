from __future__ import annotations

import re

import httpx
import pytest

from bing_webmaster_mcp.errors import AuthFailed, InvalidRequest, RateLimited
from bing_webmaster_mcp.ops import indexnow

HOST = "a.example"
KEY = "0123456789abcdef0123456789abcdef"


def test_generated_key_matches_protocol() -> None:
    assert re.fullmatch(r"[A-Za-z0-9-]{8,128}", indexnow.generate_key())


@pytest.mark.parametrize("bad", ["short", "x" * 129, "has_underscore", "has space"])
def test_invalid_keys_are_rejected(bad: str) -> None:
    with pytest.raises(InvalidRequest):
        indexnow.validate_key(bad)


def test_default_key_location_is_site_root() -> None:
    assert indexnow.key_location(HOST, KEY) == f"https://{HOST}/{KEY}.txt"


async def test_key_file_must_be_reachable_and_contain_key() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=f"{KEY}\n"))
    async with httpx.AsyncClient(transport=transport) as http:
        await indexnow.verify_key_file(http, HOST, KEY)


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(404), "not reachable"),
        (httpx.Response(200, text="wrong"), "does not contain"),
    ],
)
async def test_bad_key_file_is_clear(response: httpx.Response, message: str) -> None:
    transport = httpx.MockTransport(lambda request: response)
    async with httpx.AsyncClient(transport=transport) as http:
        with pytest.raises(InvalidRequest, match=message):
            await indexnow.verify_key_file(http, HOST, KEY)


async def test_submit_posts_documented_batch_body() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.read()
        return httpx.Response(200, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await indexnow.submit(http, HOST, KEY, [f"https://{HOST}/p"])
    assert seen["url"] == indexnow.ENDPOINT
    assert b'"host":"a.example"' in seen["body"]
    assert result["meaning"] == "received"


async def test_batch_over_10000_is_refused_without_network() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    urls = [f"https://{HOST}/{number}" for number in range(indexnow.MAX_BATCH + 1)]
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(InvalidRequest, match="10000"):
            await indexnow.submit(http, HOST, KEY, urls)
    assert calls == 0


async def test_subpath_key_only_authorizes_urls_below_subpath() -> None:
    location = f"https://{HOST}/news/{KEY}.txt"
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200))
    ) as http:
        with pytest.raises(InvalidRequest, match="key path"):
            await indexnow.submit(http, HOST, KEY, [f"https://{HOST}/shop/p"], location)


@pytest.mark.parametrize(
    ("status", "expected"),
    [(200, "received"), (202, "accepted")],
)
async def test_success_codes_are_explained(status: int, expected: str) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status, request=request))
    async with httpx.AsyncClient(transport=transport) as http:
        result = await indexnow.submit(http, HOST, KEY, [f"https://{HOST}/p"])
    assert expected in result["meaning"]


@pytest.mark.parametrize(
    ("status", "expected"),
    [(400, InvalidRequest), (403, AuthFailed), (422, InvalidRequest), (429, RateLimited)],
)
async def test_error_codes_are_mapped(status: int, expected: type[Exception]) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status, request=request))
    async with httpx.AsyncClient(transport=transport) as http:
        with pytest.raises(expected):
            await indexnow.submit(http, HOST, KEY, [f"https://{HOST}/p"])


async def test_verify_happens_before_submission() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(404, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(InvalidRequest):
            await indexnow.verify_and_submit(http, HOST, KEY, [f"https://{HOST}/p"])
    assert calls == [indexnow.key_location(HOST, KEY)]


@pytest.mark.parametrize("host", ["[abc", "a b.example", "a.example:8080", "-bad.example", ""])
def test_unusable_indexnow_hosts_raise_a_public_error(host: str) -> None:
    with pytest.raises(InvalidRequest):
        indexnow.validate_host(host)


def test_unparsable_key_location_and_urls_stay_in_the_taxonomy() -> None:
    with pytest.raises(InvalidRequest):
        indexnow.validate_key_location(HOST, KEY, "https://[abc")
    with pytest.raises(InvalidRequest):
        indexnow.validate_urls(HOST, KEY, ["https://[abc"])
