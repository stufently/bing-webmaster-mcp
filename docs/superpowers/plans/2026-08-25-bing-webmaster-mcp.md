# bing-webmaster-mcp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an MCP server and CLI over the Bing Webmaster Tools API where every read is direct and every write goes through a recorded plan a human applies.

**Architecture:** One `ops/` layer holds all behaviour; `cli.py` and `mcp_server.py` are thin fascias over it so they can never diverge. A single `client.py` owns the JSON transport and its two quirks (the `{"d": …}` envelope and ASP.NET tick dates). Mutating calls never execute inline — they produce a `Plan` record that only the CLI can apply.

**Tech Stack:** Python ≥3.12, httpx, pydantic + pydantic-settings, click, mcp (Python SDK), pytest + pytest-asyncio, ruff.

**Spec:** [`SPEC.md`](../../../SPEC.md) — read it first. This plan implements it; where the two disagree, the spec wins and the plan is wrong.

## Global Constraints

- `requires-python = ">=3.12"`. This is a **floor, not a pin**. CI matrix: 3.12, 3.13, 3.14.
- Dependency **floors** in `pyproject.toml`; exact versions only in `constraints.txt`.
- Base URL: `https://ssl.bing.com/webmaster/api.svc/json/{Method}`. No SOAP, no POX — both retire 2026-08-31.
- Auth v1: query parameter `apikey=<key>`. OAuth2 goes behind the same interface but is not implemented.
- Every success response is wrapped in `{"d": ...}`. Error responses are **not** wrapped: `{"ErrorCode": <int>, "Message": "<string>"}` with HTTP 400.
- Dates are ASP.NET ticks — `"\/Date(1316156400000-0700)\/"` — never ISO 8601.
- **Never hardcode a quota.** Read it from `GetUrlSubmissionQuota`.
- **No test may touch the network.** A `conftest.py` fixture enforces this process-wide.
- Error codes are a public JSON contract. Adding one is fine; renaming one is a breaking change.
- **No apply tool over MCP, ever.** A test asserts its absence; if that test fails the fix is to delete the tool.
- Package `bing_webmaster_mcp`, console script `bing-wm`, MIT licence.
- Ruff: `line-length = 100`, `target-version = "py312"`, `select = ["E","F","I","UP","B","SIM","S"]`, `tests/*` exempt from `S101`.
- Commit messages: short, imperative, no attribution trailers.

## File Structure

| File | Responsibility |
|---|---|
| `bing_webmaster_mcp/errors.py` | `ErrorCode` enum + exception hierarchy. Public wire contract. |
| `bing_webmaster_mcp/_serialize.py` | Envelope unwrapping and tick-date decoding. No HTTP. |
| `bing_webmaster_mcp/config.py` | `Settings` from env. No I/O beyond reading env. |
| `bing_webmaster_mcp/auth.py` | Credential application onto an outgoing request. |
| `bing_webmaster_mcp/client.py` | The only place that speaks HTTP to Bing. Throttle, retry, error mapping. |
| `bing_webmaster_mcp/render.py` | Sanitises attacker-influenced text; marks untrusted fields. |
| `bing_webmaster_mcp/ops/_common.py` | Site-URL normalisation and shared helpers for ops. |
| `bing_webmaster_mcp/ops/*.py` | One module per domain. All behaviour lives here. |
| `bing_webmaster_mcp/limits.py` | Rate limits that survive a restart. |
| `bing_webmaster_mcp/audit.py` | Append-only log of every attempted and completed write. |
| `bing_webmaster_mcp/plans.py` | Plan records: create, load, list, expire, mark applied. |
| `bing_webmaster_mcp/apply.py` | Executes an approved plan. The only writer. |
| `bing_webmaster_mcp/cli.py` | Click commands. Thin. |
| `bing_webmaster_mcp/mcp_server.py` | stdio MCP server. Thin. No apply tool. |
| `tests/fakes.py` | `httpx.MockTransport` builders and canned Bing payloads. |
| `tests/conftest.py` | Network guard, temp state dir, settings fixture. |

Tasks 1–8 build the spine; 9–11 add reads in bulk; 12–15 add the write boundary; 16–18 expose and ship it.

---

### Task 1: Project skeleton and local gates

**Files:**
- Create: `pyproject.toml`, `Makefile`, `bing_webmaster_mcp/__init__.py`, `tests/conftest.py`, `tests/test_package.py`

**Interfaces:**
- Consumes: nothing.
- Produces: importable package `bing_webmaster_mcp` with `__version__: str`; a `no_network` autouse fixture every later test relies on.

- [ ] **Step 1: Write the failing test**

`tests/test_package.py`:

```python
import bing_webmaster_mcp


def test_version_is_exposed():
    assert isinstance(bing_webmaster_mcp.__version__, str)
    assert bing_webmaster_mcp.__version__.count(".") >= 2


def test_network_is_blocked_in_tests():
    import socket

    with pytest.raises(RuntimeError, match="network access"):
        socket.socket().connect(("example.com", 80))


import pytest  # noqa: E402
```

`tests/conftest.py`:

```python
import socket

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail loudly instead of silently reaching the internet from a unit test."""

    def guard(*args, **kwargs):
        raise RuntimeError("network access is not allowed in tests")

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket.socket, "connect_ex", guard)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_package.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bing_webmaster_mcp'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/__init__.py`:

```python
"""MCP server and CLI over the Bing Webmaster Tools API."""

__version__ = "0.1.0"
```

`pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "bing-webmaster-mcp"
version = "0.1.0"
description = "MCP server and CLI for Bing Webmaster Tools, with a review step on every write"
readme = "README.md"
license = "MIT"
requires-python = ">=3.12"
# Floors, not pins. A published package that pins exact versions breaks every
# environment that already has a working newer one. Exact versions are frozen in
# constraints.txt, which is what CI and the Docker image install.
dependencies = [
    "httpx>=0.28,<1",
    "pydantic>=2.11,<3",
    "pydantic-settings>=2.6,<3",
    "click>=8.2,<9",
    "mcp>=2.1,<3",
]
classifiers = [
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
]

[project.optional-dependencies]
test = ["pytest>=8", "pytest-asyncio>=0.24", "ruff>=0.9"]

[project.scripts]
bing-wm = "bing_webmaster_mcp.cli:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["tests"]
filterwarnings = ["error::DeprecationWarning:bing_webmaster_mcp.*"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "S"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]
```

`Makefile`:

```make
.PHONY: lint test
lint:
	ruff check .
	ruff format --check .

test:
	pytest -q
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pip install -e ".[test]"` then `pytest -v` and `make lint`
Expected: 2 passed, lint clean

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml Makefile bing_webmaster_mcp tests
git commit -m "Add package skeleton and test gates"
```

---

### Task 2: Reconcile the API method surface

This is SPEC.md §4's Task 0. It produces a document, not code, but every later task
generates code from it — so it is verified by a test that counts it.

**Files:**
- Create: `docs/api-surface.md`, `tests/test_api_surface.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `docs/api-surface.md` containing one markdown table row per API method, columns `Method | Params | R/W | Group`. Later tasks copy method names from here verbatim.

- [ ] **Step 1: Write the failing test**

`tests/test_api_surface.py`:

```python
import re
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "docs" / "api-surface.md"
ROW = re.compile(r"^\|\s*`(?P<method>\w+)`\s*\|.*\|\s*(?P<rw>[RW])\s*\|\s*(?P<group>[\w /-]+?)\s*\|$")


def parse_rows():
    return [m.groupdict() for line in DOC.read_text().splitlines() if (m := ROW.match(line))]


def test_every_method_name_is_unique():
    methods = [row["method"] for row in parse_rows()]
    duplicates = {m for m in methods if methods.count(m) > 1}
    assert not duplicates, f"duplicated rows: {sorted(duplicates)}"


def test_count_matches_declared_total():
    text = DOC.read_text()
    declared = int(re.search(r"<!-- method-count: (\d+) -->", text).group(1))
    assert len(parse_rows()) == declared


def test_known_anchor_methods_are_present():
    methods = {row["method"] for row in parse_rows()}
    for anchor in ("GetUserSites", "AddSite", "SubmitUrlBatch", "GetUrlSubmissionQuota"):
        assert anchor in methods


def test_fetchurl_is_classified_as_a_write():
    rows = {row["method"]: row["rw"] for row in parse_rows()}
    assert rows["FetchUrl"] == "W", "FetchUrl consumes quota; it is a write despite the name"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_surface.py -v`
Expected: FAIL — `docs/api-surface.md` does not exist

- [ ] **Step 3: Build the document from the primary source**

Fetch <https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi?view=bing-webmaster-dotnet>
and transcribe every method into `docs/api-surface.md`. Start from the grouped table
in `SPEC.md` §4 and correct it against the page — the spec flags a 57-vs-62 count
conflict that this task exists to settle. Do not add a method the page does not list,
and do not drop one because the spec omitted it.

Header the file with the resolved count so the test can check it:

```markdown
# Bing Webmaster Tools API surface

Transcribed from the `IWebmasterApi` interface reference, fetched 2026-08-25.
R/W is derived from the verb and is not labelled by Microsoft.

<!-- method-count: 62 -->

| Method | Params | R/W | Group |
|---|---|---|---|
| `GetUserSites` | — | R | Sites |
| `AddSite` | siteUrl | W | Sites |
| `FetchUrl` | siteUrl, url | W | Crawl |
```

Set `method-count` to the number you actually counted, and record in the file's prose
which number the page gave and how the conflict resolved.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api_surface.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add docs/api-surface.md tests/test_api_surface.py
git commit -m "Transcribe and verify the API method surface"
```

---

### Task 3: Error taxonomy

**Files:**
- Create: `bing_webmaster_mcp/errors.py`, `tests/test_errors.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `ErrorCode(StrEnum)` with members `INVALID_REQUEST`, `AUTH_FAILED`, `SITE_NOT_VERIFIED`, `QUOTA_EXCEEDED`, `RATE_LIMITED`, `UPSTREAM_UNAVAILABLE`, `MALFORMED_RESPONSE`, `PLAN_NOT_FOUND`, `PLAN_EXPIRED`, `PLAN_ALREADY_APPLIED`, `PLAN_UNKNOWN_OUTCOME`, `POLICY_DENIED`, `INTERNAL`
  - `BingWebmasterError(message, *, suggestion=None, retry_after=None, details=None)` with class attributes `code: ErrorCode` and `retryable: bool`, and `.to_dict() -> dict`
  - Subclasses: `InvalidRequest`, `AuthFailed`, `SiteNotVerified`, `QuotaExceeded`, `RateLimited`, `UpstreamUnavailable`, `MalformedResponse`, `PlanNotFound`, `PlanExpired`, `PlanAlreadyApplied`, `PlanUnknownOutcome`, `PolicyDenied`, `InternalError`

- [ ] **Step 1: Write the failing test**

`tests/test_errors.py`:

```python
import pytest

from bing_webmaster_mcp.errors import (
    BingWebmasterError,
    ErrorCode,
    PlanUnknownOutcome,
    QuotaExceeded,
    RateLimited,
)


def test_to_dict_is_the_wire_contract():
    err = RateLimited("slow down", retry_after=30)
    assert err.to_dict() == {
        "code": "RATE_LIMITED",
        "message": "slow down",
        "retryable": True,
        "retry_after": 30,
    }


def test_optional_fields_are_omitted_when_absent():
    assert set(QuotaExceeded("no quota left").to_dict()) == {"code", "message", "retryable"}


def test_suggestion_and_details_round_trip():
    err = QuotaExceeded("no quota left", suggestion="wait for reset", details={"daily": 0})
    payload = err.to_dict()
    assert payload["suggestion"] == "wait for reset"
    assert payload["details"] == {"daily": 0}


def test_quota_exceeded_is_not_retryable():
    # Retrying does not create quota. Only the reset does.
    assert QuotaExceeded("x").retryable is False


def test_unknown_outcome_is_not_retryable():
    # An automatic retry here is how one submission becomes two.
    assert PlanUnknownOutcome("x").retryable is False


def test_every_error_code_has_a_class():
    subclasses = {cls.code for cls in _all_subclasses(BingWebmasterError)}
    assert subclasses == set(ErrorCode)


def _all_subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from _all_subclasses(sub)


def test_raising_is_catchable_by_the_base():
    with pytest.raises(BingWebmasterError):
        raise RateLimited("x", retry_after=1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_errors.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bing_webmaster_mcp.errors'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/errors.py`:

```python
"""Error taxonomy. The `code` strings are a public JSON contract: adding one is
fine, renaming one is a breaking change for every client that branches on it."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    # Caller mistakes
    INVALID_REQUEST = "INVALID_REQUEST"
    # Credentials and ownership
    AUTH_FAILED = "AUTH_FAILED"
    SITE_NOT_VERIFIED = "SITE_NOT_VERIFIED"
    # Budget
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    RATE_LIMITED = "RATE_LIMITED"
    # Upstream
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    # Plans
    PLAN_NOT_FOUND = "PLAN_NOT_FOUND"
    PLAN_EXPIRED = "PLAN_EXPIRED"
    PLAN_ALREADY_APPLIED = "PLAN_ALREADY_APPLIED"
    PLAN_UNKNOWN_OUTCOME = "PLAN_UNKNOWN_OUTCOME"
    # Policy
    POLICY_DENIED = "POLICY_DENIED"
    # Catch-all
    INTERNAL = "INTERNAL"


class BingWebmasterError(Exception):
    code: ErrorCode = ErrorCode.INTERNAL
    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        suggestion: str | None = None,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion
        self.retry_after = retry_after
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": str(self.code),
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.suggestion is not None:
            payload["suggestion"] = self.suggestion
        if self.retry_after is not None:
            payload["retry_after"] = self.retry_after
        if self.details is not None:
            payload["details"] = self.details
        return payload


class InvalidRequest(BingWebmasterError):
    """Bing rejected the arguments. Sending them again unchanged will fail again."""

    code = ErrorCode.INVALID_REQUEST


class AuthFailed(BingWebmasterError):
    """Missing, wrong or revoked API key. Not retryable without new credentials."""

    code = ErrorCode.AUTH_FAILED


class SiteNotVerified(BingWebmasterError):
    """The account does not own this site in Bing Webmaster Tools."""

    code = ErrorCode.SITE_NOT_VERIFIED


class QuotaExceeded(BingWebmasterError):
    """Submission quota is exhausted. Retrying does not create quota; only the reset does."""

    code = ErrorCode.QUOTA_EXCEEDED


class RateLimited(BingWebmasterError):
    """Too many calls. Retrying after `retry_after` seconds is the correct response."""

    code = ErrorCode.RATE_LIMITED
    retryable = True


class UpstreamUnavailable(BingWebmasterError):
    """Bing returned 5xx or the connection failed. Transient by assumption."""

    code = ErrorCode.UPSTREAM_UNAVAILABLE
    retryable = True


class MalformedResponse(BingWebmasterError):
    """The response did not match the documented shape. Retrying will not fix a parser."""

    code = ErrorCode.MALFORMED_RESPONSE


class PlanNotFound(BingWebmasterError):
    code = ErrorCode.PLAN_NOT_FOUND


class PlanExpired(BingWebmasterError):
    """The plan aged out. Re-plan so a human reviews current arguments, not stale ones."""

    code = ErrorCode.PLAN_EXPIRED


class PlanAlreadyApplied(BingWebmasterError):
    code = ErrorCode.PLAN_ALREADY_APPLIED


class PlanUnknownOutcome(BingWebmasterError):
    """The request left but the response was lost. Deliberately not retryable: an
    automatic retry here is how one submission becomes two."""

    code = ErrorCode.PLAN_UNKNOWN_OUTCOME


class PolicyDenied(BingWebmasterError):
    """Local configuration forbids this operation on this site."""

    code = ErrorCode.POLICY_DENIED


class InternalError(BingWebmasterError):
    code = ErrorCode.INTERNAL
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_errors.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/errors.py tests/test_errors.py
git commit -m "Add error taxonomy"
```

---

### Task 4: Envelope and tick-date decoding

The two traps from `SPEC.md` §3. They get their own task because a test written from
the same wrong assumption as the code will pass while production fails.

**Files:**
- Create: `bing_webmaster_mcp/_serialize.py`, `tests/test_serialize.py`

**Interfaces:**
- Consumes: `bing_webmaster_mcp.errors.MalformedResponse`
- Produces:
  - `unwrap(payload: Any) -> Any` — returns `payload["d"]`, raises `MalformedResponse` if absent
  - `parse_bing_datetime(value: str) -> datetime` — decodes `/Date(ticks±hhmm)/`, always tz-aware
  - `decode(value: Any) -> Any` — walks dicts/lists, replacing tick strings with `datetime` and dropping `__type` keys

- [ ] **Step 1: Write the failing test**

`tests/test_serialize.py`:

```python
from datetime import UTC, datetime, timedelta, timezone

import pytest

from bing_webmaster_mcp._serialize import decode, parse_bing_datetime, unwrap
from bing_webmaster_mcp.errors import MalformedResponse


def test_unwrap_returns_the_d_payload():
    assert unwrap({"d": [1, 2]}) == [1, 2]


def test_unwrap_rejects_a_body_without_d():
    with pytest.raises(MalformedResponse):
        unwrap({"ErrorCode": 400, "Message": "nope"})


def test_ticks_with_negative_offset():
    parsed = parse_bing_datetime("/Date(1316156400000-0700)/")
    assert parsed.utcoffset() == timedelta(hours=-7)
    assert parsed.timestamp() == 1316156400.0


def test_ticks_with_positive_offset():
    parsed = parse_bing_datetime("/Date(1316156400000+0530)/")
    assert parsed.utcoffset() == timedelta(hours=5, minutes=30)
    assert parsed.timestamp() == 1316156400.0


def test_ticks_without_offset_are_utc():
    parsed = parse_bing_datetime("/Date(1316156400000)/")
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)


def test_escaped_slashes_are_accepted():
    assert parse_bing_datetime("\\/Date(0)\\/") == datetime(1970, 1, 1, tzinfo=UTC)


def test_malformed_date_raises_rather_than_returning_none():
    with pytest.raises(MalformedResponse):
        parse_bing_datetime("2011-09-16T00:00:00Z")


def test_decode_walks_nested_structures_and_drops_type_markers():
    raw = {
        "__type": "Site:#Microsoft.Bing.Webmaster.Api",
        "Url": "https://example.com",
        "Added": "/Date(0)/",
        "Children": [{"__type": "X", "Seen": "/Date(0)/"}],
    }
    assert decode(raw) == {
        "Url": "https://example.com",
        "Added": datetime(1970, 1, 1, tzinfo=UTC),
        "Children": [{"Seen": datetime(1970, 1, 1, tzinfo=UTC)}],
    }


def test_decode_leaves_ordinary_strings_alone():
    assert decode({"Query": "/Date is a weird format/"}) == {"Query": "/Date is a weird format/"}


def test_timezone_object_is_a_real_offset():
    parsed = parse_bing_datetime("/Date(0+0100)/")
    assert parsed.tzinfo == timezone(timedelta(hours=1))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_serialize.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bing_webmaster_mcp._serialize'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/_serialize.py`:

```python
"""Decoding for Bing's JSON endpoint.

Two documented quirks live here and nowhere else:
  * every success body is wrapped in {"d": ...}; error bodies are not;
  * datetimes are ASP.NET ticks -- "/Date(1316156400000-0700)/" -- not ISO 8601.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from .errors import MalformedResponse

_TICKS = re.compile(r"^\\?/Date\((?P<ms>-?\d+)(?P<sign>[+-])?(?P<hh>\d{2})?(?P<mm>\d{2})?\)\\?/$")


def unwrap(payload: Any) -> Any:
    if not isinstance(payload, dict) or "d" not in payload:
        raise MalformedResponse(
            "response body has no 'd' envelope",
            suggestion="a body without 'd' is normally an error body; check the status code",
            details={"keys": sorted(payload) if isinstance(payload, dict) else None},
        )
    return payload["d"]


def parse_bing_datetime(value: str) -> datetime:
    match = _TICKS.match(value)
    if match is None:
        raise MalformedResponse(
            f"not an ASP.NET tick date: {value!r}",
            suggestion="Bing's JSON endpoint never returns ISO 8601; do not fall back to it",
        )
    moment = datetime.fromtimestamp(int(match["ms"]) / 1000, tz=UTC)
    if match["sign"] is None:
        return moment
    offset = timedelta(hours=int(match["hh"]), minutes=int(match["mm"]))
    if match["sign"] == "-":
        offset = -offset
    return moment.astimezone(timezone(offset))


def decode(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: decode(v) for k, v in value.items() if k != "__type"}
    if isinstance(value, list):
        return [decode(v) for v in value]
    if isinstance(value, str) and _TICKS.match(value):
        return parse_bing_datetime(value)
    return value
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_serialize.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/_serialize.py tests/test_serialize.py
git commit -m "Decode the d envelope and tick dates"
```

---

### Task 5: Settings and credentials

**Files:**
- Create: `bing_webmaster_mcp/config.py`, `bing_webmaster_mcp/auth.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `errors.AuthFailed`, `errors.PolicyDenied`
- Produces:
  - `Settings` (pydantic-settings, env prefix `BING_WM_`) with fields `api_key: SecretStr`, `base_url: str = "https://ssl.bing.com/webmaster/api.svc/json"`, `calls_per_second: float = 5.0`, `plan_ttl_seconds: int = 900`, `state_dir: Path`, `denied_sites: tuple[str, ...] = ()`
  - `Settings.load() -> Settings`
  - `Settings.check_site_allowed(site_url: str) -> None` raising `PolicyDenied`
  - `ApiKeyAuth(api_key: str)` with `apply(params: dict[str, str], headers: dict[str, str]) -> None`
  - `build_auth(settings: Settings) -> ApiKeyAuth`

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:

```python
import pytest

from bing_webmaster_mcp.auth import ApiKeyAuth, build_auth
from bing_webmaster_mcp.config import Settings
from bing_webmaster_mcp.errors import AuthFailed, PolicyDenied


def test_settings_read_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("BING_WM_API_KEY", "secret-key")
    monkeypatch.setenv("BING_WM_STATE_DIR", str(tmp_path))
    settings = Settings.load()
    assert settings.api_key.get_secret_value() == "secret-key"
    assert settings.base_url == "https://ssl.bing.com/webmaster/api.svc/json"
    assert settings.calls_per_second == 5.0
    assert settings.plan_ttl_seconds == 900


def test_missing_key_is_an_auth_error(monkeypatch, tmp_path):
    monkeypatch.delenv("BING_WM_API_KEY", raising=False)
    monkeypatch.setenv("BING_WM_STATE_DIR", str(tmp_path))
    with pytest.raises(AuthFailed):
        Settings.load()


def test_repr_does_not_leak_the_key(monkeypatch, tmp_path):
    monkeypatch.setenv("BING_WM_API_KEY", "secret-key")
    monkeypatch.setenv("BING_WM_STATE_DIR", str(tmp_path))
    assert "secret-key" not in repr(Settings.load())


def test_denied_sites_are_refused(monkeypatch, tmp_path):
    monkeypatch.setenv("BING_WM_API_KEY", "k")
    monkeypatch.setenv("BING_WM_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("BING_WM_DENIED_SITES", '["https://locked.example"]')
    settings = Settings.load()
    with pytest.raises(PolicyDenied):
        settings.check_site_allowed("https://locked.example")
    settings.check_site_allowed("https://open.example")


def test_denial_ignores_case_and_trailing_slash(monkeypatch, tmp_path):
    monkeypatch.setenv("BING_WM_API_KEY", "k")
    monkeypatch.setenv("BING_WM_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("BING_WM_DENIED_SITES", '["https://Locked.example/"]')
    with pytest.raises(PolicyDenied):
        Settings.load().check_site_allowed("https://locked.example")


def test_apikey_auth_goes_in_the_query_string():
    params: dict[str, str] = {}
    headers: dict[str, str] = {}
    ApiKeyAuth("abc").apply(params, headers)
    assert params == {"apikey": "abc"}
    assert headers == {}


def test_build_auth_returns_apikey_auth(monkeypatch, tmp_path):
    monkeypatch.setenv("BING_WM_API_KEY", "abc")
    monkeypatch.setenv("BING_WM_STATE_DIR", str(tmp_path))
    assert isinstance(build_auth(Settings.load()), ApiKeyAuth)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bing_webmaster_mcp.config'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/config.py`:

```python
"""Settings, read from the environment. The API key never appears in a repr."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import AuthFailed, PolicyDenied


def _default_state_dir() -> Path:
    return Path.home() / ".local" / "state" / "bing-webmaster-mcp"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BING_WM_", extra="ignore")

    api_key: SecretStr
    base_url: str = "https://ssl.bing.com/webmaster/api.svc/json"
    calls_per_second: float = Field(default=5.0, gt=0)
    plan_ttl_seconds: int = Field(default=900, gt=0)
    state_dir: Path = Field(default_factory=_default_state_dir)
    denied_sites: tuple[str, ...] = ()

    @classmethod
    def load(cls) -> Settings:
        try:
            return cls()
        except ValidationError as exc:
            raise AuthFailed(
                "BING_WM_API_KEY is not set",
                suggestion="create a key in Bing Webmaster Tools -> Settings -> API Access",
                details={"fields": [str(e["loc"][0]) for e in exc.errors()]},
            ) from exc

    def check_site_allowed(self, site_url: str) -> None:
        if _normalise(site_url) in {_normalise(s) for s in self.denied_sites}:
            raise PolicyDenied(
                f"{site_url} is in BING_WM_DENIED_SITES",
                suggestion="remove it from the denylist if this was intended",
            )


def _normalise(site_url: str) -> str:
    return site_url.strip().rstrip("/").lower()
```

`bing_webmaster_mcp/auth.py`:

```python
"""Credential application.

Only the api-key mode is implemented. OAuth2 (authorization-code flow, scopes
Webmaster.read / Webmaster.manage) would be a second class with the same `apply`
signature -- see SPEC.md section 3. It is deliberately not built yet.
"""

from __future__ import annotations

from .config import Settings


class ApiKeyAuth:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def apply(self, params: dict[str, str], headers: dict[str, str]) -> None:
        params["apikey"] = self._api_key


def build_auth(settings: Settings) -> ApiKeyAuth:
    return ApiKeyAuth(settings.api_key.get_secret_value())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/config.py bing_webmaster_mcp/auth.py tests/test_config.py
git commit -m "Add settings and api-key auth"
```

---

### Task 6: The HTTP client

The only module that speaks to Bing. Everything above it sees decoded data or a
typed error.

**Files:**
- Create: `bing_webmaster_mcp/client.py`, `tests/fakes.py`, `tests/test_client.py`

**Interfaces:**
- Consumes: `Settings`, `ApiKeyAuth`, `_serialize.unwrap`, `_serialize.decode`, the error classes
- Produces:
  - `BingClient(settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None)`
  - `async BingClient.call(method: str, params: dict[str, Any] | None = None, *, body: dict[str, Any] | None = None) -> Any` — GET when `body` is None, POST otherwise; returns decoded, unwrapped data
  - `async BingClient.aclose() -> None`; usable as an async context manager
- Test helper produced here and used by every later ops test:
  - `tests/fakes.py`: `bing_transport(routes: dict[str, Any], *, status: int = 200) -> httpx.MockTransport`, `error_transport(status: int, body: dict[str, Any]) -> httpx.MockTransport`, `fake_settings(tmp_path, **overrides) -> Settings`

- [ ] **Step 1: Write the failing test**

`tests/fakes.py`:

```python
"""Canned Bing responses over httpx.MockTransport. No socket is ever opened."""

from __future__ import annotations

import json
from typing import Any

import httpx

from bing_webmaster_mcp.config import Settings


def fake_settings(tmp_path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "api_key": "test-key",
        "state_dir": tmp_path,
        "calls_per_second": 1000.0,
    }
    values.update(overrides)
    return Settings(**values)


def bing_transport(routes: dict[str, Any], *, status: int = 200) -> httpx.MockTransport:
    """`routes` maps a method name to the value that belongs inside {"d": ...}."""

    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        method = request.url.path.rsplit("/", 1)[-1]
        if method not in routes:
            return httpx.Response(400, json={"ErrorCode": 400, "Message": f"no route {method}"})
        return httpx.Response(status, json={"d": routes[method]})

    transport = httpx.MockTransport(handler)
    transport.calls = calls  # type: ignore[attr-defined]
    return transport


def error_transport(status: int, body: dict[str, Any]) -> httpx.MockTransport:
    return httpx.MockTransport(lambda request: httpx.Response(status, content=json.dumps(body)))
```

`tests/test_client.py`:

```python
from datetime import UTC, datetime

import httpx
import pytest
from fakes import bing_transport, error_transport, fake_settings

from bing_webmaster_mcp.client import BingClient
from bing_webmaster_mcp.errors import (
    AuthFailed,
    InvalidRequest,
    MalformedResponse,
    RateLimited,
    UpstreamUnavailable,
)


async def test_get_unwraps_and_decodes(tmp_path):
    transport = bing_transport({"GetUserSites": [{"Url": "https://a.example", "D": "/Date(0)/"}]})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        result = await client.call("GetUserSites")
    assert result == [{"Url": "https://a.example", "D": datetime(1970, 1, 1, tzinfo=UTC)}]


async def test_api_key_is_sent_as_a_query_parameter(tmp_path):
    transport = bing_transport({"GetUserSites": []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await client.call("GetUserSites")
    assert transport.calls[0].url.params["apikey"] == "test-key"


async def test_params_are_appended_to_the_query_string(tmp_path):
    transport = bing_transport({"GetUrlInfo": {}})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await client.call("GetUrlInfo", {"siteUrl": "https://a.example", "url": "https://a/x"})
    assert transport.calls[0].url.params["siteUrl"] == "https://a.example"
    assert transport.calls[0].method == "GET"


async def test_a_body_makes_it_a_post(tmp_path):
    transport = bing_transport({"SubmitUrlBatch": None})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await client.call("SubmitUrlBatch", body={"siteUrl": "https://a.example", "urlList": []})
    assert transport.calls[0].method == "POST"


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (400, {"ErrorCode": 1, "Message": "bad"}, InvalidRequest),
        (401, {"ErrorCode": 2, "Message": "nope"}, AuthFailed),
        (403, {"ErrorCode": 3, "Message": "nope"}, AuthFailed),
        (429, {"ErrorCode": 4, "Message": "slow"}, RateLimited),
        (500, {"ErrorCode": 5, "Message": "boom"}, UpstreamUnavailable),
    ],
)
async def test_status_codes_map_to_the_taxonomy(tmp_path, status, body, expected):
    settings = fake_settings(tmp_path)
    async with BingClient(settings, transport=error_transport(status, body)) as client:
        with pytest.raises(expected):
            await client.call("GetUserSites")


async def test_bing_message_survives_into_the_error(tmp_path):
    transport = error_transport(400, {"ErrorCode": 7, "Message": "site not verified"})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        with pytest.raises(InvalidRequest) as excinfo:
            await client.call("GetUserSites")
    assert "site not verified" in excinfo.value.message
    assert excinfo.value.details == {"ErrorCode": 7}


async def test_retry_after_header_is_carried(tmp_path):
    def handler(request):
        return httpx.Response(429, json={"ErrorCode": 4, "Message": "slow"}, headers={"Retry-After": "42"})

    async with BingClient(fake_settings(tmp_path), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RateLimited) as excinfo:
            await client.call("GetUserSites")
    assert excinfo.value.retry_after == 42


async def test_success_body_without_d_is_malformed(tmp_path):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"oops": 1}))
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        with pytest.raises(MalformedResponse):
            await client.call("GetUserSites")


async def test_non_json_success_body_is_malformed(tmp_path):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"<html>"))
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        with pytest.raises(MalformedResponse):
            await client.call("GetUserSites")


async def test_connection_failure_is_upstream_unavailable(tmp_path):
    def handler(request):
        raise httpx.ConnectError("refused")

    async with BingClient(fake_settings(tmp_path), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(UpstreamUnavailable):
            await client.call("GetUserSites")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bing_webmaster_mcp.client'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/client.py`:

```python
"""The only module that speaks HTTP to Bing.

Callers above this layer see decoded Python values or a BingWebmasterError --
never an httpx object, never a raw status code.
"""

from __future__ import annotations

import asyncio
import time
from types import TracebackType
from typing import Any

import httpx

from ._serialize import decode, unwrap
from .auth import build_auth
from .config import Settings
from .errors import (
    AuthFailed,
    InvalidRequest,
    MalformedResponse,
    RateLimited,
    UpstreamUnavailable,
)


class _Throttle:
    """Bing publishes no QPS limit. This is our own politeness bound, not theirs."""

    def __init__(self, calls_per_second: float) -> None:
        self._interval = 1.0 / calls_per_second
        self._next = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if now < self._next:
                await asyncio.sleep(self._next - now)
            self._next = max(now, self._next) + self._interval


class BingClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._auth = build_auth(settings)
        self._throttle = _Throttle(settings.calls_per_second)
        self._http = httpx.AsyncClient(transport=transport, timeout=30.0)

    async def __aenter__(self) -> BingClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        body: dict[str, Any] | None = None,
    ) -> Any:
        query: dict[str, Any] = dict(params or {})
        headers: dict[str, str] = {}
        self._auth.apply(query, headers)
        url = f"{self._settings.base_url.rstrip('/')}/{method}"

        await self._throttle.wait()
        try:
            if body is None:
                response = await self._http.get(url, params=query, headers=headers)
            else:
                response = await self._http.post(url, params=query, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise UpstreamUnavailable(f"{method}: {exc}") from exc

        if response.status_code >= 400:
            raise _map_error(method, response)
        try:
            payload = response.json()
        except ValueError as exc:
            raise MalformedResponse(f"{method}: response was not JSON") from exc
        return decode(unwrap(payload))


def _map_error(method: str, response: httpx.Response) -> Exception:
    try:
        body = response.json()
    except ValueError:
        body = {}
    message = body.get("Message") or response.reason_phrase or "request failed"
    details = {"ErrorCode": body["ErrorCode"]} if "ErrorCode" in body else None
    text = f"{method}: {message}"

    if response.status_code in (401, 403):
        return AuthFailed(
            text,
            suggestion="check BING_WM_API_KEY and that the account owns this site",
            details=details,
        )
    if response.status_code == 429:
        raw = response.headers.get("Retry-After")
        return RateLimited(text, retry_after=int(raw) if raw and raw.isdigit() else None, details=details)
    if response.status_code >= 500:
        return UpstreamUnavailable(text, details=details)
    return InvalidRequest(text, details=details)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_client.py -v`
Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/client.py tests/fakes.py tests/test_client.py
git commit -m "Add the Bing JSON transport"
```

---

### Task 7: Sanitising attacker-influenced text

Anchor text, crawl-issue URLs and search queries are written by strangers: anyone
can link to a site with any anchor text, and any bot can put anything in a URL that
lands in a crawl report. That text flows through this tool into a model's context
and onto a terminal. It is data, never instructions.

**Files:**
- Create: `bing_webmaster_mcp/render.py`, `tests/test_render.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `UNTRUSTED_FIELDS: frozenset[str]` — exact field names, currently `{"AnchorText", "Query", "Url", "Title", "Message", "Description"}`
  - `sanitize_text(value: str) -> str` — strips C0/C1 control characters except `\n` and `\t`, and truncates at 2000 characters with a marker
  - `sanitize(value: Any) -> Any` — walks structures, sanitising strings under untrusted keys and wrapping them as `{"value": ..., "untrusted": True}`

- [ ] **Step 1: Write the failing test**

`tests/test_render.py`:

```python
from bing_webmaster_mcp.render import UNTRUSTED_FIELDS, sanitize, sanitize_text


def test_control_characters_are_removed():
    assert sanitize_text("a\x1b[31mb\x07c") == "a[31mbc"


def test_newlines_and_tabs_survive():
    assert sanitize_text("a\nb\tc") == "a\nb\tc"


def test_long_text_is_truncated_with_a_marker():
    out = sanitize_text("x" * 5000)
    assert len(out) == 2000 + len("… [truncated]")
    assert out.endswith("… [truncated]")


def test_untrusted_fields_are_marked():
    assert sanitize({"AnchorText": "click here"}) == {
        "AnchorText": {"value": "click here", "untrusted": True}
    }


def test_trusted_fields_pass_through_unwrapped():
    assert sanitize({"Clicks": 5, "Impressions": 10}) == {"Clicks": 5, "Impressions": 10}


def test_nested_structures_are_walked():
    raw = {"Links": [{"AnchorText": "a\x00b", "Clicks": 1}]}
    assert sanitize(raw) == {
        "Links": [{"AnchorText": {"value": "ab", "untrusted": True}, "Clicks": 1}]
    }


def test_marking_keys_on_exact_names_only():
    # A prefixed variant must not be assumed safe: if a new field appears it has to
    # be added to the set deliberately, and this test documents the sharp edge.
    assert "AnchorTextRaw" not in UNTRUSTED_FIELDS
    assert sanitize({"AnchorTextRaw": "x"}) == {"AnchorTextRaw": "x"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bing_webmaster_mcp.render'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/render.py`:

```python
"""Sanitising for text this program did not write.

Inbound-link anchor text, crawl-issue URLs and query strings are controlled by
whoever linked to the site or crawled it. Treat them as data. Marking them
`untrusted` in the payload is what lets a model downstream tell the difference.
"""

from __future__ import annotations

from typing import Any

UNTRUSTED_FIELDS = frozenset(
    {"AnchorText", "Query", "Url", "Title", "Message", "Description"}
)

_MAX = 2000
_KEEP = {"\n", "\t"}


def sanitize_text(value: str) -> str:
    cleaned = "".join(
        ch for ch in value if ch in _KEEP or (ch.isprintable() and not _is_control(ch))
    )
    if len(cleaned) > _MAX:
        return cleaned[:_MAX] + "… [truncated]"
    return cleaned


def _is_control(ch: str) -> bool:
    point = ord(ch)
    return point < 0x20 or 0x7F <= point <= 0x9F


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key in UNTRUSTED_FIELDS and isinstance(item, str):
                out[key] = {"value": sanitize_text(item), "untrusted": True}
            else:
                out[key] = sanitize(item)
        return out
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_render.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/render.py tests/test_render.py
git commit -m "Mark and sanitise untrusted text"
```

---

### Task 8: First vertical slice — `bing-wm sites list`

Proves the whole spine works end to end before reads are added in bulk.

**Files:**
- Create: `bing_webmaster_mcp/ops/__init__.py`, `bing_webmaster_mcp/ops/_common.py`, `bing_webmaster_mcp/ops/sites.py`, `bing_webmaster_mcp/cli.py`, `tests/test_ops_sites.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `BingClient.call`, `Settings`, `render.sanitize`
- Produces:
  - `ops/_common.py`: `normalise_site(site_url: str) -> str` (adds `https://` when missing, strips a trailing slash), `async fetch(client, method, params=None, *, body=None) -> Any` (calls then sanitises)
  - `ops/sites.py`: `async list_sites(client) -> list[dict]`, `async site_roles(client, site_url) -> list[dict]`, `async site_moves(client, site_url) -> list[dict]`
  - `cli.py`: `main()` Click group, `sites` subgroup with `list` and `roles`, a `--json` flag, and `run_async(coro)` + `open_client(settings)` helpers every later CLI task reuses

- [ ] **Step 1: Write the failing test**

`tests/test_ops_sites.py`:

```python
import pytest
from fakes import bing_transport, fake_settings

from bing_webmaster_mcp.client import BingClient
from bing_webmaster_mcp.ops._common import normalise_site
from bing_webmaster_mcp.ops.sites import list_sites, site_roles


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("example.com", "https://example.com"),
        ("https://example.com/", "https://example.com"),
        ("http://example.com", "http://example.com"),
        ("  https://example.com  ", "https://example.com"),
    ],
)
def test_site_normalisation(raw, expected):
    assert normalise_site(raw) == expected


async def test_list_sites_returns_rows(tmp_path):
    transport = bing_transport({"GetUserSites": [{"Url": "https://a.example", "IsVerified": True}]})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        assert await list_sites(client) == [
            {"Url": {"value": "https://a.example", "untrusted": True}, "IsVerified": True}
        ]


async def test_site_roles_normalises_the_site_argument(tmp_path):
    transport = bing_transport({"GetSiteRoles": []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await site_roles(client, "a.example/")
    assert transport.calls[0].url.params["siteUrl"] == "https://a.example"
```

`tests/test_cli.py`:

```python
import json

from click.testing import CliRunner
from fakes import bing_transport, fake_settings

from bing_webmaster_mcp import cli


def test_sites_list_prints_json(tmp_path, monkeypatch):
    transport = bing_transport({"GetUserSites": [{"Url": "https://a.example"}]})
    monkeypatch.setattr(cli, "_load_settings", lambda: fake_settings(tmp_path))
    monkeypatch.setattr(cli, "_transport", lambda: transport)

    result = CliRunner().invoke(cli.main, ["sites", "list", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == [{"Url": {"value": "https://a.example", "untrusted": True}}]


def test_errors_exit_nonzero_with_the_code(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_load_settings", lambda: fake_settings(tmp_path))
    monkeypatch.setattr(cli, "_transport", lambda: bing_transport({}))

    result = CliRunner().invoke(cli.main, ["sites", "list", "--json"])

    assert result.exit_code == 1
    assert "INVALID_REQUEST" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ops_sites.py tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bing_webmaster_mcp.ops'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/ops/__init__.py`: empty file.

`bing_webmaster_mcp/ops/_common.py`:

```python
"""Helpers shared by every ops module. No HTTP details leak above this line."""

from __future__ import annotations

from typing import Any

from ..client import BingClient
from ..render import sanitize


def normalise_site(site_url: str) -> str:
    site = site_url.strip().rstrip("/")
    if not site.startswith(("http://", "https://")):
        site = f"https://{site}"
    return site


async def fetch(
    client: BingClient,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    body: dict[str, Any] | None = None,
) -> Any:
    return sanitize(await client.call(method, params, body=body))
```

`bing_webmaster_mcp/ops/sites.py`:

```python
from __future__ import annotations

from typing import Any

from ..client import BingClient
from ._common import fetch, normalise_site


async def list_sites(client: BingClient) -> list[dict[str, Any]]:
    return await fetch(client, "GetUserSites")


async def site_roles(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(
        client, "GetSiteRoles", {"siteUrl": normalise_site(site_url), "includeAllPending": "true"}
    )


async def site_moves(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetSiteMoves", {"siteUrl": normalise_site(site_url)})
```

`bing_webmaster_mcp/cli.py`:

```python
"""Click entry point. Thin by policy: behaviour lives in ops/."""

from __future__ import annotations

import asyncio
import json as jsonlib
import sys
from collections.abc import Awaitable
from typing import Any

import click

from .client import BingClient
from .config import Settings
from .errors import BingWebmasterError
from .ops import sites as sites_ops


def _load_settings() -> Settings:
    return Settings.load()


def _transport() -> Any:
    return None  # real network; tests monkeypatch this to a MockTransport


def run_async(coro: Awaitable[Any]) -> Any:
    return asyncio.run(coro)  # type: ignore[arg-type]


async def _with_client(fn) -> Any:
    settings = _load_settings()
    async with BingClient(settings, transport=_transport()) as client:
        return await fn(client, settings)


def emit(result: Any, as_json: bool) -> None:
    if as_json:
        click.echo(jsonlib.dumps(result, indent=2, default=str, ensure_ascii=False))
    else:
        click.echo(jsonlib.dumps(result, indent=2, default=str, ensure_ascii=False))


def guarded(fn):
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except BingWebmasterError as exc:
            click.echo(jsonlib.dumps(exc.to_dict(), indent=2, ensure_ascii=False), err=True)
            sys.exit(1)

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


@click.group()
def main() -> None:
    """Bing Webmaster Tools from the command line."""


@main.group("sites")
def sites_group() -> None:
    """Sites in the account."""


@sites_group.command("list")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@guarded
def sites_list(as_json: bool) -> None:
    """List every site in the account."""
    emit(run_async(_with_client(lambda client, _s: sites_ops.list_sites(client))), as_json)


@sites_group.command("roles")
@click.argument("site")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@guarded
def sites_roles(site: str, as_json: bool) -> None:
    """List who has access to SITE."""
    emit(run_async(_with_client(lambda client, _s: sites_ops.site_roles(client, site))), as_json)
```

Note for the implementer: `guarded` must wrap the function *inside* the Click
decorator stack as written above, so the `SystemExit` happens after Click has parsed
arguments. `CliRunner` reports it as `exit_code == 1`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ops_sites.py tests/test_cli.py -v` then `make lint`
Expected: 7 passed, lint clean

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/ops bing_webmaster_mcp/cli.py tests/test_ops_sites.py tests/test_cli.py
git commit -m "Add sites ops and the first CLI command"
```

---

### Task 9: Traffic and query reads

**Files:**
- Create: `bing_webmaster_mcp/ops/traffic.py`, `tests/test_ops_traffic.py`
- Modify: `bing_webmaster_mcp/cli.py` — add the `traffic` subgroup

**Interfaces:**
- Consumes: `ops/_common.fetch`, `ops/_common.normalise_site`
- Produces, all `async (client, ...) -> list[dict] | dict`:
  `query_stats(client, site_url)`, `query_traffic_stats(client, site_url, query)`,
  `query_page_stats(client, site_url, query)`,
  `query_page_detail_stats(client, site_url, query, page)`,
  `page_stats(client, site_url)`, `page_query_stats(client, site_url, page)`,
  `rank_and_traffic_stats(client, site_url)`

- [ ] **Step 1: Write the failing test**

`tests/test_ops_traffic.py`:

```python
import pytest
from fakes import bing_transport, fake_settings

from bing_webmaster_mcp.client import BingClient
from bing_webmaster_mcp.ops import traffic


@pytest.mark.parametrize(
    ("fn", "method", "args", "expected_params"),
    [
        (traffic.query_stats, "GetQueryStats", (), {"siteUrl": "https://a.example"}),
        (
            traffic.query_traffic_stats,
            "GetQueryTrafficStats",
            ("shoes",),
            {"siteUrl": "https://a.example", "query": "shoes"},
        ),
        (
            traffic.query_page_stats,
            "GetQueryPageStats",
            ("shoes",),
            {"siteUrl": "https://a.example", "query": "shoes"},
        ),
        (
            traffic.query_page_detail_stats,
            "GetQueryPageDetailStats",
            ("shoes", "https://a.example/p"),
            {"siteUrl": "https://a.example", "query": "shoes", "page": "https://a.example/p"},
        ),
        (traffic.page_stats, "GetPageStats", (), {"siteUrl": "https://a.example"}),
        (
            traffic.page_query_stats,
            "GetPageQueryStats",
            ("https://a.example/p",),
            {"siteUrl": "https://a.example", "page": "https://a.example/p"},
        ),
        (traffic.rank_and_traffic_stats, "GetRankAndTrafficStats", (), {"siteUrl": "https://a.example"}),
    ],
)
async def test_each_call_hits_the_right_method_with_the_right_params(
    tmp_path, fn, method, args, expected_params
):
    transport = bing_transport({method: []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await fn(client, "a.example/", *args)
    request = transport.calls[0]
    assert request.url.path.endswith(f"/{method}")
    for key, value in expected_params.items():
        assert request.url.params[key] == value


async def test_query_text_comes_back_marked_untrusted(tmp_path):
    transport = bing_transport({"GetQueryStats": [{"Query": "shoes", "Clicks": 3}]})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        rows = await traffic.query_stats(client, "a.example")
    assert rows == [{"Query": {"value": "shoes", "untrusted": True}, "Clicks": 3}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ops_traffic.py -v`
Expected: FAIL with `ImportError: cannot import name 'traffic'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/ops/traffic.py`:

```python
from __future__ import annotations

from typing import Any

from ..client import BingClient
from ._common import fetch, normalise_site


async def query_stats(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetQueryStats", {"siteUrl": normalise_site(site_url)})


async def query_traffic_stats(
    client: BingClient, site_url: str, query: str
) -> list[dict[str, Any]]:
    return await fetch(
        client, "GetQueryTrafficStats", {"siteUrl": normalise_site(site_url), "query": query}
    )


async def query_page_stats(client: BingClient, site_url: str, query: str) -> list[dict[str, Any]]:
    return await fetch(
        client, "GetQueryPageStats", {"siteUrl": normalise_site(site_url), "query": query}
    )


async def query_page_detail_stats(
    client: BingClient, site_url: str, query: str, page: str
) -> list[dict[str, Any]]:
    return await fetch(
        client,
        "GetQueryPageDetailStats",
        {"siteUrl": normalise_site(site_url), "query": query, "page": page},
    )


async def page_stats(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetPageStats", {"siteUrl": normalise_site(site_url)})


async def page_query_stats(client: BingClient, site_url: str, page: str) -> list[dict[str, Any]]:
    return await fetch(
        client, "GetPageQueryStats", {"siteUrl": normalise_site(site_url), "page": page}
    )


async def rank_and_traffic_stats(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetRankAndTrafficStats", {"siteUrl": normalise_site(site_url)})
```

Add to `cli.py`, importing `from .ops import traffic as traffic_ops`:

```python
@main.group("traffic")
def traffic_group() -> None:
    """Impressions, clicks and positions."""


@traffic_group.command("queries")
@click.argument("site")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@guarded
def traffic_queries(site: str, as_json: bool) -> None:
    """Top queries for SITE."""
    emit(run_async(_with_client(lambda c, _s: traffic_ops.query_stats(c, site))), as_json)


@traffic_group.command("pages")
@click.argument("site")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@guarded
def traffic_pages(site: str, as_json: bool) -> None:
    """Top pages for SITE."""
    emit(run_async(_with_client(lambda c, _s: traffic_ops.page_stats(c, site))), as_json)


@traffic_group.command("rank")
@click.argument("site")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@guarded
def traffic_rank(site: str, as_json: bool) -> None:
    """Impressions and clicks over time for SITE."""
    emit(run_async(_with_client(lambda c, _s: traffic_ops.rank_and_traffic_stats(c, site))), as_json)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ops_traffic.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/ops/traffic.py bing_webmaster_mcp/cli.py tests/test_ops_traffic.py
git commit -m "Add traffic reads"
```

---

### Task 10: Index and crawl reads

`FetchUrl` and `SaveCrawlSettings` are writes and are **not** implemented here —
they arrive in Task 15 behind a plan.

**Files:**
- Create: `bing_webmaster_mcp/ops/crawl.py`, `tests/test_ops_crawl.py`
- Modify: `bing_webmaster_mcp/cli.py` — add `index` and `crawl` subgroups

**Interfaces:**
- Produces, all `async (client, ...)`:
  `url_info(client, site_url, url)`, `url_traffic_info(client, site_url, url)`,
  `children_url_info(client, site_url, url, page=0)`,
  `children_url_traffic_info(client, site_url, url, page=0)`,
  `crawl_stats(client, site_url)`, `crawl_issues(client, site_url)`,
  `crawl_settings(client, site_url)`, `fetched_urls(client, site_url)`,
  `fetched_url_details(client, site_url, url)`

- [ ] **Step 1: Write the failing test**

`tests/test_ops_crawl.py`:

```python
import pytest
from fakes import bing_transport, fake_settings

from bing_webmaster_mcp.client import BingClient
from bing_webmaster_mcp.ops import crawl


@pytest.mark.parametrize(
    ("fn", "method", "args"),
    [
        (crawl.url_info, "GetUrlInfo", ("https://a.example/p",)),
        (crawl.url_traffic_info, "GetUrlTrafficInfo", ("https://a.example/p",)),
        (crawl.crawl_stats, "GetCrawlStats", ()),
        (crawl.crawl_issues, "GetCrawlIssues", ()),
        (crawl.crawl_settings, "GetCrawlSettings", ()),
        (crawl.fetched_urls, "GetFetchedUrls", ()),
        (crawl.fetched_url_details, "GetFetchedUrlDetails", ("https://a.example/p",)),
    ],
)
async def test_methods_are_routed(tmp_path, fn, method, args):
    transport = bing_transport({method: []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await fn(client, "a.example", *args)
    assert transport.calls[0].url.path.endswith(f"/{method}")


async def test_children_pagination_defaults_to_zero(tmp_path):
    transport = bing_transport({"GetChildrenUrlInfo": []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await crawl.children_url_info(client, "a.example", "https://a.example/dir")
    assert transport.calls[0].url.params["page"] == "0"


async def test_children_pagination_is_passed_through(tmp_path):
    transport = bing_transport({"GetChildrenUrlTrafficInfo": []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await crawl.children_url_traffic_info(client, "a.example", "https://a.example/dir", page=3)
    assert transport.calls[0].url.params["page"] == "3"


async def test_crawl_issue_urls_are_marked_untrusted(tmp_path):
    # A crawl issue can carry any URL a bot invented. It is data, not instruction.
    transport = bing_transport({"GetCrawlIssues": [{"Url": "https://a.example/‮evil"}]})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        rows = await crawl.crawl_issues(client, "a.example")
    assert rows[0]["Url"]["untrusted"] is True
    assert "‮" not in rows[0]["Url"]["value"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ops_crawl.py -v`
Expected: FAIL with `ImportError: cannot import name 'crawl'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/ops/crawl.py`:

```python
from __future__ import annotations

from typing import Any

from ..client import BingClient
from ._common import fetch, normalise_site


async def url_info(client: BingClient, site_url: str, url: str) -> dict[str, Any]:
    return await fetch(client, "GetUrlInfo", {"siteUrl": normalise_site(site_url), "url": url})


async def url_traffic_info(client: BingClient, site_url: str, url: str) -> dict[str, Any]:
    return await fetch(
        client, "GetUrlTrafficInfo", {"siteUrl": normalise_site(site_url), "url": url}
    )


async def children_url_info(
    client: BingClient, site_url: str, url: str, page: int = 0
) -> list[dict[str, Any]]:
    return await fetch(
        client,
        "GetChildrenUrlInfo",
        {"siteUrl": normalise_site(site_url), "url": url, "page": page},
    )


async def children_url_traffic_info(
    client: BingClient, site_url: str, url: str, page: int = 0
) -> list[dict[str, Any]]:
    return await fetch(
        client,
        "GetChildrenUrlTrafficInfo",
        {"siteUrl": normalise_site(site_url), "url": url, "page": page},
    )


async def crawl_stats(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetCrawlStats", {"siteUrl": normalise_site(site_url)})


async def crawl_issues(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetCrawlIssues", {"siteUrl": normalise_site(site_url)})


async def crawl_settings(client: BingClient, site_url: str) -> dict[str, Any]:
    return await fetch(client, "GetCrawlSettings", {"siteUrl": normalise_site(site_url)})


async def fetched_urls(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetFetchedUrls", {"siteUrl": normalise_site(site_url)})


async def fetched_url_details(client: BingClient, site_url: str, url: str) -> dict[str, Any]:
    return await fetch(
        client, "GetFetchedUrlDetails", {"siteUrl": normalise_site(site_url), "url": url}
    )
```

Add to `cli.py`, importing `from .ops import crawl as crawl_ops`:

```python
@main.group("index")
def index_group() -> None:
    """What Bing has indexed."""


@index_group.command("url")
@click.argument("site")
@click.argument("url")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@guarded
def index_url(site: str, url: str, as_json: bool) -> None:
    """Index details for URL on SITE."""
    emit(run_async(_with_client(lambda c, _s: crawl_ops.url_info(c, site, url))), as_json)


@main.group("crawl")
def crawl_group() -> None:
    """Crawl statistics and problems."""


@crawl_group.command("issues")
@click.argument("site")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@guarded
def crawl_issues_cmd(site: str, as_json: bool) -> None:
    """Crawl issues for SITE."""
    emit(run_async(_with_client(lambda c, _s: crawl_ops.crawl_issues(c, site))), as_json)


@crawl_group.command("stats")
@click.argument("site")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@guarded
def crawl_stats_cmd(site: str, as_json: bool) -> None:
    """Crawl statistics for SITE."""
    emit(run_async(_with_client(lambda c, _s: crawl_ops.crawl_stats(c, site))), as_json)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ops_crawl.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/ops/crawl.py bing_webmaster_mcp/cli.py tests/test_ops_crawl.py
git commit -m "Add index and crawl reads"
```

---

### Task 11: The remaining reads

Links, keywords, sitemaps, quotas and the read halves of the settings groups. After
this task every `R` row in `docs/api-surface.md` has an implementation.

**Files:**
- Create: `bing_webmaster_mcp/ops/links.py`, `bing_webmaster_mcp/ops/keywords.py`, `bing_webmaster_mcp/ops/sitemaps.py`, `bing_webmaster_mcp/ops/settings_reads.py`, `bing_webmaster_mcp/ops/submission.py`, `tests/test_ops_reads.py`, `tests/test_read_coverage.py`

**Interfaces:**
- Produces:
  - `links.py`: `link_counts(client, site_url, page=0)`, `url_links(client, site_url, url, page=0)`, `connected_pages(client, site_url)`
  - `keywords.py`: `keyword(client, keyword, country, language, start_date, end_date)`, `keyword_stats(client, keyword, country, language)`, `related_keywords(client, keyword, country, language, start_date, end_date)` — dates are `datetime.date`, serialised as `YYYY-MM-DD`
  - `sitemaps.py`: `feeds(client, site_url)`, `feed_details(client, site_url, feed_url)`
  - `settings_reads.py`: `blocked_urls`, `query_parameters`, `country_region_settings`, `page_preview_blocks`, `deep_link_blocks` — each `(client, site_url)`
  - `submission.py`: `url_submission_quota(client, site_url)`, `content_submission_quota(client, site_url)`

- [ ] **Step 1: Write the failing test**

`tests/test_ops_reads.py`:

```python
from datetime import date

import pytest
from fakes import bing_transport, fake_settings

from bing_webmaster_mcp.client import BingClient
from bing_webmaster_mcp.ops import keywords, links, settings_reads, sitemaps, submission


@pytest.mark.parametrize(
    ("fn", "method", "args"),
    [
        (links.link_counts, "GetLinkCounts", ()),
        (links.connected_pages, "GetConnectedPages", ()),
        (sitemaps.feeds, "GetFeeds", ()),
        (sitemaps.feed_details, "GetFeedDetails", ("https://a.example/sitemap.xml",)),
        (settings_reads.blocked_urls, "GetBlockedUrls", ()),
        (settings_reads.query_parameters, "GetQueryParameters", ()),
        (settings_reads.country_region_settings, "GetCountryRegionSettings", ()),
        (settings_reads.page_preview_blocks, "GetActivePagePreviewBlocks", ()),
        (settings_reads.deep_link_blocks, "GetDeepLinkBlocks", ()),
        (submission.url_submission_quota, "GetUrlSubmissionQuota", ()),
        (submission.content_submission_quota, "GetContentSubmissionQuota", ()),
    ],
)
async def test_site_scoped_reads_are_routed(tmp_path, fn, method, args):
    transport = bing_transport({method: []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await fn(client, "a.example", *args)
    request = transport.calls[0]
    assert request.url.path.endswith(f"/{method}")
    assert request.url.params["siteUrl"] == "https://a.example"


async def test_url_links_paginates(tmp_path):
    transport = bing_transport({"GetUrlLinks": []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await links.url_links(client, "a.example", "https://a.example/p", page=2)
    assert transport.calls[0].url.params["page"] == "2"


async def test_anchor_text_is_marked_untrusted(tmp_path):
    transport = bing_transport({"GetUrlLinks": [{"AnchorText": "buy now", "Url": "https://x"}]})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        rows = await links.url_links(client, "a.example", "https://a.example/p")
    assert rows[0]["AnchorText"] == {"value": "buy now", "untrusted": True}


async def test_keyword_dates_are_iso_days(tmp_path):
    transport = bing_transport({"GetKeyword": {}})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await keywords.keyword(client, "shoes", "US", "en-US", date(2026, 8, 1), date(2026, 8, 25))
    params = transport.calls[0].url.params
    assert params["startDate"] == "2026-08-01"
    assert params["endDate"] == "2026-08-25"
    assert params["q"] == "shoes"


async def test_keyword_stats_takes_no_dates(tmp_path):
    transport = bing_transport({"GetKeywordStats": []})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await keywords.keyword_stats(client, "shoes", "US", "en-US")
    assert "startDate" not in transport.calls[0].url.params
```

`tests/test_read_coverage.py` — the coverage gate that makes this task's boundary real:

```python
import importlib
import re
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "docs" / "api-surface.md"
ROW = re.compile(r"^\|\s*`(?P<method>\w+)`\s*\|.*\|\s*(?P<rw>[RW])\s*\|")

OPS_MODULES = [
    "sites",
    "traffic",
    "crawl",
    "links",
    "keywords",
    "sitemaps",
    "settings_reads",
    "submission",
]

# Deliberately unexposed, with the reason. See docs/product-boundaries.md.
EXCLUDED = {
    "GetDeepLinkAlgoUrls",  # Microsoft marks it Obsolete
    "GetDeepLink",  # Microsoft marks it Obsolete
}


def test_every_read_method_appears_in_an_ops_module():
    sources = "\n".join(
        importlib.import_module(f"bing_webmaster_mcp.ops.{name}").__file__ and
        Path(importlib.import_module(f"bing_webmaster_mcp.ops.{name}").__file__).read_text()
        for name in OPS_MODULES
    )
    missing = [
        m["method"]
        for line in DOC.read_text().splitlines()
        if (m := ROW.match(line)) and m["rw"] == "R" and m["method"] not in EXCLUDED
        if f'"{m["method"]}"' not in sources
    ]
    assert not missing, f"read methods with no implementation: {missing}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ops_reads.py tests/test_read_coverage.py -v`
Expected: FAIL with `ImportError: cannot import name 'links'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/ops/links.py`:

```python
from __future__ import annotations

from typing import Any

from ..client import BingClient
from ._common import fetch, normalise_site


async def link_counts(client: BingClient, site_url: str, page: int = 0) -> list[dict[str, Any]]:
    return await fetch(client, "GetLinkCounts", {"siteUrl": normalise_site(site_url), "page": page})


async def url_links(
    client: BingClient, site_url: str, url: str, page: int = 0
) -> list[dict[str, Any]]:
    return await fetch(
        client, "GetUrlLinks", {"siteUrl": normalise_site(site_url), "url": url, "page": page}
    )


async def connected_pages(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetConnectedPages", {"siteUrl": normalise_site(site_url)})
```

`bing_webmaster_mcp/ops/keywords.py`:

```python
from __future__ import annotations

from datetime import date
from typing import Any

from ..client import BingClient
from ._common import fetch


async def keyword(
    client: BingClient,
    keyword: str,
    country: str,
    language: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    return await fetch(
        client,
        "GetKeyword",
        {
            "q": keyword,
            "country": country,
            "language": language,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        },
    )


async def keyword_stats(
    client: BingClient, keyword: str, country: str, language: str
) -> list[dict[str, Any]]:
    return await fetch(
        client, "GetKeywordStats", {"q": keyword, "country": country, "language": language}
    )


async def related_keywords(
    client: BingClient,
    keyword: str,
    country: str,
    language: str,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    return await fetch(
        client,
        "GetRelatedKeywords",
        {
            "q": keyword,
            "country": country,
            "language": language,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        },
    )
```

`bing_webmaster_mcp/ops/sitemaps.py`:

```python
from __future__ import annotations

from typing import Any

from ..client import BingClient
from ._common import fetch, normalise_site


async def feeds(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetFeeds", {"siteUrl": normalise_site(site_url)})


async def feed_details(client: BingClient, site_url: str, feed_url: str) -> list[dict[str, Any]]:
    return await fetch(
        client, "GetFeedDetails", {"siteUrl": normalise_site(site_url), "feedUrl": feed_url}
    )
```

`bing_webmaster_mcp/ops/settings_reads.py`:

```python
"""Read halves of the configuration groups. Their write halves live behind plans."""

from __future__ import annotations

from typing import Any

from ..client import BingClient
from ._common import fetch, normalise_site


async def blocked_urls(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetBlockedUrls", {"siteUrl": normalise_site(site_url)})


async def query_parameters(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetQueryParameters", {"siteUrl": normalise_site(site_url)})


async def country_region_settings(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetCountryRegionSettings", {"siteUrl": normalise_site(site_url)})


async def page_preview_blocks(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(
        client, "GetActivePagePreviewBlocks", {"siteUrl": normalise_site(site_url)}
    )


async def deep_link_blocks(client: BingClient, site_url: str) -> list[dict[str, Any]]:
    return await fetch(client, "GetDeepLinkBlocks", {"siteUrl": normalise_site(site_url)})
```

`bing_webmaster_mcp/ops/submission.py`:

```python
"""Quota reads. The submission writes themselves arrive with plans (Task 13)."""

from __future__ import annotations

from typing import Any

from ..client import BingClient
from ._common import fetch, normalise_site


async def url_submission_quota(client: BingClient, site_url: str) -> dict[str, Any]:
    return await fetch(client, "GetUrlSubmissionQuota", {"siteUrl": normalise_site(site_url)})


async def content_submission_quota(client: BingClient, site_url: str) -> dict[str, Any]:
    return await fetch(client, "GetContentSubmissionQuota", {"siteUrl": normalise_site(site_url)})
```

Also add `bing-wm links`, `bing-wm keywords`, `bing-wm sitemaps list` and `bing-wm quota`
commands to `cli.py`, following exactly the shape used in Task 9 (`@main.group`, one
`@click.argument("site")`, a `--json` flag, `@guarded`, `emit(run_async(...))`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -v` then `make lint`
Expected: all green, and `test_every_read_method_appears_in_an_ops_module` passes —
if it names a method, implement it rather than adding it to `EXCLUDED`, unless the
reason goes into `docs/product-boundaries.md` in the same commit.

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/ops bing_webmaster_mcp/cli.py tests/test_ops_reads.py tests/test_read_coverage.py
git commit -m "Add links, keywords, sitemap and settings reads"
```

---

### Task 12: Audit log and restart-persistent rate limits

Both are compensating controls for the honest limit named in `SPEC.md` §6: an MCP
client with a shell can run `plan apply` itself. These make that visible and bounded.

**Files:**
- Create: `bing_webmaster_mcp/audit.py`, `bing_webmaster_mcp/limits.py`, `tests/test_audit.py`, `tests/test_limits.py`

**Interfaces:**
- Produces:
  - `audit.AuditLog(state_dir: Path)` with `record(event: str, **fields: Any) -> None` and `entries() -> list[dict]`; writes JSON lines to `state_dir/audit.jsonl`, appending only
  - `limits.RateLimiter(state_dir: Path, *, max_per_day: int)` with `check(key: str, cost: int = 1) -> None` raising `QuotaExceeded`, and `consume(key: str, cost: int = 1) -> None`; counters persist in `state_dir/limits.json` and roll over on UTC date change

- [ ] **Step 1: Write the failing test**

`tests/test_audit.py`:

```python
import json

from bing_webmaster_mcp.audit import AuditLog


def test_entries_are_appended_as_json_lines(tmp_path):
    log = AuditLog(tmp_path)
    log.record("plan_created", plan_id="abc", operation="submit_url")
    log.record("plan_applied", plan_id="abc", outcome="ok")

    lines = (tmp_path / "audit.jsonl").read_text().strip().splitlines()
    assert [json.loads(line)["event"] for line in lines] == ["plan_created", "plan_applied"]
    assert json.loads(lines[0])["plan_id"] == "abc"


def test_every_entry_is_timestamped(tmp_path):
    log = AuditLog(tmp_path)
    log.record("x")
    assert "ts" in log.entries()[0]


def test_a_second_instance_appends_rather_than_truncates(tmp_path):
    AuditLog(tmp_path).record("first")
    AuditLog(tmp_path).record("second")
    assert [e["event"] for e in AuditLog(tmp_path).entries()] == ["first", "second"]
```

`tests/test_limits.py`:

```python
import pytest

from bing_webmaster_mcp.errors import QuotaExceeded
from bing_webmaster_mcp.limits import RateLimiter


def test_consumption_accumulates(tmp_path):
    limiter = RateLimiter(tmp_path, max_per_day=10)
    limiter.consume("https://a.example", 4)
    limiter.check("https://a.example", 6)
    with pytest.raises(QuotaExceeded):
        limiter.check("https://a.example", 7)


def test_counters_survive_a_new_instance(tmp_path):
    RateLimiter(tmp_path, max_per_day=5).consume("https://a.example", 5)
    with pytest.raises(QuotaExceeded):
        RateLimiter(tmp_path, max_per_day=5).check("https://a.example", 1)


def test_keys_are_independent(tmp_path):
    limiter = RateLimiter(tmp_path, max_per_day=5)
    limiter.consume("https://a.example", 5)
    limiter.check("https://b.example", 5)


def test_counter_rolls_over_on_a_new_utc_day(tmp_path, monkeypatch):
    limiter = RateLimiter(tmp_path, max_per_day=1)
    monkeypatch.setattr("bing_webmaster_mcp.limits._today", lambda: "2026-08-25")
    limiter.consume("https://a.example")
    with pytest.raises(QuotaExceeded):
        limiter.check("https://a.example")
    monkeypatch.setattr("bing_webmaster_mcp.limits._today", lambda: "2026-08-26")
    limiter.check("https://a.example")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_audit.py tests/test_limits.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bing_webmaster_mcp.audit'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/audit.py`:

```python
"""Append-only record of every write this program attempted and how it ended."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, state_dir: Path) -> None:
        self._path = Path(state_dir) / "audit.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, **fields: Any) -> None:
        entry = {"ts": datetime.now(UTC).isoformat(), "event": event, **fields}
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    def entries(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        return [json.loads(line) for line in self._path.read_text(encoding="utf-8").splitlines()]
```

`bing_webmaster_mcp/limits.py`:

```python
"""Daily write budget that survives a restart.

Bing enforces its own submission quota; this is a local ceiling on top of it, so a
runaway loop stops at a number the operator chose rather than at Bing's.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .errors import QuotaExceeded


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


class RateLimiter:
    def __init__(self, state_dir: Path, *, max_per_day: int) -> None:
        self._path = Path(state_dir) / "limits.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._max = max_per_day

    def _load(self) -> dict[str, int]:
        if not self._path.exists():
            return {}
        stored = json.loads(self._path.read_text(encoding="utf-8"))
        if stored.get("date") != _today():
            return {}
        return stored.get("counts", {})

    def check(self, key: str, cost: int = 1) -> None:
        used = self._load().get(key, 0)
        if used + cost > self._max:
            raise QuotaExceeded(
                f"local daily limit reached for {key}: {used}/{self._max}",
                suggestion="raise BING_WM_MAX_WRITES_PER_DAY or wait for the UTC day to roll over",
                details={"used": used, "requested": cost, "max_per_day": self._max},
            )

    def consume(self, key: str, cost: int = 1) -> None:
        self.check(key, cost)
        counts = self._load()
        counts[key] = counts.get(key, 0) + cost
        self._path.write_text(
            json.dumps({"date": _today(), "counts": counts}), encoding="utf-8"
        )
```

Add `max_writes_per_day: int = Field(default=200, gt=0)` to `Settings` in `config.py`
so `BING_WM_MAX_WRITES_PER_DAY` configures it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_audit.py tests/test_limits.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/audit.py bing_webmaster_mcp/limits.py bing_webmaster_mcp/config.py tests/test_audit.py tests/test_limits.py
git commit -m "Add audit log and persistent write limits"
```

---

### Task 13: Plan-and-apply, and the first write

The reason this project exists. Get the boundary right here; Task 14 is then
mechanical.

**Files:**
- Create: `bing_webmaster_mcp/plans.py`, `bing_webmaster_mcp/apply.py`, `bing_webmaster_mcp/writes.py`, `tests/test_plans.py`, `tests/test_apply.py`
- Modify: `bing_webmaster_mcp/cli.py` — add the `plan` subgroup

**Interfaces:**
- Consumes: `Settings`, `BingClient`, `AuditLog`, `RateLimiter`, the plan error classes
- Produces:
  - `writes.py`: `WriteOp(name: str, method: str, cost: int, build: Callable[[dict], dict], summarise: Callable[[dict], str], http: str)` and `WRITE_OPS: dict[str, WriteOp]`, seeded with `submit_url`
  - `plans.py`: `Plan` (pydantic model: `plan_id, operation, site_url, args, summary, created_at, expires_at, applied_at`), `Plan.is_expired(now=None) -> bool`, and `PlanStore(state_dir, ttl_seconds)` with `create(operation, site_url, args, summary) -> Plan`, `get(plan_id) -> Plan`, `list() -> list[Plan]`, `mark_applied(plan_id) -> None`, `reject(plan_id) -> None`
  - `apply.py`: `async apply_plan(plan_id, *, store, client, audit, limiter) -> dict`

- [ ] **Step 1: Write the failing test**

`tests/test_plans.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest

from bing_webmaster_mcp.errors import PlanAlreadyApplied, PlanNotFound
from bing_webmaster_mcp.plans import PlanStore


def test_created_plan_gets_an_id_and_a_summary(tmp_path):
    store = PlanStore(tmp_path, ttl_seconds=900)
    plan = store.create("submit_url", "https://a.example", {"url": "https://a.example/p"}, "submit 1 URL")
    assert plan.plan_id
    assert plan.summary == "submit 1 URL"
    assert plan.applied_at is None


def test_plans_survive_a_new_store(tmp_path):
    plan = PlanStore(tmp_path, ttl_seconds=900).create("submit_url", "https://a.example", {}, "s")
    assert PlanStore(tmp_path, ttl_seconds=900).get(plan.plan_id).operation == "submit_url"


def test_unknown_plan_raises(tmp_path):
    with pytest.raises(PlanNotFound):
        PlanStore(tmp_path, ttl_seconds=900).get("nope")


def test_marking_applied_twice_raises(tmp_path):
    store = PlanStore(tmp_path, ttl_seconds=900)
    plan = store.create("submit_url", "https://a.example", {}, "s")
    store.mark_applied(plan.plan_id)
    with pytest.raises(PlanAlreadyApplied):
        store.mark_applied(plan.plan_id)


def test_expiry_is_computed_from_the_ttl(tmp_path):
    store = PlanStore(tmp_path, ttl_seconds=60)
    plan = store.create("submit_url", "https://a.example", {}, "s")
    assert plan.expires_at - plan.created_at == timedelta(seconds=60)
    assert plan.is_expired(now=datetime.now(UTC) + timedelta(seconds=61))
    assert not plan.is_expired(now=datetime.now(UTC))


def test_rejecting_removes_the_plan(tmp_path):
    store = PlanStore(tmp_path, ttl_seconds=900)
    plan = store.create("submit_url", "https://a.example", {}, "s")
    store.reject(plan.plan_id)
    with pytest.raises(PlanNotFound):
        store.get(plan.plan_id)
```

`tests/test_apply.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from fakes import bing_transport, fake_settings

from bing_webmaster_mcp.apply import apply_plan
from bing_webmaster_mcp.audit import AuditLog
from bing_webmaster_mcp.client import BingClient
from bing_webmaster_mcp.errors import PlanAlreadyApplied, PlanExpired
from bing_webmaster_mcp.limits import RateLimiter
from bing_webmaster_mcp.plans import PlanStore


async def _apply(tmp_path, transport, plan, *, max_per_day=100):
    store = PlanStore(tmp_path, ttl_seconds=900)
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        return await apply_plan(
            plan.plan_id,
            store=store,
            client=client,
            audit=AuditLog(tmp_path),
            limiter=RateLimiter(tmp_path, max_per_day=max_per_day),
        )


async def test_apply_calls_bing_and_marks_the_plan(tmp_path):
    store = PlanStore(tmp_path, ttl_seconds=900)
    plan = store.create(
        "submit_url", "https://a.example", {"url": "https://a.example/p"}, "submit 1 URL"
    )
    transport = bing_transport({"SubmitUrl": None})

    result = await _apply(tmp_path, transport, plan)

    assert transport.calls[0].url.path.endswith("/SubmitUrl")
    assert result["applied"] is True
    assert PlanStore(tmp_path, ttl_seconds=900).get(plan.plan_id).applied_at is not None


async def test_applying_twice_is_refused(tmp_path):
    store = PlanStore(tmp_path, ttl_seconds=900)
    plan = store.create("submit_url", "https://a.example", {"url": "https://a.example/p"}, "s")
    transport = bing_transport({"SubmitUrl": None})
    await _apply(tmp_path, transport, plan)
    with pytest.raises(PlanAlreadyApplied):
        await _apply(tmp_path, transport, plan)
    assert len(transport.calls) == 1, "a refused apply must not reach Bing"


async def test_expired_plan_is_refused_before_the_call(tmp_path):
    store = PlanStore(tmp_path, ttl_seconds=1)
    plan = store.create("submit_url", "https://a.example", {"url": "https://a.example/p"}, "s")
    store.set_expiry(plan.plan_id, datetime.now(UTC) - timedelta(seconds=1))
    transport = bing_transport({"SubmitUrl": None})
    with pytest.raises(PlanExpired):
        await _apply(tmp_path, transport, plan)
    assert transport.calls == []


async def test_local_limit_stops_the_call(tmp_path):
    from bing_webmaster_mcp.errors import QuotaExceeded

    store = PlanStore(tmp_path, ttl_seconds=900)
    plan = store.create("submit_url", "https://a.example", {"url": "https://a.example/p"}, "s")
    transport = bing_transport({"SubmitUrl": None})
    with pytest.raises(QuotaExceeded):
        await _apply(tmp_path, transport, plan, max_per_day=0)
    assert transport.calls == []


async def test_both_attempt_and_outcome_are_audited(tmp_path):
    store = PlanStore(tmp_path, ttl_seconds=900)
    plan = store.create("submit_url", "https://a.example", {"url": "https://a.example/p"}, "s")
    await _apply(tmp_path, bing_transport({"SubmitUrl": None}), plan)
    events = [entry["event"] for entry in AuditLog(tmp_path).entries()]
    assert events == ["plan_apply_attempted", "plan_apply_succeeded"]


async def test_a_failed_apply_is_audited_and_leaves_the_plan_unapplied(tmp_path):
    from fakes import error_transport

    from bing_webmaster_mcp.errors import InvalidRequest

    store = PlanStore(tmp_path, ttl_seconds=900)
    plan = store.create("submit_url", "https://a.example", {"url": "https://a.example/p"}, "s")
    transport = error_transport(400, {"ErrorCode": 1, "Message": "bad url"})
    with pytest.raises(InvalidRequest):
        await _apply(tmp_path, transport, plan)
    assert AuditLog(tmp_path).entries()[-1]["event"] == "plan_apply_failed"
    assert PlanStore(tmp_path, ttl_seconds=900).get(plan.plan_id).applied_at is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_plans.py tests/test_apply.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bing_webmaster_mcp.plans'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/writes.py`:

```python
"""Registry of mutating operations. A write that is not in here cannot be planned,
and a write that is not planned cannot happen."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WriteOp:
    name: str
    method: str
    cost: int
    build: Callable[[dict[str, Any]], dict[str, Any]]
    summarise: Callable[[dict[str, Any]], str]
    http: str = "GET"  # "POST" when Bing needs a JSON body


WRITE_OPS: dict[str, WriteOp] = {
    "submit_url": WriteOp(
        name="submit_url",
        method="SubmitUrl",
        cost=1,
        build=lambda args: {"siteUrl": args["site_url"], "url": args["url"]},
        summarise=lambda args: f"submit {args['url']} to Bing for recrawl",
    ),
}
```

`bing_webmaster_mcp/plans.py`:

```python
"""Recorded intent. Creating a plan sends nothing; only apply.py sends."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .errors import PlanAlreadyApplied, PlanNotFound


class Plan(BaseModel):
    plan_id: str
    operation: str
    site_url: str
    args: dict[str, Any]
    summary: str
    created_at: datetime
    expires_at: datetime
    applied_at: datetime | None = None

    def is_expired(self, now: datetime | None = None) -> bool:
        return (now or datetime.now(UTC)) > self.expires_at


class PlanStore:
    def __init__(self, state_dir: Path, ttl_seconds: int) -> None:
        self._dir = Path(state_dir) / "plans"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ttl = ttl_seconds

    def _path(self, plan_id: str) -> Path:
        return self._dir / f"{plan_id}.json"

    def create(
        self, operation: str, site_url: str, args: dict[str, Any], summary: str
    ) -> Plan:
        now = datetime.now(UTC)
        plan = Plan(
            plan_id=secrets.token_hex(8),
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
        self._path(plan.plan_id).write_text(plan.model_dump_json(indent=2), encoding="utf-8")

    def get(self, plan_id: str) -> Plan:
        path = self._path(plan_id)
        if not path.exists():
            raise PlanNotFound(f"no plan {plan_id}", suggestion="run `bing-wm plan list`")
        return Plan.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self) -> list[Plan]:
        return sorted(
            (Plan.model_validate_json(p.read_text(encoding="utf-8")) for p in self._dir.glob("*.json")),
            key=lambda plan: plan.created_at,
        )

    def mark_applied(self, plan_id: str) -> None:
        plan = self.get(plan_id)
        if plan.applied_at is not None:
            raise PlanAlreadyApplied(f"plan {plan_id} was already applied at {plan.applied_at}")
        self._write(plan.model_copy(update={"applied_at": datetime.now(UTC)}))

    def set_expiry(self, plan_id: str, when: datetime) -> None:
        self._write(self.get(plan_id).model_copy(update={"expires_at": when}))

    def reject(self, plan_id: str) -> None:
        self._path(plan_id).unlink(missing_ok=True)

    def json_load(self, plan_id: str) -> dict[str, Any]:
        return json.loads(self._path(plan_id).read_text(encoding="utf-8"))
```

`bing_webmaster_mcp/apply.py`:

```python
"""The only place a mutating Bing call is made."""

from __future__ import annotations

from typing import Any

from .audit import AuditLog
from .client import BingClient
from .errors import BingWebmasterError, PlanAlreadyApplied, PlanExpired
from .limits import RateLimiter
from .plans import PlanStore
from .writes import WRITE_OPS


async def apply_plan(
    plan_id: str,
    *,
    store: PlanStore,
    client: BingClient,
    audit: AuditLog,
    limiter: RateLimiter,
) -> dict[str, Any]:
    plan = store.get(plan_id)
    if plan.applied_at is not None:
        raise PlanAlreadyApplied(f"plan {plan_id} was already applied at {plan.applied_at}")
    if plan.is_expired():
        raise PlanExpired(
            f"plan {plan_id} expired at {plan.expires_at}",
            suggestion="re-plan so a human reviews current arguments",
        )

    op = WRITE_OPS[plan.operation]
    limiter.check(plan.site_url, op.cost)

    audit.record(
        "plan_apply_attempted", plan_id=plan_id, operation=plan.operation, site=plan.site_url
    )
    params = op.build(plan.args)
    try:
        if op.http == "POST":
            result = await client.call(op.method, body=params)
        else:
            result = await client.call(op.method, params)
    except BingWebmasterError as exc:
        audit.record("plan_apply_failed", plan_id=plan_id, error=exc.to_dict())
        raise

    limiter.consume(plan.site_url, op.cost)
    store.mark_applied(plan_id)
    audit.record("plan_apply_succeeded", plan_id=plan_id)
    return {"applied": True, "plan_id": plan_id, "operation": plan.operation, "result": result}
```

Add the `plan` group to `cli.py`. `apply` prompts unless `--yes`:

```python
from .apply import apply_plan
from .audit import AuditLog
from .limits import RateLimiter
from .plans import PlanStore
from .writes import WRITE_OPS


@main.group("plan")
def plan_group() -> None:
    """Prepare a change, review it, then apply it."""


@plan_group.command("submit-url")
@click.argument("site")
@click.argument("url")
@guarded
def plan_submit_url(site: str, url: str) -> None:
    """Prepare a recrawl request for URL on SITE. Sends nothing."""
    settings = _load_settings()
    site_url = normalise_site(site)
    settings.check_site_allowed(site_url)
    args = {"site_url": site_url, "url": url}
    op = WRITE_OPS["submit_url"]
    store = PlanStore(settings.state_dir, settings.plan_ttl_seconds)
    plan = store.create("submit_url", site_url, args, op.summarise(args))
    AuditLog(settings.state_dir).record("plan_created", plan_id=plan.plan_id, operation="submit_url")
    click.echo(f"{plan.plan_id}  {plan.summary}")
    click.echo(f"apply with: bing-wm plan apply {plan.plan_id}")


@plan_group.command("list")
@guarded
def plan_list() -> None:
    """List plans that have not been applied or rejected."""
    settings = _load_settings()
    for plan in PlanStore(settings.state_dir, settings.plan_ttl_seconds).list():
        state = "applied" if plan.applied_at else ("expired" if plan.is_expired() else "pending")
        click.echo(f"{plan.plan_id}  {state:8}  {plan.summary}")


@plan_group.command("show")
@click.argument("plan_id")
@guarded
def plan_show(plan_id: str) -> None:
    """Show one plan in full."""
    settings = _load_settings()
    plan = PlanStore(settings.state_dir, settings.plan_ttl_seconds).get(plan_id)
    click.echo(plan.model_dump_json(indent=2))


@plan_group.command("apply")
@click.argument("plan_id")
@click.option("--yes", is_flag=True, help="Skip the confirmation prompt.")
@guarded
def plan_apply(plan_id: str, yes: bool) -> None:
    """Execute PLAN_ID. This is the step that changes something."""
    settings = _load_settings()
    store = PlanStore(settings.state_dir, settings.plan_ttl_seconds)
    plan = store.get(plan_id)
    if not yes:
        click.confirm(f"{plan.summary}\nApply?", abort=True)

    async def run(client, _settings):
        return await apply_plan(
            plan_id,
            store=store,
            client=client,
            audit=AuditLog(settings.state_dir),
            limiter=RateLimiter(settings.state_dir, max_per_day=settings.max_writes_per_day),
        )

    emit(run_async(_with_client(run)), True)


@plan_group.command("reject")
@click.argument("plan_id")
@guarded
def plan_reject(plan_id: str) -> None:
    """Discard PLAN_ID without applying it."""
    settings = _load_settings()
    PlanStore(settings.state_dir, settings.plan_ttl_seconds).reject(plan_id)
    AuditLog(settings.state_dir).record("plan_rejected", plan_id=plan_id)
    click.echo(f"rejected {plan_id}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_plans.py tests/test_apply.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/plans.py bing_webmaster_mcp/apply.py bing_webmaster_mcp/writes.py bing_webmaster_mcp/cli.py tests/test_plans.py tests/test_apply.py
git commit -m "Add plan-and-apply and the first write"
```

---

### Task 14: The remaining writes

Mechanical now: each write is a `WriteOp` entry plus a `plan` subcommand. Nothing
new goes into `apply.py`.

**Files:**
- Modify: `bing_webmaster_mcp/writes.py`, `bing_webmaster_mcp/cli.py`
- Create: `tests/test_writes.py`, `tests/test_write_coverage.py`

**Interfaces:**
- Consumes: `WriteOp`, `WRITE_OPS`
- Produces: `WRITE_OPS` keys `submit_url`, `submit_url_batch`, `submit_feed`, `remove_feed`, `add_site`, `remove_site`, `verify_site`, `add_site_roles`, `remove_site_role`, `submit_site_move`, `save_crawl_settings`, `fetch_url`, `submit_content`, `add_blocked_url`, `remove_blocked_url`, `add_query_parameter`, `remove_query_parameter`, `enable_disable_query_parameter`, `add_country_region_settings`, `remove_country_region_settings`, `add_page_preview_block`, `remove_page_preview_block`, `add_deep_link_block`, `remove_deep_link_block`, `add_connected_page`

- [ ] **Step 1: Write the failing test**

`tests/test_writes.py`:

```python
import pytest
from fakes import bing_transport, fake_settings

from bing_webmaster_mcp.apply import apply_plan
from bing_webmaster_mcp.audit import AuditLog
from bing_webmaster_mcp.client import BingClient
from bing_webmaster_mcp.limits import RateLimiter
from bing_webmaster_mcp.plans import PlanStore
from bing_webmaster_mcp.writes import WRITE_OPS

SITE = "https://a.example"


def test_every_write_op_has_a_nonzero_cost_and_a_summary():
    for name, op in WRITE_OPS.items():
        assert op.cost >= 1, name
        assert op.http in ("GET", "POST"), name


def test_batch_summary_states_the_count():
    op = WRITE_OPS["submit_url_batch"]
    summary = op.summarise({"site_url": SITE, "url_list": ["u1", "u2", "u3"]})
    assert "3" in summary


def test_batch_cost_is_the_number_of_urls():
    op = WRITE_OPS["submit_url_batch"]
    assert op.cost_for({"url_list": ["u1", "u2"]}) == 2


def test_destructive_summaries_name_the_target():
    summary = WRITE_OPS["remove_site"].summarise({"site_url": SITE})
    assert SITE in summary
    assert "remove" in summary.lower()


@pytest.mark.parametrize("name", sorted(WRITE_OPS))
async def test_each_write_routes_to_its_method(tmp_path, name):
    op = WRITE_OPS[name]
    args = _sample_args(name)
    store = PlanStore(tmp_path, ttl_seconds=900)
    plan = store.create(name, SITE, args, op.summarise(args))
    transport = bing_transport({op.method: None})
    async with BingClient(fake_settings(tmp_path), transport=transport) as client:
        await apply_plan(
            plan.plan_id,
            store=store,
            client=client,
            audit=AuditLog(tmp_path),
            limiter=RateLimiter(tmp_path, max_per_day=1000),
        )
    assert transport.calls[0].url.path.endswith(f"/{op.method}")


def _sample_args(name: str) -> dict:
    """One valid argument set per write, so the parametrised test stays honest."""
    base = {"site_url": SITE}
    extras = {
        "submit_url": {"url": f"{SITE}/p"},
        "submit_url_batch": {"url_list": [f"{SITE}/p"]},
        "submit_feed": {"feed_url": f"{SITE}/sitemap.xml"},
        "remove_feed": {"feed_url": f"{SITE}/sitemap.xml"},
        "add_site": {},
        "remove_site": {},
        "verify_site": {},
        "add_site_roles": {"email": "a@b.example", "role": "Administrator"},
        "remove_site_role": {"email": "a@b.example"},
        "submit_site_move": {"target": "https://b.example"},
        "save_crawl_settings": {"crawl_rate": [1] * 24},
        "fetch_url": {"url": f"{SITE}/p"},
        "submit_content": {"url": f"{SITE}/p", "content": "<html></html>"},
        "add_blocked_url": {"url": f"{SITE}/secret"},
        "remove_blocked_url": {"url": f"{SITE}/secret"},
        "add_query_parameter": {"parameter": "utm_source"},
        "remove_query_parameter": {"parameter": "utm_source"},
        "enable_disable_query_parameter": {"parameter": "utm_source", "enabled": True},
        "add_country_region_settings": {"country": "TH"},
        "remove_country_region_settings": {"country": "TH"},
        "add_page_preview_block": {"url": f"{SITE}/p", "reason": "Other"},
        "remove_page_preview_block": {"url": f"{SITE}/p"},
        "add_deep_link_block": {"url": f"{SITE}/p", "link_url": f"{SITE}/q", "link_text": "q"},
        "remove_deep_link_block": {"url": f"{SITE}/p", "link_url": f"{SITE}/q", "link_text": "q"},
        "add_connected_page": {"page_url": "https://social.example/profile"},
    }
    return base | extras[name]
```

`tests/test_write_coverage.py`:

```python
import re
from pathlib import Path

from bing_webmaster_mcp.writes import WRITE_OPS

DOC = Path(__file__).resolve().parents[1] / "docs" / "api-surface.md"
ROW = re.compile(r"^\|\s*`(?P<method>\w+)`\s*\|.*\|\s*(?P<rw>[RW])\s*\|")

# Deliberately unexposed. Every entry needs a line in docs/product-boundaries.md.
EXCLUDED = {"UpdateDeepLink"}  # Microsoft marks it Obsolete


def test_every_write_method_is_registered():
    registered = {op.method for op in WRITE_OPS.values()}
    missing = [
        m["method"]
        for line in DOC.read_text().splitlines()
        if (m := ROW.match(line)) and m["rw"] == "W" and m["method"] not in EXCLUDED
        if m["method"] not in registered
    ]
    assert not missing, f"write methods with no WriteOp: {missing}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_writes.py tests/test_write_coverage.py -v`
Expected: FAIL — `KeyError: 'submit_url_batch'` and the coverage test lists every
unregistered write.

- [ ] **Step 3: Write minimal implementation**

Extend `WriteOp` with a per-call cost so a batch costs what it actually spends:

```python
@dataclass(frozen=True)
class WriteOp:
    name: str
    method: str
    cost: int
    build: Callable[[dict[str, Any]], dict[str, Any]]
    summarise: Callable[[dict[str, Any]], str]
    http: str = "GET"
    variable_cost: Callable[[dict[str, Any]], int] | None = None

    def cost_for(self, args: dict[str, Any]) -> int:
        return self.variable_cost(args) if self.variable_cost else self.cost
```

Change `apply.py` to call `op.cost_for(plan.args)` in both the `limiter.check` and
`limiter.consume` calls.

Then register the rest. Two representative entries — write the remaining ones the
same way, taking each parameter name from `docs/api-surface.md`:

```python
WRITE_OPS.update(
    {
        "submit_url_batch": WriteOp(
            name="submit_url_batch",
            method="SubmitUrlBatch",
            cost=1,
            http="POST",
            variable_cost=lambda args: len(args["url_list"]),
            build=lambda args: {"siteUrl": args["site_url"], "urlList": args["url_list"]},
            summarise=lambda args: (
                f"submit {len(args['url_list'])} URLs on {args['site_url']} for recrawl"
            ),
        ),
        "remove_site": WriteOp(
            name="remove_site",
            method="RemoveSite",
            cost=1,
            build=lambda args: {"siteUrl": args["site_url"]},
            summarise=lambda args: (
                f"REMOVE {args['site_url']} from the account — verification is lost"
            ),
        ),
    }
)
```

Add a `bing-wm plan <name>` subcommand per write, following the `plan_submit_url`
shape from Task 13. For `submit_url_batch`, take `--file` with one URL per line and
check the live quota before creating the plan:

```python
@plan_group.command("submit-urls")
@click.argument("site")
@click.option("--file", "path", required=True, type=click.Path(exists=True, dir_okay=False))
@guarded
def plan_submit_urls(site: str, path: str) -> None:
    """Prepare a batch recrawl request for the URLs listed in FILE."""
    settings = _load_settings()
    site_url = normalise_site(site)
    settings.check_site_allowed(site_url)
    urls = [line.strip() for line in Path(path).read_text().splitlines() if line.strip()]
    if not urls:
        raise InvalidRequest(f"{path} contains no URLs")

    quota = run_async(_with_client(lambda c, _s: submission_ops.url_submission_quota(c, site_url)))
    remaining = quota.get("DailyQuota")
    if isinstance(remaining, int) and len(urls) > remaining:
        raise QuotaExceeded(
            f"{len(urls)} URLs requested, Bing reports {remaining} left today",
            suggestion="split the batch across days",
            details={"requested": len(urls), "daily_quota": remaining},
        )

    args = {"site_url": site_url, "url_list": urls}
    op = WRITE_OPS["submit_url_batch"]
    store = PlanStore(settings.state_dir, settings.plan_ttl_seconds)
    plan = store.create("submit_url_batch", site_url, args, op.summarise(args))
    AuditLog(settings.state_dir).record("plan_created", plan_id=plan.plan_id, operation=op.name)
    click.echo(f"{plan.plan_id}  {plan.summary}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -v` then `make lint`
Expected: all green; `test_every_write_method_is_registered` names nothing.

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/writes.py bing_webmaster_mcp/apply.py bing_webmaster_mcp/cli.py tests/test_writes.py tests/test_write_coverage.py
git commit -m "Register the remaining writes behind plans"
```

---

### Task 15: IndexNow

A different protocol on a different host with different auth. It gets its own
client rather than being bent into `BingClient`.

**Files:**
- Create: `bing_webmaster_mcp/ops/indexnow.py`, `tests/test_indexnow.py`
- Modify: `bing_webmaster_mcp/writes.py`, `bing_webmaster_mcp/apply.py`, `bing_webmaster_mcp/cli.py`

**Interfaces:**
- Produces:
  - `generate_key() -> str` — 32 hex characters, inside the documented 8–128 `a-zA-Z0-9-` alphabet
  - `validate_key(key: str) -> None` raising `InvalidRequest`
  - `key_location(host: str, key: str) -> str` — `https://{host}/{key}.txt`
  - `async verify_key_file(http, host, key, key_location=None) -> None` raising `InvalidRequest`
  - `async submit(http, host, key, urls, key_location=None) -> dict` — POST to `https://api.indexnow.org/indexnow`
  - `MAX_BATCH = 10_000`, `ENDPOINT = "https://api.indexnow.org/indexnow"`
- `apply.py` gains a branch: an op whose `method` is `"IndexNow"` is dispatched to `indexnow.submit` instead of `BingClient.call`.

- [ ] **Step 1: Write the failing test**

`tests/test_indexnow.py`:

```python
import re

import httpx
import pytest

from bing_webmaster_mcp.errors import InvalidRequest
from bing_webmaster_mcp.ops import indexnow

HOST = "a.example"
KEY = "0123456789abcdef0123456789abcdef"


def test_generated_key_matches_the_documented_alphabet():
    key = indexnow.generate_key()
    assert re.fullmatch(r"[A-Za-z0-9-]{8,128}", key)


@pytest.mark.parametrize("bad", ["short", "x" * 129, "has_underscore", "has space"])
def test_invalid_keys_are_rejected(bad):
    with pytest.raises(InvalidRequest):
        indexnow.validate_key(bad)


def test_default_key_location_is_the_site_root():
    assert indexnow.key_location(HOST, KEY) == f"https://{HOST}/{KEY}.txt"


async def test_key_file_must_contain_exactly_the_key():
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text=f"{KEY}\n"))
    async with httpx.AsyncClient(transport=transport) as http:
        await indexnow.verify_key_file(http, HOST, KEY)


async def test_wrong_key_file_contents_is_refused_before_submitting():
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text="something else"))
    async with httpx.AsyncClient(transport=transport) as http:
        with pytest.raises(InvalidRequest, match="does not contain"):
            await indexnow.verify_key_file(http, HOST, KEY)


async def test_missing_key_file_is_refused_before_submitting():
    transport = httpx.MockTransport(lambda r: httpx.Response(404))
    async with httpx.AsyncClient(transport=transport) as http:
        with pytest.raises(InvalidRequest, match="not reachable"):
            await indexnow.verify_key_file(http, HOST, KEY)


async def test_submit_posts_the_documented_body():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["json"] = request.read().decode()
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await indexnow.submit(http, HOST, KEY, [f"https://{HOST}/p"])

    assert seen["url"] == indexnow.ENDPOINT
    assert '"host": "a.example"' in seen["json"].replace('"host":"', '"host": "')
    assert result["status_code"] == 200


async def test_batch_over_the_cap_is_refused_locally():
    urls = [f"https://{HOST}/{n}" for n in range(indexnow.MAX_BATCH + 1)]
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))) as http:
        with pytest.raises(InvalidRequest, match="10000"):
            await indexnow.submit(http, HOST, KEY, urls)


async def test_urls_from_another_host_are_refused_locally():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))) as http:
        with pytest.raises(InvalidRequest, match="do not belong"):
            await indexnow.submit(http, HOST, KEY, ["https://other.example/p"])


@pytest.mark.parametrize(
    ("status", "expected"),
    [(200, "received"), (202, "accepted"), (403, "key rejected"), (422, "rejected"), (429, "rate limited")],
)
async def test_response_codes_are_explained(status, expected):
    transport = httpx.MockTransport(lambda r: httpx.Response(status))
    async with httpx.AsyncClient(transport=transport) as http:
        if status < 400:
            result = await indexnow.submit(http, HOST, KEY, [f"https://{HOST}/p"])
            assert expected in result["meaning"]
        else:
            with pytest.raises(Exception) as excinfo:
                await indexnow.submit(http, HOST, KEY, [f"https://{HOST}/p"])
            assert expected in str(excinfo.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_indexnow.py -v`
Expected: FAIL with `ImportError: cannot import name 'indexnow'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/ops/indexnow.py`:

```python
"""IndexNow: a separate protocol, not part of the Bing Webmaster Tools API.

Authentication is a key file served from the site itself, not an API key. One
submission fans out to every participating engine -- Bing, Yandex, Seznam, Naver,
Yep, Internet Archive and Amazonbot. Google does not participate and never adopted
it; say so wherever a user might assume otherwise.
"""

from __future__ import annotations

import re
import secrets
from typing import Any
from urllib.parse import urlparse

import httpx

from ...errors import InvalidRequest, RateLimited, UpstreamUnavailable

ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_BATCH = 10_000
_KEY = re.compile(r"^[A-Za-z0-9-]{8,128}$")

_MEANING = {
    200: "received",
    202: "accepted, not yet processed (normal the first time a key is used)",
}


def generate_key() -> str:
    return secrets.token_hex(16)


def validate_key(key: str) -> None:
    if not _KEY.fullmatch(key):
        raise InvalidRequest(
            "IndexNow keys are 8-128 characters of a-z, A-Z, 0-9 and '-'",
            details={"length": len(key)},
        )


def key_location(host: str, key: str) -> str:
    return f"https://{host}/{key}.txt"


async def verify_key_file(
    http: httpx.AsyncClient, host: str, key: str, location: str | None = None
) -> None:
    """Check the key file before submitting.

    A 403 from a fan-out endpoint is close to undiagnosable after the fact; this
    turns it into a sentence that names the file.
    """
    validate_key(key)
    url = location or key_location(host, key)
    try:
        response = await http.get(url, follow_redirects=True)
    except httpx.HTTPError as exc:
        raise InvalidRequest(f"key file {url} is not reachable: {exc}") from exc
    if response.status_code != 200:
        raise InvalidRequest(
            f"key file {url} is not reachable (HTTP {response.status_code})",
            suggestion="serve the key at that exact path with no authentication",
        )
    if response.text.strip() != key:
        raise InvalidRequest(
            f"key file {url} does not contain the key",
            suggestion="the file must contain the key and nothing else",
        )


async def submit(
    http: httpx.AsyncClient,
    host: str,
    key: str,
    urls: list[str],
    location: str | None = None,
) -> dict[str, Any]:
    validate_key(key)
    if len(urls) > MAX_BATCH:
        raise InvalidRequest(
            f"IndexNow accepts at most {MAX_BATCH} URLs per request, got {len(urls)}",
            suggestion="split the batch",
        )
    if not urls:
        raise InvalidRequest("no URLs to submit")
    foreign = [u for u in urls if urlparse(u).hostname != host]
    if foreign:
        raise InvalidRequest(
            f"{len(foreign)} URLs do not belong to {host}",
            details={"examples": foreign[:3]},
        )

    body = {
        "host": host,
        "key": key,
        "keyLocation": location or key_location(host, key),
        "urlList": urls,
    }
    try:
        response = await http.post(
            ENDPOINT, json=body, headers={"Content-Type": "application/json; charset=utf-8"}
        )
    except httpx.HTTPError as exc:
        raise UpstreamUnavailable(f"IndexNow: {exc}") from exc

    if response.status_code == 429:
        raise RateLimited("IndexNow rate limited this key", retry_after=None)
    if response.status_code == 403:
        raise InvalidRequest("IndexNow key rejected: the key file is invalid or unreachable")
    if response.status_code == 422:
        raise InvalidRequest("IndexNow rejected the batch: URLs not on the host, or batch too large")
    if response.status_code >= 400:
        raise InvalidRequest(f"IndexNow returned HTTP {response.status_code}")

    return {
        "submitted": len(urls),
        "status_code": response.status_code,
        "meaning": _MEANING.get(response.status_code, "accepted"),
    }
```

Register it as a write so it goes through the same review gate:

```python
"indexnow_submit": WriteOp(
    name="indexnow_submit",
    method="IndexNow",  # sentinel: apply.py dispatches this one outside BingClient
    cost=1,
    http="POST",
    variable_cost=lambda args: len(args["url_list"]),
    build=lambda args: args,
    summarise=lambda args: (
        f"submit {len(args['url_list'])} URLs for {args['host']} to IndexNow "
        "(Bing, Yandex, Seznam, Naver, Yep, Internet Archive, Amazonbot — not Google)"
    ),
),
```

In `apply.py`, before the `BingClient` branch:

```python
    if op.method == "IndexNow":
        async with httpx.AsyncClient(timeout=30.0) as http:
            await indexnow.verify_key_file(
                http, plan.args["host"], plan.args["key"], plan.args.get("key_location")
            )
            result = await indexnow.submit(
                http,
                plan.args["host"],
                plan.args["key"],
                plan.args["url_list"],
                plan.args.get("key_location"),
            )
```

Add `bing-wm indexnow key` (prints a fresh key and the file path to create) and
`bing-wm plan indexnow HOST --file urls.txt --key KEY`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_indexnow.py -v`
Expected: 15 passed

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/ops/indexnow.py bing_webmaster_mcp/writes.py bing_webmaster_mcp/apply.py bing_webmaster_mcp/cli.py tests/test_indexnow.py
git commit -m "Add IndexNow submission behind a plan"
```

---

### Task 16: The MCP server

**Files:**
- Create: `bing_webmaster_mcp/mcp_server.py`, `scripts/smoke_mcp.py`, `tests/test_mcp_server.py`
- Modify: `pyproject.toml` — add `bing-webmaster-mcp = "bing_webmaster_mcp.mcp_server:main"`

**Interfaces:**
- Consumes: every ops module, `PlanStore`, `WRITE_OPS`, `Settings`
- Produces:
  - `READ_TOOLS: dict[str, Callable]` — MCP tool name to ops coroutine
  - `build_server() -> mcp.server.Server`
  - `tool_names() -> list[str]` — every registered name, for the assertion test
  - `main() -> None` — runs stdio

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_server.py`:

```python
import pytest

from bing_webmaster_mcp import mcp_server
from bing_webmaster_mcp.writes import WRITE_OPS


def test_no_tool_applies_a_plan():
    """The security boundary, asserted.

    If this fails, the fix is to delete the tool, not to update the test. A
    confirmation an agent can send over MCP is a confirmation prompt injection can
    send.
    """
    for name in mcp_server.tool_names():
        assert "apply" not in name, f"{name} would let an agent execute a plan"


def test_every_write_has_a_plan_tool_and_no_direct_tool():
    names = set(mcp_server.tool_names())
    for op_name in WRITE_OPS:
        assert f"bing_plan_{op_name}" in names
        assert f"bing_{op_name}" not in names


def test_read_tools_are_registered():
    names = set(mcp_server.tool_names())
    for expected in (
        "bing_sites_list",
        "bing_traffic_queries",
        "bing_crawl_issues",
        "bing_url_info",
        "bing_submission_quota",
    ):
        assert expected in names


def test_plan_list_and_show_are_available_but_reject_is_not():
    names = set(mcp_server.tool_names())
    assert "bing_plan_list" in names
    assert "bing_plan_show" in names
    assert "bing_plan_reject" not in names


def test_tool_names_are_unique():
    names = mcp_server.tool_names()
    assert len(names) == len(set(names))


@pytest.mark.parametrize("name", sorted(mcp_server.READ_TOOLS))
def test_every_read_tool_maps_to_a_coroutine(name):
    import inspect

    assert inspect.iscoroutinefunction(mcp_server.READ_TOOLS[name])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mcp_server.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bing_webmaster_mcp.mcp_server'`

- [ ] **Step 3: Write minimal implementation**

`bing_webmaster_mcp/mcp_server.py` — the shape; fill in the remaining read tools
from the ops modules built in Tasks 9–11:

```python
"""stdio MCP server.

Reads are direct. Writes are not: an agent can only create a plan, and applying it
is a shell command a human runs. There is deliberately no apply tool here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .client import BingClient
from .config import Settings
from .ops import crawl, keywords, links, settings_reads, sitemaps, sites, submission, traffic
from .plans import PlanStore
from .writes import WRITE_OPS

READ_TOOLS: dict[str, Callable[..., Any]] = {
    "bing_sites_list": sites.list_sites,
    "bing_site_roles": sites.site_roles,
    "bing_site_moves": sites.site_moves,
    "bing_traffic_queries": traffic.query_stats,
    "bing_traffic_pages": traffic.page_stats,
    "bing_traffic_query": traffic.query_traffic_stats,
    "bing_traffic_page": traffic.page_query_stats,
    "bing_traffic_rank": traffic.rank_and_traffic_stats,
    "bing_url_info": crawl.url_info,
    "bing_children_url_info": crawl.children_url_info,
    "bing_crawl_stats": crawl.crawl_stats,
    "bing_crawl_issues": crawl.crawl_issues,
    "bing_crawl_settings": crawl.crawl_settings,
    "bing_fetched_urls": crawl.fetched_urls,
    "bing_link_counts": links.link_counts,
    "bing_url_links": links.url_links,
    "bing_connected_pages": links.connected_pages,
    "bing_keyword": keywords.keyword,
    "bing_keyword_stats": keywords.keyword_stats,
    "bing_related_keywords": keywords.related_keywords,
    "bing_sitemaps": sitemaps.feeds,
    "bing_sitemap_details": sitemaps.feed_details,
    "bing_blocked_urls": settings_reads.blocked_urls,
    "bing_query_parameters": settings_reads.query_parameters,
    "bing_geo_settings": settings_reads.country_region_settings,
    "bing_page_preview_blocks": settings_reads.page_preview_blocks,
    "bing_deep_link_blocks": settings_reads.deep_link_blocks,
    "bing_submission_quota": submission.url_submission_quota,
    "bing_content_submission_quota": submission.content_submission_quota,
}

PLAN_READ_TOOLS = ("bing_plan_list", "bing_plan_show")


def tool_names() -> list[str]:
    return [
        *READ_TOOLS,
        *(f"bing_plan_{name}" for name in WRITE_OPS),
        *PLAN_READ_TOOLS,
    ]
```

Then register those names with the `mcp` SDK's `Server`, each read tool calling its
coroutine inside `async with BingClient(Settings.load())`, and each
`bing_plan_<op>` tool creating a `Plan` through `PlanStore` and returning
`{"plan_id", "summary", "apply_with": f"bing-wm plan apply {plan_id}"}`.

Write tool descriptions as instructions to a model. For example, for
`bing_plan_submit_url`: *"Prepare a request for Bing to recrawl one URL. This sends
nothing — it records intent and returns a plan id a human must apply. Do not tell
the user the URL was submitted."*

`scripts/smoke_mcp.py` performs a real stdio `initialize` handshake against the
server and exits non-zero if the tool list is empty — an import check would not
catch a server that fails to start.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mcp_server.py -v` then `python scripts/smoke_mcp.py`
Expected: tests pass; the smoke script prints the tool count and exits 0

- [ ] **Step 5: Commit**

```bash
git add bing_webmaster_mcp/mcp_server.py scripts/smoke_mcp.py pyproject.toml tests/test_mcp_server.py
git commit -m "Add the stdio MCP server"
```

---

### Task 17: Documentation

Docs are load-bearing here: the README's first paragraph is what an LLM quotes when
someone asks it for a Bing MCP server, so it is a distribution asset, not decoration.

**Files:**
- Create: `llms.txt`, `CITATION.cff`, `CHANGELOG.md`, `docs/product-boundaries.md`, `docs/operations.md`, `docs/configuration.md`, `tests/test_docs.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `mcp_server.tool_names()`, `WRITE_OPS`
- Produces: documentation whose claims are checked by tests rather than trusted.

- [ ] **Step 1: Write the failing test**

`tests/test_docs.py`:

```python
from pathlib import Path

from bing_webmaster_mcp import mcp_server
from bing_webmaster_mcp.writes import WRITE_OPS

ROOT = Path(__file__).resolve().parents[1]


def test_readme_states_the_no_apply_boundary():
    text = (ROOT / "README.md").read_text().lower()
    assert "no apply tool" in text or "deliberately no apply" in text


def test_readme_says_google_does_not_participate_in_indexnow():
    # Everyone assumes it does. Saying so is the single most useful line in the file.
    text = (ROOT / "README.md").read_text().lower()
    assert "google" in text and "indexnow" in text


def test_every_write_is_documented_in_product_boundaries_or_readme():
    documented = (ROOT / "README.md").read_text() + (ROOT / "docs" / "operations.md").read_text()
    missing = [name for name in WRITE_OPS if name not in documented]
    assert not missing, f"undocumented writes: {missing}"


def test_llms_txt_exists_and_names_the_project():
    text = (ROOT / "llms.txt").read_text()
    assert "bing-webmaster-mcp" in text
    assert len(text.splitlines()) >= 5


def test_operations_doc_lists_every_mcp_tool():
    text = (ROOT / "docs" / "operations.md").read_text()
    missing = [name for name in mcp_server.tool_names() if name not in text]
    assert not missing, f"tools missing from docs/operations.md: {missing}"


def test_product_boundaries_explains_each_exclusion():
    text = (ROOT / "docs" / "product-boundaries.md").read_text()
    for excluded in ("GetDeepLinkAlgoUrls", "GetDeepLink", "UpdateDeepLink", "OAuth"):
        assert excluded in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_docs.py -v`
Expected: FAIL — `llms.txt` and `docs/product-boundaries.md` do not exist

- [ ] **Step 3: Write the documents**

`README.md` — expand the existing stub with: install, getting an API key, a
30-second example, the plan-and-apply explanation with the honest limit from
`SPEC.md` §6, the IndexNow section including the Google sentence, configuration
table, and a "Related projects" list linking `telegram-ai-cli`, `zabbix-ai-cli`,
`yandex-mcp`. First paragraph stays one or two sentences saying exactly what the
project is — that is the passage that gets quoted.

`llms.txt` — the llms.txt convention: an H1 with the project name, a one-line
blockquote summary, then linked sections pointing at `README.md`, `SPEC.md`,
`docs/operations.md` and `docs/product-boundaries.md` with one line of context each.

`docs/product-boundaries.md` — dated non-goals with reasons, at minimum: no SOAP or
POX; no Bing Search or SERP scraping; no Google Search Console or GA4; no apply tool
over MCP; the three `Obsolete` deep-link methods; OAuth2 designed for but not built;
no stored analytics or scheduler.

`docs/operations.md` — every CLI command and every MCP tool, with what each returns.

`docs/configuration.md` — every `BING_WM_*` variable, its default and its effect.

`CITATION.cff` — machine-readable attribution; GitHub surfaces a "Cite this
repository" button from it.

`CHANGELOG.md` — `## Unreleased` with what this plan built.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_docs.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add README.md llms.txt CITATION.cff CHANGELOG.md docs tests/test_docs.py
git commit -m "Add documentation and doc tests"
```

---

### Task 18: CI, packaging and the release workflow

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `constraints.txt`, `Dockerfile`, `.gitignore`, `TASKS.md`

**Interfaces:**
- Consumes: `Makefile` targets `lint` and `test`, `scripts/smoke_mcp.py`
- Produces: green CI on every push; a release triggered by a `v*` tag.

- [ ] **Step 1: Write the failing check**

There is no pytest for a workflow file, so the gate is the run itself. Before
writing them, confirm the current state is red for the right reason:

Run: `gh workflow list`
Expected: no workflows configured

- [ ] **Step 2: Write `constraints.txt` and the Dockerfile**

`constraints.txt` — exact versions, produced by `pip freeze` in a clean environment
after `pip install -e ".[test]"`, filtered to the direct and transitive runtime deps.
Header comment: *"Floors live in pyproject.toml. This file pins what CI and the
image actually install."*

`Dockerfile` — a slim Python 3.14 base, a non-root user, `pip install -c
constraints.txt .`, entrypoint `bing-webmaster-mcp`. Verify the freshest supported
Python tag at build time rather than copying a number from this plan.

- [ ] **Step 3: Write the workflows**

`.github/workflows/ci.yml` with `permissions: contents: read`, `concurrency`
cancelling superseded runs, third-party actions pinned to a commit SHA with a
comment recording the date and source of each SHA, and four jobs:

| Job | What it runs |
|---|---|
| `lint` | `make lint` |
| `test` | matrix 3.12/3.13/3.14, `pip install -c constraints.txt ".[test]"`, `make test` |
| `smoke` | `python scripts/smoke_mcp.py` — a real stdio handshake |
| `container` | builds the image and asserts `docker run --rm <img> id -u` is not `0` |

`.github/workflows/release.yml`: triggered on `v*` tags, environment `pypi`,
`permissions: id-token: write` for Trusted Publishing, and a first step that fails
if the tag does not match `project.version` in `pyproject.toml`.

`TASKS.md` — the owner-only steps that cannot be done from this checkout:
register the PyPI pending publisher (project `bing-webmaster-mcp`, owner
`stufently`, repository `bing-webmaster-mcp`, workflow `release.yml`, environment
`pypi`), create the GitHub environment `pypi`, bump the version and push the first
`v*` tag.

- [ ] **Step 4: Verify CI is green**

```bash
git push
gh run watch
```

Expected: all four jobs succeed. A red `container` job usually means the image runs
as root — fix the image, not the assertion.

- [ ] **Step 5: Commit**

```bash
git add .github constraints.txt Dockerfile .gitignore TASKS.md
git commit -m "Add CI, packaging and release workflow"
```

---

## Phase 2 — Launch and promotion

Discovery for a tool like this is now split: some people search, and some ask a
model. Both paths are worked here. Nothing in this phase ships before Phase 1 is
green — an empty or broken repo spends its one first impression badly.

### Task 19: Make the repository quotable

The first paragraph of the README and the repo description are what a model
reproduces when someone asks it for a Bing MCP server. They are the product's
copy, not its label.

- [ ] **Step 1: Write the one-sentence pitch and use it in all four places**

The same sentence goes in: the GitHub description, the README's first paragraph,
`pyproject.toml`'s `description`, and `llms.txt`'s summary line. Four different
sentences means four different quotes and no reinforcement.

```bash
gh repo edit stufently/bing-webmaster-mcp \
  --description "MCP server and CLI for Bing Webmaster Tools: traffic, indexing, crawl issues and IndexNow, with a review step on every write"
```

- [ ] **Step 2: Confirm the topics are the ones people search**

Already set at creation: `mcp`, `mcp-server`, `model-context-protocol`, `bing`,
`bing-webmaster-tools`, `seo`, `geo`, `indexnow`, `ai-search`, `claude-code`, `cli`,
`python`, `ai-tools`, `llm-tools`, `webmaster-tools`. Review once the README's pitch
is final and add anything the pitch now claims.

- [ ] **Step 3: Add the answer-shaped sections**

People ask models questions, not keywords. Give the README headings that match the
questions: *"How do I check if Bing has indexed my page?"*, *"How do I submit URLs
to Bing from the command line?"*, *"Does IndexNow work with Google?"* Each followed
by a copy-pasteable command. This is what gets extracted into an answer.

- [ ] **Step 4: Upload the social preview**

A 1280×640 PNG in Settings → General → Social preview. It is what renders when the
link is shared anywhere, including some model-generated cards. Owner step; record
it in `TASKS.md`.

- [ ] **Step 5: Commit**

```bash
git add README.md llms.txt pyproject.toml
git commit -m "Align the pitch across README, package and llms.txt"
```

### Task 20: Ship the package and register the server

Distribution identity matters more than the repo name: PyPI and the MCP registry
are what `uvx` and MCP clients resolve.

- [ ] **Step 1: First release**

Owner steps from `TASKS.md`: pending publisher on PyPI, GitHub environment `pypi`,
then bump `project.version` and push `v0.1.0`. Confirm the package page renders the
README and that `keywords` and `[project.urls]` are populated — that page is
indexed independently of GitHub.

- [ ] **Step 2: Register in the official MCP registry**

Publish through `mcp-publisher` to `registry.modelcontextprotocol.io`. The namespace
binds to a verified GitHub account, so publish under the same account that owns the
repo. For a PyPI package the registry expects an `mcp-name` line in the README.

- [ ] **Step 3: Submit to the community catalogues**

One PR each to `punkpeye/awesome-mcp-servers` and the other awesome-MCP lists, plus
listings on `mcpservers.org` and `glama.ai/mcp`. These are where developers browse
rather than search.

- [ ] **Step 4: Verify installability from a clean machine**

```bash
docker run --rm python:3.14-slim sh -c "pip install bing-webmaster-mcp && bing-wm --help"
```

Expected: help text. A package that imports in the author's checkout but not in a
clean container is the classic first-release failure.

- [ ] **Step 5: Record what shipped**

```bash
git add CHANGELOG.md TASKS.md
git commit -m "Record the first release"
```

### Task 21: Cross-link the family

A small connected set of tools by one author is a stronger signal than four
unrelated repos — for search and for a model deciding whether an author is real.

- [ ] **Step 1: Add a "Related projects" section to this README** linking
`telegram-ai-cli`, `zabbix-ai-cli`, `yandex-mcp` and `gpt-web-gateway`, one line each
on what it does.

- [ ] **Step 2: Add the reverse link** to each of those four repos' READMEs, in the
same section. Per the house rule about working in other repositories, update each
repo's own `CHANGELOG.md` in the same commit.

- [ ] **Step 3: Position against the neighbours honestly.** In the README, name
`search-console-mcp` as the right choice for someone who wants Google plus Bing in
one tool, and say what this one does that it does not: complete Bing coverage and a
review step on writes. A comparison a reader can verify is worth more than a claim
they cannot.

- [ ] **Step 4: Commit** in each repository separately, since they push to different
remotes.

### Task 22: Write the launch content

- [ ] **Step 1: A Habr article.** Not a release announcement — the interesting story
is the reporting: the Bing Search API is dead, Bing Webmaster Tools is alive and
free, and Bing is what ChatGPT search reads. That is news to most readers, and the
tool follows from it rather than leading. Use the existing Habr pipeline in
`dailywork/`.

- [ ] **Step 2: Reddit.** `r/mcp` and `r/ClaudeAI`. Lead with the plan-and-apply
idea, not the tool — "I did not want an agent submitting URLs to Bing on its own"
is a discussion; "I made a thing" is not.

- [ ] **Step 3: A demo recording.** Thirty seconds: ask an agent which pages Bing
has not indexed, then plan a submission and apply it in the terminal. The review
step is the whole point and it is visual.

- [ ] **Step 4: Answer existing questions.** Search for people already asking how to
reach Bing Webmaster Tools from an agent, and answer with the command rather than
the link. The answer earns the click.

- [ ] **Step 5: Product Hunt** — only if the first release lands well. A launch on an
unproven tool spends the slot for nothing.

### Task 23: Measure, using the tool itself

The project can watch its own visibility, which is also the most honest demo there is.

- [ ] **Step 1: Add the repo and PyPI pages to Bing Webmaster Tools** once they exist.

- [ ] **Step 2: Baseline** — record impressions and clicks from
`bing-wm traffic rank` on the launch day.

- [ ] **Step 3: Ask the models directly.** Every few weeks, ask ChatGPT, Claude and
Perplexity "what MCP server should I use for Bing Webmaster Tools?" and record
whether this project is named. That answer is the actual objective; stars are a
proxy for it.

- [ ] **Step 4: Feed the result back into the README.** If the models describe the
project wrongly, the first paragraph is wrong — rewrite it and re-check. The pitch
is a hypothesis, and this is the test.

- [ ] **Step 5: Set a review date** rather than trusting memory: a reminder at 30
days to repeat steps 2–4.

---

## Self-review

Checked against `SPEC.md` after writing:

**Spec coverage.** §1 identity → Tasks 17 and 19. §2 non-goals → Task 17's
`product-boundaries.md`, with `test_product_boundaries_explains_each_exclusion`
enforcing it. §3 transport, auth and both traps → Tasks 4, 5 and 6. §4 method
surface → Task 2, with the count conflict as its explicit deliverable, and coverage
gates in Tasks 11 and 14. §5 architecture → the file-structure table; `render.py`
→ Task 7; error taxonomy → Task 3. §6 plan-and-apply → Task 13, asserted in Task 16.
§7 CLI and MCP surface → Tasks 8–11, 16. §8 IndexNow → Task 15. §9 quotas → Tasks 12
and 14 (the live-quota check before a batch). §10 packaging → Tasks 1 and 18. §11
tests → every task. §12 CI → Task 18. §13 build order → Tasks 1–18 follow it. §14
open questions → carried into Task 2's step 3 and Task 14's parameter sourcing.

One gap found and closed while reviewing: the spec requires refusing a batch larger
than the remaining quota, and the original Task 14 had no step for it — the live
`GetUrlSubmissionQuota` check is now in `plan_submit_urls`.

**Placeholder scan.** No "TBD", no "add error handling", no "similar to Task N".
Task 11 and Task 14 delegate the repetitive tail to a named pattern plus a
coverage test that fails if the tail is skipped, which is a gate rather than a
placeholder. Tasks 17–23 are documentation and distribution work, where the steps
are the deliverable and code blocks would be fabrication.

**Type consistency.** `normalise_site` is used under that name in Tasks 8–14.
`fetch(client, method, params, *, body)` is unchanged from Task 8 onward.
`WriteOp.cost_for(args)` is introduced in Task 14 and `apply.py` is explicitly
updated in the same task to use it rather than `op.cost`. `PlanStore.set_expiry`
is used by `tests/test_apply.py` and is defined in Task 13's `plans.py`. The MCP
tool names asserted in Task 16 match the names listed in `SPEC.md` §7.

