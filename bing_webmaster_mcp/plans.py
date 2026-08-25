"""Durable one-shot plan records. Creating a plan never sends a mutation."""

from __future__ import annotations

import os
import re
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, computed_field

from .audit import AuditLog
from .client import BingClient
from .config import Settings
from .errors import (
    MalformedResponse,
    PlanAlreadyApplied,
    PlanExpired,
    PlanNotFound,
    QuotaExceeded,
)
from .ops._common import normalise_site
from .writes import prepare_write

_PLAN_ID = re.compile(r"^[0-9a-f]{32}$")


class Plan(BaseModel):
    plan_id: str
    operation: str
    site_url: str
    args: dict[str, Any]
    summary: str
    created_at: datetime
    expires_at: datetime
    applied_at: datetime | None = None
    rejected_at: datetime | None = None
    unknown_outcome_at: datetime | None = None

    @computed_field
    @property
    def state(self) -> str:
        if self.applied_at is not None:
            return "applied"
        if self.rejected_at is not None:
            return "rejected"
        if self.unknown_outcome_at is not None:
            return "unknown_outcome"
        if self.is_expired():
            return "expired"
        return "pending"

    def is_expired(self, now: datetime | None = None) -> bool:
        return (now or datetime.now(UTC)) >= self.expires_at


class PlanStore:
    def __init__(self, state_dir: Path, ttl_seconds: int) -> None:
        self._directory = Path(state_dir) / "plans"
        self._directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._directory.chmod(0o700)
        self._ttl = ttl_seconds

    def _path(self, plan_id: str) -> Path:
        if _PLAN_ID.fullmatch(plan_id) is None:
            raise PlanNotFound(f"no plan {plan_id!r}")
        return self._directory / f"{plan_id}.json"

    def create(self, operation: str, site_url: str, args: dict[str, Any], summary: str) -> Plan:
        now = datetime.now(UTC)
        plan = Plan(
            plan_id=secrets.token_hex(16),
            operation=operation,
            site_url=site_url,
            args=args,
            summary=summary,
            created_at=now,
            expires_at=now + timedelta(seconds=self._ttl),
        )
        self._write(plan)
        return plan

    def _write(self, plan: Plan) -> None:
        path = self._path(plan.plan_id)
        temporary = path.with_suffix(f".{secrets.token_hex(8)}.tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, plan.model_dump_json(indent=2).encode())
        finally:
            os.close(descriptor)
        os.replace(temporary, path)

    def get(self, plan_id: str) -> Plan:
        path = self._path(plan_id)
        if not path.exists():
            raise PlanNotFound(f"no plan {plan_id}", suggestion="run `bing-wm plan list`")
        return Plan.model_validate_json(path.read_text())

    def list(self) -> list[Plan]:
        return sorted(
            (Plan.model_validate_json(path.read_text()) for path in self._directory.glob("*.json")),
            key=lambda plan: plan.created_at,
            reverse=True,
        )

    def ensure_pending(self, plan_id: str) -> Plan:
        plan = self.get(plan_id)
        if plan.applied_at or plan.rejected_at or plan.unknown_outcome_at:
            raise PlanAlreadyApplied(f"plan {plan_id} is already {plan.state}")
        if plan.is_expired():
            raise PlanExpired(
                f"plan {plan_id} expired at {plan.expires_at.isoformat()}",
                suggestion="create a fresh plan and review its current arguments",
            )
        return plan

    def _record_outcome(self, plan_id: str, field: str) -> Plan:
        """Write a terminal state.

        Deliberately not routed through ``ensure_pending``: expiry is checked before a
        mutation is sent, never after. A plan whose TTL elapses while its request is in
        flight must still record what happened to it, or the operator is told "expired"
        about a write that already reached Bing.
        """
        plan = self.get(plan_id)
        if plan.applied_at or plan.rejected_at or plan.unknown_outcome_at:
            raise PlanAlreadyApplied(f"plan {plan_id} is already {plan.state}")
        updated = plan.model_copy(update={field: datetime.now(UTC)})
        self._write(updated)
        return updated

    def mark_applied(self, plan_id: str) -> Plan:
        return self._record_outcome(plan_id, "applied_at")

    def mark_unknown(self, plan_id: str) -> Plan:
        return self._record_outcome(plan_id, "unknown_outcome_at")

    def reject(self, plan_id: str) -> Plan:
        """Refuse a plan.

        Unlike the two apply outcomes this is a fresh decision, not the record of a
        request already sent, so it keeps the expiry check. It takes the same exclusive
        lock for the whole transition: testing for the lock and then writing would let
        an apply start in between and lose its own outcome.
        """
        with self._locked(plan_id, "wait for it to finish"):
            self.ensure_pending(plan_id)
            return self._record_outcome(plan_id, "rejected_at")

    def set_expiry(self, plan_id: str, when: datetime) -> None:
        self._write(self.get(plan_id).model_copy(update={"expires_at": when}))

    @contextmanager
    def _locked(self, plan_id: str, advice: str) -> Iterator[None]:
        path = self._path(plan_id).with_suffix(".lock")
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise PlanAlreadyApplied(
                f"plan {plan_id} is locked by an apply attempt; {advice}"
            ) from exc
        try:
            os.write(descriptor, f"pid={os.getpid()}\n".encode())
            os.close(descriptor)
            yield
        finally:
            if path.exists():
                path.unlink()

    @contextmanager
    def applying(self, plan_id: str) -> Iterator[Plan]:
        with self._locked(plan_id, "its outcome may be unknown"):
            yield self.ensure_pending(plan_id)


async def create_write_plan(
    operation: str,
    args: dict[str, Any],
    *,
    settings: Settings,
    client: BingClient | None,
) -> Plan:
    prepared = prepare_write(operation, args)
    if operation == "indexnow_submit":
        site_url = f"https://{prepared.body['host']}"
    else:
        site_url = normalise_site(str(args.get("site_url", "")))
    settings.check_site_allowed(site_url)

    if prepared.quota_method is not None:
        if client is None:
            raise RuntimeError("a Bing client is required for quota-aware plans")
        quota = await client.call(prepared.quota_method, {"siteUrl": site_url})
        if not isinstance(quota, dict) or not isinstance(quota.get("DailyQuota"), int):
            raise MalformedResponse(
                f"{prepared.quota_method}: DailyQuota is missing or not an integer"
            )
        remaining = quota["DailyQuota"]
        if prepared.cost > remaining:
            raise QuotaExceeded(
                f"{prepared.cost} submissions requested; Bing reports {remaining} left today",
                suggestion="reduce the plan or wait for Bing's quota to reset",
                details={"requested": prepared.cost, "daily_quota": remaining},
            )

    store = PlanStore(settings.state_dir, settings.plan_ttl_seconds)
    plan = store.create(operation, site_url, args, prepared.summary)
    AuditLog(settings.state_dir).record(
        "plan_created", plan_id=plan.plan_id, operation=operation, site=site_url
    )
    return plan
