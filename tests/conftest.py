import os
import subprocess
import sys
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from ari.core.models import SourceReference
from ari.device.adb import AdbReadOperation, AdbReadTransport, DeviceProperty
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


@pytest.fixture
def adb_executable(tmp_path):
    directory = tmp_path / "platform tools ñ"
    directory.mkdir()
    executable = directory / ("adb.exe" if os.name == "nt" else "adb")
    executable.write_bytes(b"synthetic mock file; never execute")
    return executable


@pytest.fixture
def adb_values():
    return {
        DeviceProperty.MANUFACTURER: "Synthetic OEM",
        DeviceProperty.MODEL: "Test Phone",
        DeviceProperty.DEVICE: "test_codename",
        DeviceProperty.PRODUCT_NAME: "test_product",
        DeviceProperty.HARDWARE_SKU: "TEST-A",
        DeviceProperty.ODM_SKU: "TEST-ODM-1",
        DeviceProperty.BUILD_ID: "TEST.BUILD.1",
        DeviceProperty.FINGERPRINT: "synthetic/test/device:1/build/release",
        DeviceProperty.ANDROID_RELEASE: "test-only",
        DeviceProperty.SDK_LEVEL: "999",
        DeviceProperty.ABI_LIST: "arm64-v8a,armeabi-v7a",
        DeviceProperty.CPU_ABI: "arm64-v8a",
    }


@pytest.fixture
def mock_adb_transport(adb_values):
    transport = Mock(spec=AdbReadTransport)

    def respond(request):
        if request.operation == AdbReadOperation.DEVICES:
            return (
                "List of devices attached\n"
                "SYNTHETIC-1 device product:test_product model:Inventory_Hint "
                "device:test_codename transport_id:1\n"
            )
        if request.operation == AdbReadOperation.STATE:
            return "device\n"
        return adb_values[request.property] + "\n"

    transport.execute.side_effect = respond
    return transport
