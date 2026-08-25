from __future__ import annotations

from bing_webmaster_mcp.render import sanitize, sanitize_text


def test_controls_and_bidi_marks_are_neutralised() -> None:
    assert sanitize_text("a\x1b[31mb\x07c\u202eevil") == "a[31mbcevil"


def test_newlines_and_tabs_survive() -> None:
    assert sanitize_text("a\nb\tc") == "a\nb\tc"


def test_long_text_is_truncated_with_marker() -> None:
    result = sanitize_text("x" * 5000)
    assert result.endswith("… [truncated]")
    assert len(result) == 2000 + len("… [truncated]")


def test_untrusted_fields_are_marked_recursively() -> None:
    assert sanitize({"Links": [{"AnchorText": "a\x00b", "Clicks": 1}]}) == {
        "Links": [{"AnchorText": {"value": "ab", "untrusted": True}, "Clicks": 1}]
    }


def test_query_strings_and_urls_are_untrusted() -> None:
    result = sanitize({"Query": "x", "QueryString": "a=b", "Url": "https://a"})
    assert all(result[key]["untrusted"] for key in result)
