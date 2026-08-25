from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bing_webmaster_mcp.errors import PlanAlreadyApplied, PlanNotFound
from bing_webmaster_mcp.plans import PlanStore


def test_plan_persists_with_expiry_and_owner_only_mode(tmp_path) -> None:
    plan = PlanStore(tmp_path, ttl_seconds=60).create(
        "submit_url", "https://a.example", {"url": "https://a.example/p"}, "submit URL"
    )
    loaded = PlanStore(tmp_path, ttl_seconds=60).get(plan.plan_id)
    assert loaded.operation == "submit_url"
    assert loaded.expires_at - loaded.created_at == timedelta(seconds=60)
    assert loaded.state == "pending"
    path = tmp_path / "plans" / f"{plan.plan_id}.json"
    assert path.stat().st_mode & 0o777 == 0o600


def test_unknown_plan_and_path_traversal_are_not_found(tmp_path) -> None:
    store = PlanStore(tmp_path, ttl_seconds=60)
    with pytest.raises(PlanNotFound):
        store.get("../audit")


def test_applied_and_rejected_plans_cannot_be_reused(tmp_path) -> None:
    store = PlanStore(tmp_path, ttl_seconds=60)
    applied = store.create("x", "site", {}, "x")
    store.mark_applied(applied.plan_id)
    with pytest.raises(PlanAlreadyApplied):
        store.ensure_pending(applied.plan_id)
    rejected = store.create("x", "site", {}, "x")
    store.reject(rejected.plan_id)
    with pytest.raises(PlanAlreadyApplied):
        store.ensure_pending(rejected.plan_id)


def test_expiry_is_computed_in_utc(tmp_path) -> None:
    plan = PlanStore(tmp_path, ttl_seconds=1).create("x", "site", {}, "x")
    assert plan.is_expired(datetime.now(UTC) + timedelta(seconds=2))
