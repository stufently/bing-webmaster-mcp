from __future__ import annotations

import base64

import pytest

from bing_webmaster_mcp.errors import InvalidRequest
from bing_webmaster_mcp.writes import WRITE_OPS, prepare_write

SITE = "https://a.example"

EXPECTED = {
    "add_blocked_url",
    "add_connected_page",
    "add_country_region_settings",
    "add_deep_link_block",
    "add_page_preview_block",
    "add_query_parameter",
    "add_site",
    "add_site_roles",
    "enable_disable_query_parameter",
    "fetch_url",
    "remove_blocked_url",
    "remove_country_region_settings",
    "remove_deep_link_block",
    "remove_feed",
    "remove_page_preview_block",
    "remove_query_parameter",
    "remove_site",
    "remove_site_role",
    "save_crawl_settings",
    "submit_content",
    "submit_feed",
    "submit_site_move",
    "submit_url",
    "submit_url_batch",
    "verify_site",
}


def sample_args(name: str) -> dict:
    encoded = base64.b64encode(b"HTTP/1.1 200 OK\r\n\r\nhello").decode()
    extras = {
        "add_blocked_url": {
            "blocked_url": {"Url": f"{SITE}/secret", "EntityType": 0, "RequestType": 1}
        },
        "add_connected_page": {"master_url": "https://social.example/profile"},
        "add_country_region_settings": {
            "settings": {"TwoLetterIsoCountryCode": "TH", "Type": 0, "Url": SITE}
        },
        "add_deep_link_block": {
            "market": "en-US",
            "search_url": f"{SITE}/p",
            "deep_link_url": f"{SITE}/q",
        },
        "add_page_preview_block": {"url": f"{SITE}/p", "reason": 0},
        "add_query_parameter": {"query_parameter": "utm_source"},
        "add_site": {},
        "add_site_roles": {
            "delegated_url": SITE,
            "user_email": "a@b.example",
            "authentication_code": "abc",
            "is_administrator": False,
            "is_read_only": True,
        },
        "enable_disable_query_parameter": {"query_parameter": "utm_source", "is_enabled": True},
        "fetch_url": {"url": f"{SITE}/p"},
        "remove_blocked_url": {
            "blocked_url": {"Url": f"{SITE}/secret", "EntityType": 0, "RequestType": 0}
        },
        "remove_country_region_settings": {
            "settings": {"TwoLetterIsoCountryCode": "TH", "Type": 0, "Url": SITE}
        },
        "remove_deep_link_block": {
            "market": "en-US",
            "search_url": f"{SITE}/p",
            "deep_link_url": f"{SITE}/q",
        },
        "remove_feed": {"feed_url": f"{SITE}/sitemap.xml"},
        "remove_page_preview_block": {"url": f"{SITE}/p"},
        "remove_query_parameter": {"query_parameter": "utm_source"},
        "remove_site": {},
        "remove_site_role": {"site_role": {"Email": "a@b.example", "Site": SITE, "Role": 2}},
        "save_crawl_settings": {
            "crawl_settings": {"CrawlBoostEnabled": False, "CrawlRate": [1] * 24}
        },
        "submit_content": {
            "url": f"{SITE}/p",
            "http_message": encoded,
            "structured_data": "",
            "dynamic_serving": 0,
        },
        "submit_feed": {"feed_url": f"{SITE}/sitemap.xml"},
        "submit_site_move": {
            "settings": {
                "MoveScope": 0,
                "MoveType": 0,
                "SourceUrl": SITE,
                "TargetUrl": "https://b.example",
            }
        },
        "submit_url": {"url": f"{SITE}/p"},
        "submit_url_batch": {"url_list": [f"{SITE}/p"]},
        "verify_site": {},
    }
    return {"site_url": SITE, **extras[name]}


def test_registry_is_the_complete_supported_write_surface() -> None:
    assert set(WRITE_OPS) == EXPECTED
    assert all(operation.http == "POST" for operation in WRITE_OPS.values())


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_every_write_prepares_verified_camel_case_body(name: str) -> None:
    prepared = prepare_write(name, sample_args(name))
    assert prepared.body["siteUrl"] == SITE
    assert prepared.summary
    assert prepared.cost >= 1


def test_batch_cap_is_verified_and_enforced() -> None:
    args = {"site_url": SITE, "url_list": [f"{SITE}/{number}" for number in range(501)]}
    with pytest.raises(InvalidRequest, match="500"):
        prepare_write("submit_url_batch", args)


def test_content_must_be_base64_and_dynamic_serving_in_range() -> None:
    args = sample_args("submit_content")
    args["http_message"] = "not base64!"
    with pytest.raises(InvalidRequest, match="base64"):
        prepare_write("submit_content", args)
    args = sample_args("submit_content")
    args["dynamic_serving"] = 6
    with pytest.raises(InvalidRequest, match="dynamic_serving"):
        prepare_write("submit_content", args)


def test_complex_types_reject_invented_fields() -> None:
    args = sample_args("save_crawl_settings")
    args["crawl_settings"]["AjaxEnabled"] = True
    with pytest.raises(InvalidRequest, match="AjaxEnabled"):
        prepare_write("save_crawl_settings", args)
