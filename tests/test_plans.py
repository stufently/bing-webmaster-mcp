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


def test_outcome_is_recorded_even_when_the_ttl_elapsed_mid_apply(tmp_path) -> None:
    store = PlanStore(tmp_path, ttl_seconds=60)
    applied = store.create("x", "site", {}, "x")
    unknown = store.create("x", "site", {}, "x")
    past = datetime.now(UTC) - timedelta(seconds=1)
    store.set_expiry(applied.plan_id, past)
    store.set_expiry(unknown.plan_id, past)
    assert store.get(applied.plan_id).state == "expired"

    assert store.mark_applied(applied.plan_id).state == "applied"
    assert store.mark_unknown(unknown.plan_id).state == "unknown_outcome"


def test_reject_refuses_an_expired_or_locked_plan(tmp_path) -> None:
    from bing_webmaster_mcp.errors import PlanExpired

    store = PlanStore(tmp_path, ttl_seconds=60)
    expired = store.create("x", "site", {}, "x")
    store.set_expiry(expired.plan_id, datetime.now(UTC) - timedelta(seconds=1))
    with pytest.raises(PlanExpired):
        store.reject(expired.plan_id)

    locked = store.create("x", "site", {}, "x")
    (tmp_path / "plans" / f"{locked.plan_id}.lock").touch()
    with pytest.raises(PlanAlreadyApplied):
        store.reject(locked.plan_id)
