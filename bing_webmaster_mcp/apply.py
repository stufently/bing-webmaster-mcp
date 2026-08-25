"""The only module that executes a mutating Bing API request."""

from __future__ import annotations

from typing import Any

from .audit import AuditLog
from .client import BingClient
from .errors import BingWebmasterError, PlanUnknownOutcome
from .limits import RateLimiter
from .plans import PlanStore
from .writes import prepare_write


async def apply_plan(
    plan_id: str,
    *,
    store: PlanStore,
    client: BingClient,
    audit: AuditLog,
    limiter: RateLimiter,
) -> dict[str, Any]:
    with store.applying(plan_id) as plan:
        prepared = prepare_write(plan.operation, plan.args)
        limiter.check(plan.site_url, prepared.cost)
        audit.record(
            "plan_apply_attempted",
            plan_id=plan_id,
            operation=plan.operation,
            site=plan.site_url,
        )
        try:
            result = await client.call(
                prepared.method,
                body=prepared.body,
                mutating=True,
            )
        except PlanUnknownOutcome as exc:
            store.mark_unknown(plan_id)
            audit.record("plan_apply_unknown", plan_id=plan_id, error=exc.to_dict())
            raise
        except BingWebmasterError as exc:
            audit.record("plan_apply_failed", plan_id=plan_id, error=exc.to_dict())
            raise

        limiter.consume(plan.site_url, prepared.cost)
        store.mark_applied(plan_id)
        audit.record("plan_apply_succeeded", plan_id=plan_id)
        return {
            "applied": True,
            "plan_id": plan_id,
            "operation": plan.operation,
            "result": result,
        }
