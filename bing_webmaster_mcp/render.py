"""Neutralise and label attacker-influenced text before returning it."""

from __future__ import annotations

import unicodedata
from typing import Any

UNTRUSTED_FIELDS = frozenset(
    {"AnchorText", "Description", "Message", "Query", "QueryString", "Title", "Url"}
)
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
