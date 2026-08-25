from __future__ import annotations

import json

from click.testing import CliRunner
from fakes import bing_transport, fake_settings

from bing_webmaster_mcp import cli


def test_sites_list_prints_json(tmp_path, monkeypatch) -> None:
    transport = bing_transport({"GetUserSites": [{"Url": "https://a.example"}]})
    monkeypatch.setattr(cli, "_load_settings", lambda **kwargs: fake_settings(tmp_path))
    monkeypatch.setattr(cli, "_transport", lambda: transport)
    result = CliRunner().invoke(cli.main, ["sites", "list", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [{"Url": {"value": "https://a.example", "untrusted": True}}]


def test_human_list_is_a_table(tmp_path, monkeypatch) -> None:
    transport = bing_transport({"GetUserSites": [{"Url": "https://a.example", "IsVerified": True}]})
    monkeypatch.setattr(cli, "_load_settings", lambda **kwargs: fake_settings(tmp_path))
    monkeypatch.setattr(cli, "_transport", lambda: transport)
    result = CliRunner().invoke(cli.main, ["sites", "list"])
    assert result.exit_code == 0
    assert "Url" in result.output
    assert "IsVerified" in result.output


def test_public_errors_are_json_and_nonzero(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cli, "_load_settings", lambda **kwargs: fake_settings(tmp_path))
    monkeypatch.setattr(cli, "_transport", lambda: bing_transport({}))
    result = CliRunner().invoke(cli.main, ["sites", "list", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output)["code"] == "INVALID_REQUEST"


def test_plan_submit_url_checks_quota_and_records_only(tmp_path, monkeypatch) -> None:
    transport = bing_transport({"GetUrlSubmissionQuota": {"DailyQuota": 1}})
    monkeypatch.setattr(cli, "_load_settings", lambda **kwargs: fake_settings(tmp_path))
    monkeypatch.setattr(cli, "_transport", lambda: transport)
    result = CliRunner().invoke(
        cli.main,
        ["plan", "submit-url", "a.example", "https://a.example/p", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["plan_id"]
    assert [request.url.path.rsplit("/", 1)[-1] for request in transport.calls] == [
        "GetUrlSubmissionQuota"
    ]


def test_apply_prompts_and_can_be_aborted(tmp_path, monkeypatch) -> None:
    settings = fake_settings(tmp_path)
    monkeypatch.setattr(cli, "_load_settings", lambda **kwargs: settings)
    monkeypatch.setattr(cli, "_transport", lambda: bing_transport({"AddSite": None}))
    plan = cli.run_async(cli._create_plan("add_site", {"site_url": "https://a.example"}))
    result = CliRunner().invoke(cli.main, ["plan", "apply", plan.plan_id], input="n\n")
    assert result.exit_code == 1
    assert "Aborted" in result.output


def test_all_required_command_groups_exist() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.main, ["--help"])
    assert result.exit_code == 0
    for group in (
        "sites",
        "traffic",
        "index",
        "crawl",
        "links",
        "keywords",
        "sitemaps",
        "plan",
        "indexnow",
    ):
        assert group in result.output
