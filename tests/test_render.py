from __future__ import annotations

import json

from bing_webmaster_mcp.render import REDACTED, redact_secrets, sanitize, sanitize_text


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


def test_verification_secrets_are_redacted_by_default() -> None:
    result = redact_secrets(
        {"Url": "https://a.example", "IsVerified": True, "AuthenticationCode": "auth-secret"}
    )
    assert result == {
        "Url": "https://a.example",
        "IsVerified": True,
        "AuthenticationCode": REDACTED,
    }
    assert "auth-secret" not in json.dumps(result)


def test_every_secret_field_is_redacted_however_deeply_it_is_nested() -> None:
    payload = [{"Roles": [{"DelegatedCode": "d", "DnsVerificationCode": "n", "Email": "a@b.c"}]}]
    assert redact_secrets(payload) == [
        {"Roles": [{"DelegatedCode": REDACTED, "DnsVerificationCode": REDACTED, "Email": "a@b.c"}]}
    ]


def test_an_absent_code_is_never_claimed_to_exist() -> None:
    """Redacting a null would report an ownership proof where Bing reported none."""
    assert redact_secrets({"DelegatedCode": None, "AuthenticationCode": ""}) == {
        "DelegatedCode": None,
        "AuthenticationCode": "",
    }


def test_the_marker_says_what_was_removed() -> None:
    assert "redacted" in REDACTED
    assert "verification secret" in REDACTED
