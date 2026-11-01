import os
import subprocess
import sys
from datetime import UTC, datetime

import pytest

from ari.core.models import SourceReference
from ari.device.models import DeviceIdentity
from ari.knowledge.database import Database
from ari.knowledge.repository import KnowledgeRepository


@pytest.fixture(autouse=True)
def block_external_commands(monkeypatch, request):
    """No test can accidentally use ADB/Fastboot from the machine's PATH."""
    original_popen = subprocess.Popen

    def guarded_popen(args, *positional, **kwargs):
        permitted = (
            request.node.get_closest_marker("stdio") is not None
            and isinstance(args, (tuple, list))
            and list(args) == [sys.executable, "-m", "ari.mcp.server"]
            and not kwargs.get("shell", False)
        )
        if not permitted:
            raise AssertionError(f"External process forbidden in tests: {args!r}")
        return original_popen(args, *positional, **kwargs)

    def forbidden_system(*_args, **_kwargs):
        raise AssertionError("Shell commands are forbidden in tests")

    monkeypatch.setattr(subprocess, "Popen", guarded_popen)
    monkeypatch.setattr(os, "system", forbidden_system)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def identity():
    return DeviceIdentity(
        manufacturer="Synthetic OEM",
        model="Test Phone",
        variant="TEST-A",
        build_fingerprint="synthetic/test-a/build:1/release",
        android_version="test-only",
        architecture="arm64-v8a",
    )


@pytest.fixture
def source():
    return SourceReference(
        title="Synthetic fixture, not compatibility evidence",
        url="https://example.invalid/ari-test",
        verified_at=datetime(2026, 10, 31, tzinfo=UTC),
    )


@pytest.fixture
def database(tmp_path):
    db = Database(tmp_path / "pruebas con espacios ñ" / "ari.sqlite3")
    db.initialize()
    yield db
    db.close()


@pytest.fixture
def repository(database):
    return KnowledgeRepository(database)
