"""Optional local daily write ceiling with restart-persistent counters.

This is operator policy, not a Bing quota. The default is disabled so the project never
hardcodes a quota; submission quotas always come from Bing itself.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .errors import QuotaExceeded


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


class RateLimiter:
    def __init__(self, state_dir: Path, *, max_per_day: int | None) -> None:
        directory = Path(state_dir)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._path = directory / "limits.sqlite3"
        self._max = max_per_day
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        self._path.chmod(0o600)
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS usage "
                "(day TEXT NOT NULL, key TEXT NOT NULL, count INTEGER NOT NULL, "
                "PRIMARY KEY (day, key))"
            )

    def _used(self, connection: sqlite3.Connection, key: str) -> int:
        row = connection.execute(
            "SELECT count FROM usage WHERE day = ? AND key = ?", (_today(), key)
        ).fetchone()
        return int(row[0]) if row else 0

    def check(self, key: str, cost: int = 1) -> None:
        if cost < 0:
            raise ValueError("cost must be non-negative")
        if self._max is None:
            return
        with self._connect() as connection:
            used = self._used(connection, key)
        if used + cost > self._max:
            raise QuotaExceeded(
                f"local daily write limit reached for {key}: {used}/{self._max}",
                suggestion="change BING_WM_MAX_WRITES_PER_DAY or wait for the UTC day rollover",
                details={"used": used, "requested": cost, "local_max": self._max},
            )

    def consume(self, key: str, cost: int = 1) -> None:
        if cost < 0:
            raise ValueError("cost must be non-negative")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            used = self._used(connection, key)
            if self._max is not None and used + cost > self._max:
                raise QuotaExceeded(
                    f"local daily write limit reached for {key}: {used}/{self._max}",
                    details={"used": used, "requested": cost, "local_max": self._max},
                )
            connection.execute(
                "INSERT INTO usage(day, key, count) VALUES (?, ?, ?) "
                "ON CONFLICT(day, key) DO UPDATE SET count = excluded.count",
                (_today(), key, used + cost),
            )
