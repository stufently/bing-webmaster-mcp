from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

from bing_webmaster_mcp.audit import AuditLog
from bing_webmaster_mcp.errors import InvalidRequest, PlanAlreadyApplied, PlanNotFound
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


def test_plan_writer_handles_partial_os_writes(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_write = os.write

    def partial_write(descriptor: int, data: bytes) -> int:
        return real_write(descriptor, data[:7])

    monkeypatch.setattr("bing_webmaster_mcp.plans.os.write", partial_write)
    store = PlanStore(tmp_path, ttl_seconds=60)
    plan = store.create("x", "https://a.example", {"value": "x" * 100}, "partial")

    assert store.get(plan.plan_id).summary == "partial"


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


def test_lock_cleanup_never_unlinks_a_replacement_lock(tmp_path) -> None:
    store = PlanStore(tmp_path, ttl_seconds=60)
    plan = store.create("x", "site", {}, "x")
    lock = tmp_path / "plans" / f"{plan.plan_id}.lock"

    with store._locked(plan.plan_id, "wait"):
        lock.unlink()
        lock.write_text("pid=999999\n")

    assert lock.read_text() == "pid=999999\n"


def test_recover_stale_lock_marks_an_unfinished_plan_unknown(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = PlanStore(tmp_path, ttl_seconds=60)
    plan = store.create("x", "site", {}, "x")
    lock = tmp_path / "plans" / f"{plan.plan_id}.lock"
    lock.write_text("pid=12345\n")
    monkeypatch.setattr("bing_webmaster_mcp.plans._pid_is_alive", lambda _pid: False)

    recovered, owner_pid = store.recover_lock(plan.plan_id, AuditLog(tmp_path))

    assert owner_pid == 12345
    assert recovered.state == "unknown_outcome"
    assert not lock.exists()
    assert AuditLog(tmp_path).entries()[-1]["event"] == "plan_lock_recovered"


def test_recover_stale_lock_preserves_a_terminal_outcome(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = PlanStore(tmp_path, ttl_seconds=60)
    plan = store.create("x", "site", {}, "x")
    store.mark_applied(plan.plan_id)
    lock = tmp_path / "plans" / f"{plan.plan_id}.lock"
    lock.write_text("pid=12345\n")
    monkeypatch.setattr("bing_webmaster_mcp.plans._pid_is_alive", lambda _pid: False)

    recovered, _ = store.recover_lock(plan.plan_id, AuditLog(tmp_path))

    assert recovered.state == "applied"
    assert not lock.exists()


def test_recover_lock_refuses_a_live_owner_or_missing_lock(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = PlanStore(tmp_path, ttl_seconds=60)
    plan = store.create("x", "site", {}, "x")
    lock = tmp_path / "plans" / f"{plan.plan_id}.lock"
    lock.write_text("pid=12345\n")
    monkeypatch.setattr("bing_webmaster_mcp.plans._pid_is_alive", lambda _pid: True)

    with pytest.raises(PlanAlreadyApplied):
        store.recover_lock(plan.plan_id, AuditLog(tmp_path))
    assert lock.exists()

    lock.unlink()
    with pytest.raises(InvalidRequest):
        store.recover_lock(plan.plan_id, AuditLog(tmp_path))

    lock.write_bytes(b"\xff")
    with pytest.raises(InvalidRequest, match="malformed"):
        store.recover_lock(plan.plan_id, AuditLog(tmp_path))
