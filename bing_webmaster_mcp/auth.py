"""Credential application with an interface that can later host OAuth2."""

from __future__ import annotations

from typing import Any, Protocol

from .config import Settings


class AuthProvider(Protocol):
    def apply(self, params: dict[str, Any], headers: dict[str, str]) -> None: ...


class ApiKeyAuth:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def apply(self, params: dict[str, Any], headers: dict[str, str]) -> None:
        params["apikey"] = self._api_key


def build_auth(settings: Settings) -> AuthProvider:
    if settings.api_key is None:
        from .errors import AuthFailed

        raise AuthFailed("BING_WM_API_KEY is required for Bing Webmaster API calls")
    return ApiKeyAuth(settings.api_key.get_secret_value())
