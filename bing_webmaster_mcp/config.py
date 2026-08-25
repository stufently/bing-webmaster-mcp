"""Environment-first settings. Secret values never appear in representations."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import AuthFailed, InvalidRequest, PolicyDenied


def _default_state_dir() -> Path:
    return Path.home() / ".local" / "state" / "bing-webmaster-mcp"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BING_WM_", extra="ignore")

    api_key: SecretStr
    base_url: str = "https://ssl.bing.com/webmaster/api.svc/json"
    calls_per_second: float = Field(default=5.0, gt=0)
    max_attempts: int = Field(default=3, ge=1, le=10)
    plan_ttl_seconds: int = Field(default=900, gt=0)
    state_dir: Path = Field(default_factory=_default_state_dir)
    denied_sites: tuple[str, ...] = ()
    max_writes_per_day: int | None = Field(default=None, gt=0)
    http_host: str = "127.0.0.1"
    http_port: int = Field(default=8765, ge=1, le=65535)
    http_bearer_token: SecretStr | None = None

    @classmethod
    def load(cls) -> Settings:
        try:
            return cls()
        except ValidationError as exc:
            missing_key = any(error["loc"] == ("api_key",) for error in exc.errors())
            error_type = AuthFailed if missing_key else InvalidRequest
            raise error_type(
                "BING_WM_API_KEY is not set" if missing_key else "invalid BING_WM_* configuration",
                suggestion=(
                    "create a key in Bing Webmaster Tools -> Settings -> API Access"
                    if missing_key
                    else "check the named environment variables"
                ),
                details={"fields": [str(error["loc"][0]) for error in exc.errors()]},
            ) from exc

    def check_site_allowed(self, site_url: str) -> None:
        if _normalise_for_policy(site_url) in {
            _normalise_for_policy(site) for site in self.denied_sites
        }:
            raise PolicyDenied(
                f"{site_url} is in BING_WM_DENIED_SITES",
                suggestion="remove it from the denylist only after reviewing the policy",
            )


def _normalise_for_policy(site_url: str) -> str:
    return site_url.strip().rstrip("/").casefold()
