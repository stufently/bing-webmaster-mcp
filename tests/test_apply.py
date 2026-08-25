from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fakes import bing_transport, fake_settings
from test_writes import sample_args

from bing_webmaster_mcp.apply import apply_plan
from bing_webmaster_mcp.audit import AuditLog
from bing_webmaster_mcp.client import BingClient
from bing_webmaster_mcp.errors import PlanAlreadyApplied, PlanExpired, PlanUnknownOutcome
from bing_webmaster_mcp.limits import RateLimiter
from bing_webmaster_mcp.plans import PlanStore, create_write_plan
from bing_webmaster_mcp.writes import WRITE_OPS


async def test_creating_plan_sends_nothing_and_checks_live_quota(tmp_path) -> None:
    transport = bing_transport({"GetUrlSubmissionQuota": {"DailyQuota": 1, "MonthlyQuota": 5}})
    settings = fake_settings(tmp_path)
    async with BingClient(settings, transport=transport) as client:
        plan = await create_write_plan(
            "submit_url", sample_args("submit_url"), settings=settings, client=client
        )
    assert [request.url.path.rsplit("/", 1)[-1] for request in transport.calls] == [
        "GetUrlSubmissionQuota"
    ]
    assert plan.state == "pending"


async def test_batch_larger_than_remaining_quota_is_refused(tmp_path) -> None:
    from bing_webmaster_mcp.errors import QuotaExceeded

    args = {
        "site_url": "https://a.example",
        "url_list": ["https://a.example/1", "https://a.example/2"],
    }
    transport = bing_transport({"GetUrlSubmissionQuota": {"DailyQuota": 1}})
    settings = fake_settings(tmp_path)
    async with BingClient(settings, transport=transport) as client:
        with pytest.raises(QuotaExceeded):
            await create_write_plan("submit_url_batch", args, settings=settings, client=client)


async def test_apply_is_one_shot_and_audited(tmp_path) -> None:
    settings = fake_settings(tmp_path)
    store = PlanStore(tmp_path, settings.plan_ttl_seconds)
    args = sample_args("add_site")
    plan = store.create("add_site", args["site_url"], args, "add site")
    transport = bing_transport({"AddSite": None})
    async with BingClient(settings, transport=transport) as client:
        result = await apply_plan(
            plan.plan_id,
            store=store,
            client=client,
            audit=AuditLog(tmp_path),
            limiter=RateLimiter(tmp_path, max_per_day=None),
        )
        with pytest.raises(PlanAlreadyApplied):
            await apply_plan(
                plan.plan_id,
                store=store,
                client=client,
                audit=AuditLog(tmp_path),
                limiter=RateLimiter(tmp_path, max_per_day=None),
            )
    assert result["applied"] is True
    assert len(transport.calls) == 1
    assert [entry["event"] for entry in AuditLog(tmp_path).entries()] == [
        "plan_apply_attempted",
        "plan_apply_succeeded",
    ]


async def test_expired_plan_never_reaches_upstream(tmp_path) -> None:
    settings = fake_settings(tmp_path)
    store = PlanStore(tmp_path, 1)
    plan = store.create("add_site", "https://a.example", sample_args("add_site"), "x")
    store.set_expiry(plan.plan_id, datetime.now(UTC) - timedelta(seconds=1))
    transport = bing_transport({"AddSite": None})
    async with BingClient(settings, transport=transport) as client:
        with pytest.raises(PlanExpired):
            await apply_plan(
                plan.plan_id,
                store=store,
                client=client,
                audit=AuditLog(tmp_path),
                limiter=RateLimiter(tmp_path, max_per_day=None),
            )
    assert transport.calls == []


async def test_lost_write_response_marks_unknown_and_blocks_retry(tmp_path) -> None:
    settings = fake_settings(tmp_path)
    store = PlanStore(tmp_path, 900)
    plan = store.create("add_site", "https://a.example", sample_args("add_site"), "x")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("lost", request=request)

    async with BingClient(settings, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(PlanUnknownOutcome):
            await apply_plan(
                plan.plan_id,
                store=store,
                client=client,
                audit=AuditLog(tmp_path),
                limiter=RateLimiter(tmp_path, max_per_day=None),
            )
    assert store.get(plan.plan_id).state == "unknown_outcome"
    with pytest.raises(PlanAlreadyApplied):
        store.ensure_pending(plan.plan_id)


async def test_indexnow_plan_verifies_key_then_submits(tmp_path) -> None:
    store = PlanStore(tmp_path, 900)
    args = sample_args("indexnow_submit")
    prepared = WRITE_OPS["indexnow_submit"].prepare(args)
    plan = store.create("indexnow_submit", "https://a.example", args, prepared.summary)
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.method == "GET":
            return httpx.Response(200, text=args["key"], request=request)
        return httpx.Response(200, request=request)

    result = await apply_plan(
        plan.plan_id,
        store=store,
        client=None,
        audit=AuditLog(tmp_path),
        limiter=RateLimiter(tmp_path, max_per_day=None),
        indexnow_transport=httpx.MockTransport(handler),
    )
    assert result["applied"] is True
    assert calls == [prepared.body["keyLocation"], "https://api.indexnow.org/indexnow"]


@pytest.mark.parametrize("name", sorted(name for name in WRITE_OPS if name != "indexnow_submit"))
async def test_every_write_applies_as_post(tmp_path, name: str) -> None:
    settings = fake_settings(tmp_path)
    store = PlanStore(tmp_path, 900)
    args = sample_args(name)
    prepared = WRITE_OPS[name].prepare(args)
    plan = store.create(name, args["site_url"], args, prepared.summary)
    transport = bing_transport({prepared.method: None})
    async with BingClient(settings, transport=transport) as client:
        await apply_plan(
            plan.plan_id,
            store=store,
            client=client,
            audit=AuditLog(tmp_path),
            limiter=RateLimiter(tmp_path, max_per_day=None),
        )
    assert transport.calls[0].method == "POST"
