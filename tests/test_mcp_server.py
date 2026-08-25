from __future__ import annotations

import pytest

from bing_webmaster_mcp import mcp_server
from bing_webmaster_mcp.writes import WRITE_OPS


def test_no_mcp_tool_can_apply_or_reject_a_plan() -> None:
    names = mcp_server.tool_names()
    assert not any("apply" in name or "reject" in name for name in names)


def test_every_write_has_only_a_plan_tool() -> None:
    names = set(mcp_server.tool_names())
    for operation in WRITE_OPS:
        assert f"bing_plan_{operation}" in names
        assert f"bing_{operation}" not in names


def test_all_reads_and_plan_inspection_are_registered() -> None:
    names = set(mcp_server.tool_names())
    assert set(mcp_server.READ_TOOLS) <= names
    assert {"bing_plan_list", "bing_plan_show"} <= names


def test_names_are_unique() -> None:
    assert len(mcp_server.tool_names()) == len(set(mcp_server.tool_names()))


def test_plan_descriptions_warn_that_nothing_was_sent() -> None:
    for name in mcp_server.tool_names():
        if name.startswith("bing_plan_") and name not in {"bing_plan_list", "bing_plan_show"}:
            description = mcp_server.TOOL_SPECS[name].description.casefold()
            assert "sends nothing" in description
            assert "do not" in description


@pytest.mark.parametrize("name", sorted(mcp_server.READ_TOOLS))
def test_read_tools_map_to_coroutines(name: str) -> None:
    import inspect

    assert inspect.iscoroutinefunction(mcp_server.READ_TOOLS[name])


async def test_sdk_server_lists_the_same_tools() -> None:
    mcp_server.build_server()
    result = await mcp_server.list_tools()
    assert [tool.name for tool in result.tools] == mcp_server.tool_names()


async def test_error_results_keep_public_error_contract() -> None:
    result = await mcp_server.call_tool("bing_url_info", {})
    assert result.is_error is True
    assert result.structured_content["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("bing_link_counts", {"site_url": "https://a.example", "page": "one"}),
        ("bing_site_roles", {"site_url": "https://a.example", "include_all_subdomains": "yes"}),
        ("bing_children_url_info", {"site_url": "https://a.example", "url": ["https://a.example"]}),
        ("bing_plan_submit_url_batch", {"site_url": "https://a.example", "url_list": [1, 2]}),
        ("bing_plan_save_crawl_settings", {"site_url": "https://a.example", "crawl_settings": "x"}),
    ],
)
async def test_argument_types_are_enforced_by_the_server(name: str, arguments: dict) -> None:
    result = await mcp_server.call_tool(name, arguments)
    assert result.is_error
    assert "INVALID_REQUEST" in result.content[0].text


async def test_a_boolean_is_not_accepted_where_an_integer_is_declared() -> None:
    result = await mcp_server.call_tool(
        "bing_plan_add_page_preview_block",
        {"site_url": "https://a.example", "url": "https://a.example/p", "reason": True},
    )
    assert result.is_error
