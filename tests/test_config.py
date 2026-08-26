from __future__ import annotations

import pytest
from pydantic import ValidationError

from bing_webmaster_mcp.auth import ApiKeyAuth, build_auth
from bing_webmaster_mcp.config import Settings
from bing_webmaster_mcp.errors import AuthFailed, InvalidRequest, PolicyDenied


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


@pytest.mark.parametrize(
    "site",
    [
        "http://locked.example",
        "https://locked.example:443",
        "https://locked.example./",
        "HTTPS://Locked.Example",
        "locked.example",
    ],
)
def test_denylist_matches_on_the_host_not_the_string(tmp_path, site: str) -> None:
    settings = Settings(api_key="k", state_dir=tmp_path, denied_sites=("https://locked.example",))
    with pytest.raises(PolicyDenied):
        settings.check_site_allowed(site)


def test_denylist_does_not_swallow_a_different_host(tmp_path) -> None:
    settings = Settings(api_key="k", state_dir=tmp_path, denied_sites=("https://locked.example",))
    settings.check_site_allowed("https://other.example")
    settings.check_site_allowed("https://locked.example:8443")


def test_non_json_list_variable_is_a_public_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("BING_WM_API_KEY", "k")
    monkeypatch.setenv("BING_WM_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("BING_WM_DENIED_SITES", "https://locked.example")
    with pytest.raises(InvalidRequest):
        Settings.load()


def test_denied_site_with_a_path_covers_its_subpaths_only(tmp_path) -> None:
    settings = Settings(api_key="k", state_dir=tmp_path, denied_sites=("https://a.example/shop",))
    with pytest.raises(PolicyDenied):
        settings.check_site_allowed("https://a.example/shop/eu")
    settings.check_site_allowed("https://a.example/blog")
    settings.check_site_allowed("https://a.example")


@pytest.mark.parametrize(
    "site",
    [
        "https://a.example/shop/../admin",
        "https://a.example/shop/%2e%2e/admin",
    ],
)
def test_ambiguous_site_path_cannot_bypass_a_path_denylist(tmp_path, site: str) -> None:
    settings = Settings(api_key="k", state_dir=tmp_path, denied_sites=("https://a.example/admin",))
    with pytest.raises(InvalidRequest, match="dot segments"):
        settings.check_site_allowed(site)


def test_denied_host_covers_every_path_on_it(tmp_path) -> None:
    settings = Settings(api_key="k", state_dir=tmp_path, denied_sites=("a.example",))
    with pytest.raises(PolicyDenied):
        settings.check_site_allowed("https://a.example/shop")


def test_denied_entry_with_a_doubled_slash_still_matches(tmp_path) -> None:
    settings = Settings(api_key="k", state_dir=tmp_path, denied_sites=("a.example/shop//eu",))
    with pytest.raises(PolicyDenied):
        settings.check_site_allowed("https://a.example/shop//eu")


def test_denylist_entry_without_a_host_is_refused_at_load(tmp_path) -> None:
    with pytest.raises(ValidationError):
        Settings(api_key="k", state_dir=tmp_path, denied_sites=("/nohost",))


@pytest.mark.parametrize("entry", [".", "...", "https://."])
def test_denylist_entry_that_normalises_to_nothing_is_refused(tmp_path, entry: str) -> None:
    with pytest.raises(ValidationError):
        Settings(api_key="k", state_dir=tmp_path, denied_sites=(entry,))
