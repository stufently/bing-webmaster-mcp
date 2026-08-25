from __future__ import annotations

import pytest

from bing_webmaster_mcp.auth import ApiKeyAuth, build_auth
from bing_webmaster_mcp.config import Settings
from bing_webmaster_mcp.errors import AuthFailed, PolicyDenied


def test_settings_read_from_environment(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("BING_WM_API_KEY", "secret-key")
    monkeypatch.setenv("BING_WM_STATE_DIR", str(tmp_path))
    settings = Settings.load()
    assert settings.api_key.get_secret_value() == "secret-key"
    assert settings.calls_per_second == 5.0
    assert settings.plan_ttl_seconds == 900


def test_missing_key_is_an_auth_error(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("BING_WM_API_KEY", raising=False)
    monkeypatch.setenv("BING_WM_STATE_DIR", str(tmp_path))
    with pytest.raises(AuthFailed):
        Settings.load()


def test_indexnow_only_settings_can_load_without_bing_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.delenv("BING_WM_API_KEY", raising=False)
    monkeypatch.setenv("BING_WM_STATE_DIR", str(tmp_path))
    assert Settings.load(require_api_key=False).api_key is None


def test_key_does_not_leak_from_repr(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("BING_WM_API_KEY", "secret-key")
    monkeypatch.setenv("BING_WM_STATE_DIR", str(tmp_path))
    assert "secret-key" not in repr(Settings.load())


def test_denied_sites_ignore_case_and_trailing_slash(tmp_path) -> None:
    settings = Settings(api_key="k", state_dir=tmp_path, denied_sites=("https://Locked.example/",))
    with pytest.raises(PolicyDenied):
        settings.check_site_allowed("https://locked.example")


def test_apikey_auth_uses_the_query_string() -> None:
    params: dict[str, object] = {}
    headers: dict[str, str] = {}
    ApiKeyAuth("abc").apply(params, headers)
    assert params == {"apikey": "abc"}
    assert headers == {}


def test_build_auth_returns_apikey_auth(tmp_path) -> None:
    assert isinstance(build_auth(Settings(api_key="abc", state_dir=tmp_path)), ApiKeyAuth)
