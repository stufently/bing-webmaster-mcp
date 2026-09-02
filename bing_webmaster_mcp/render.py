"""Neutralise and label attacker-influenced text, and hide secrets, before returning it."""

from __future__ import annotations

import unicodedata
from typing import Any

UNTRUSTED_FIELDS = frozenset(
    {"AnchorText", "Description", "Message", "Query", "QueryString", "Title", "Url"}
)

# Ownership proofs Bing hands back beside a site: the code that goes in the verification
# file or meta tag, the one that goes in a DNS TXT record, and the delegation code on a
# site role. Whoever holds one can claim the site in another Bing account, so they are
# credentials, not site metadata - and none of them is needed to list, audit or report
# on a site. Anything that reaches a caller reaches its transcript, its logs and its
# reports, so these are redacted everywhere by default and revealed only when an
# operator at the CLI asks for them by name.
SECRET_FIELDS = frozenset({"AuthenticationCode", "DelegatedCode", "DnsVerificationCode"})
REDACTED = "[redacted: verification secret]"
_MAX_LENGTH = 2000
_KEEP_CONTROLS = {"\n", "\t"}
_TRUNCATED = "… [truncated]"


def sanitize_text(value: str) -> str:
    cleaned = "".join(
        character
        for character in value
        if character in _KEEP_CONTROLS or not unicodedata.category(character).startswith("C")
    )
    if len(cleaned) > _MAX_LENGTH:
        return cleaned[:_MAX_LENGTH] + _TRUNCATED
    return cleaned


def _is_present(value: Any) -> bool:
    """Whether a secret field actually carries one.

    A code Bing did not set stays ``null``: replacing it with the marker would claim an
    ownership proof exists where there is none.
    """
    return value is not None and value != ""


def redact_secrets(value: Any) -> Any:
    """Replace every verification secret in a response with a self-describing marker."""
    if isinstance(value, dict):
        return {
            key: REDACTED if key in SECRET_FIELDS and _is_present(item) else redact_secrets(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            if key in UNTRUSTED_FIELDS and isinstance(item, str):
                output[key] = {"value": sanitize_text(item), "untrusted": True}
            else:
                output[key] = sanitize(item)
        return output
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value
