"""Test-wide safety fixtures."""

from __future__ import annotations

import os
import socket

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail loudly instead of allowing a unit test to reach the internet."""

    def guard(*args: object, **kwargs: object) -> None:
        raise RuntimeError("network access is not allowed in tests")

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket.socket, "connect_ex", guard)


@pytest.fixture(autouse=True)
def clean_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's own BING_WM_* variables out of every test.

    Settings reads the environment for any field a test does not override, so an
    exported denylist or state directory would otherwise change what the suite asserts.
    """
    for name in [key for key in os.environ if key.startswith("BING_WM_")]:
        monkeypatch.delenv(name, raising=False)
