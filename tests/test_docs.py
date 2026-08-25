from __future__ import annotations

from pathlib import Path

from bing_webmaster_mcp.mcp_server import tool_names
from bing_webmaster_mcp.writes import WRITE_OPS

ROOT = Path(__file__).resolve().parents[1]
PITCH = (
    "bing-webmaster-mcp gives an AI agent read access to what Bing knows about your sites "
    "— traffic, indexing, crawl issues, inbound links, keywords — and a reviewed, two-step "
    "path for the operations that change something."
)


def test_pitch_is_consistent() -> None:
    for path in (ROOT / "README.md", ROOT / "llms.txt", ROOT / "pyproject.toml"):
        assert PITCH in path.read_text()


def test_readme_states_security_boundary_and_indexnow_google_fact() -> None:
    text = (ROOT / "README.md").read_text().casefold()
    assert "no apply tool" in text or "deliberately no" in text
    assert "google" in text and "does not participate" in text


def test_every_mcp_tool_and_write_is_documented() -> None:
    operations = (ROOT / "docs" / "operations.md").read_text()
    assert not [name for name in tool_names() if name not in operations]
    assert not [name for name in WRITE_OPS if name not in operations]


def test_product_boundaries_record_every_deliberate_exclusion() -> None:
    text = (ROOT / "docs" / "product-boundaries.md").read_text()
    for term in (
        "SOAP",
        "POX",
        "Bing Search",
        "Google Search Console",
        "GetDeepLinkAlgoUrls",
        "GetDeepLink",
        "UpdateDeepLink",
        "OAuth2",
        "scheduler",
    ):
        assert term in text
    assert "2026-08-25" in text


def test_configuration_names_every_setting() -> None:
    text = (ROOT / "docs" / "configuration.md").read_text()
    for name in (
        "BING_WM_API_KEY",
        "BING_WM_BASE_URL",
        "BING_WM_CALLS_PER_SECOND",
        "BING_WM_MAX_ATTEMPTS",
        "BING_WM_PLAN_TTL_SECONDS",
        "BING_WM_STATE_DIR",
        "BING_WM_DENIED_SITES",
        "BING_WM_MAX_WRITES_PER_DAY",
        "BING_WM_HTTP_HOST",
        "BING_WM_HTTP_PORT",
        "BING_WM_HTTP_BEARER_TOKEN",
    ):
        assert name in text


def test_supporting_metadata_exists() -> None:
    assert "bing-webmaster-mcp" in (ROOT / "CITATION.cff").read_text()
    assert "## Unreleased" in (ROOT / "CHANGELOG.md").read_text()
    assert len((ROOT / "llms.txt").read_text().splitlines()) >= 8
