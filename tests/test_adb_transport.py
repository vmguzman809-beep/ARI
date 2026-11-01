import os
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from ari.device.adb import AdbReadOperation, AdbRequest, DeviceProperty
from ari.device.errors import AdbError, AdbErrorCode
from ari.device.inspector import AdbDeviceInspector
from integrations.adb.transport import AdbSubprocessTransport, resolve_adb_executable


@pytest.fixture
def process_mock(monkeypatch):
    process = Mock(return_value=subprocess.CompletedProcess([], 0, b"device\n", b""))
    monkeypatch.setattr("integrations.adb.transport.subprocess.run", process)
    return process


@pytest.mark.parametrize(
    ("authorized", "simulation", "code"),
    [
        (False, True, AdbErrorCode.AUTHORIZATION_REQUIRED),
        (False, False, AdbErrorCode.AUTHORIZATION_REQUIRED),
        (True, True, AdbErrorCode.SIMULATION_ENABLED),
    ],
)
def test_default_or_unapproved_transport_starts_no_process(
    process_mock, authorized, simulation, code
):
    transport = AdbSubprocessTransport(authorized=authorized, simulation=simulation)
    with pytest.raises(AdbError) as caught:
        transport.execute(AdbRequest(operation=AdbReadOperation.DEVICES))
    assert caught.value.code == code
    process_mock.assert_not_called()


@pytest.mark.parametrize("property", list(DeviceProperty))
def test_only_fixed_property_commands_reach_process(
    adb_executable, process_mock, property, monkeypatch
):
    monkeypatch.setenv("ADB_TRACE", "all")
    monkeypatch.setenv("ADB_SERVER_SOCKET", "tcp:untrusted.example:1234")
    monkeypatch.setenv("ANDROID_SERIAL", "WRONG-TARGET")
    monkeypatch.setenv("SECRET_TEST_TOKEN", "not-a-real-secret")
    transport = AdbSubprocessTransport(adb_executable, authorized=True, simulation=False)
    transport.execute(
        AdbRequest(operation=AdbReadOperation.PROPERTY, serial="SYNTHETIC-1", property=property)
    )
    args, kwargs = process_mock.call_args
    assert args[0] == [
        str(adb_executable),
        "-H",
        "127.0.0.1",
        "-P",
        "5037",
        "-s",
        "SYNTHETIC-1",
        "shell",
        "-T",
        "getprop",
        property.value,
    ]
    assert kwargs["shell"] is False
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["capture_output"] is True
    assert kwargs["timeout"] == 5.0
    assert kwargs["cwd"] == str(adb_executable.parent)
    assert kwargs["creationflags"] == (subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    for key in ("ADB_TRACE", "ADB_SERVER_SOCKET", "ANDROID_SERIAL", "SECRET_TEST_TOKEN"):
        assert key not in kwargs["env"]


def test_inventory_and_state_commands_are_bounded(adb_executable, process_mock):
    transport = AdbSubprocessTransport(adb_executable, authorized=True, simulation=False)
    transport.execute(AdbRequest(operation=AdbReadOperation.DEVICES))
    assert process_mock.call_args.args[0][5:] == ["devices", "-l"]
    transport.execute(AdbRequest(operation=AdbReadOperation.STATE, serial="SYNTHETIC-1"))
    assert process_mock.call_args.args[0][5:] == ["-s", "SYNTHETIC-1", "get-state"]


@pytest.mark.parametrize(
    "operation",
    [
        "reboot",
        "root",
        "unroot",
        "remount",
        "push",
        "install",
        "uninstall",
        "sideload",
        "flash",
        "erase",
        "unlock",
        "tcpip",
        "connect",
        "pair",
        "reconnect",
        "kill-server",
        "shell",
    ],
)
def test_mutating_or_free_commands_have_no_request_interface(operation, process_mock):
    with pytest.raises(ValidationError):
        AdbRequest(operation=operation, serial="SYNTHETIC-1")
    process_mock.assert_not_called()


@pytest.mark.parametrize(
    "data",
    [
        {"operation": "property", "serial": "SYNTH", "property": "persist.sys.anything"},
        {"operation": "property", "serial": "SYNTH", "property": "ro.product.model; reboot"},
        {"operation": "state"},
        {"operation": "devices", "serial": "SYNTH"},
        {"operation": "state", "serial": "SYNTH", "property": "ro.product.model"},
        {"operation": "devices", "argv": ["root"]},
    ],
)
def test_invalid_requests_stop_before_process(data, process_mock):
    with pytest.raises(ValidationError):
        AdbRequest.model_validate(data)
    process_mock.assert_not_called()


def test_forged_models_and_raw_argv_are_revalidated(adb_executable, process_mock):
    transport = AdbSubprocessTransport(adb_executable, authorized=True, simulation=False)
    for request in (
        ["reboot"],
        AdbRequest.model_construct(operation="root", serial="SYNTH"),
        AdbRequest.model_construct(operation=AdbReadOperation.STATE, serial="--reboot"),
    ):
        with pytest.raises(AdbError) as caught:
            transport.execute(request)
        assert caught.value.code == AdbErrorCode.INVALID_REQUEST
    process_mock.assert_not_called()


@pytest.mark.parametrize("timeout", [0, -1, 11, float("inf"), float("nan"), True, "5", None])
def test_invalid_timeout_cannot_start_a_process(timeout, process_mock):
    with pytest.raises(ValueError):
        AdbSubprocessTransport(timeout_seconds=timeout)
    process_mock.assert_not_called()


@pytest.mark.parametrize(
    ("exception", "code"),
    [
        (
            subprocess.TimeoutExpired(["private-serial"], 1, output=b"private-data"),
            AdbErrorCode.TIMEOUT,
        ),
        (FileNotFoundError("private-path"), AdbErrorCode.TOOL_NOT_FOUND),
        (PermissionError("private-path"), AdbErrorCode.ACCESS_DENIED),
        (OSError("private-path"), AdbErrorCode.COMMAND_FAILED),
    ],
)
def test_process_exceptions_are_sanitized(adb_executable, process_mock, exception, code, capsys):
    process_mock.side_effect = exception
    transport = AdbSubprocessTransport(adb_executable, authorized=True, simulation=False)
    with pytest.raises(AdbError) as caught:
        transport.execute(AdbRequest(operation=AdbReadOperation.STATE, serial="SYNTH"))
    assert caught.value.code == code
    assert "private" not in str(caught.value)
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ("device unauthorized", AdbErrorCode.DEVICE_UNAUTHORIZED),
        ("device offline", AdbErrorCode.DEVICE_OFFLINE),
        ("more than one device/emulator", AdbErrorCode.AMBIGUOUS_TARGET),
        ("no devices/emulators found", AdbErrorCode.NO_DEVICES),
        ("device 'PRIVATE' not found", AdbErrorCode.DEVICE_NOT_FOUND),
        ("device disconnected", AdbErrorCode.DEVICE_NOT_FOUND),
        ("no permissions", AdbErrorCode.ACCESS_DENIED),
        ("cannot connect to daemon", AdbErrorCode.SERVER_UNAVAILABLE),
        ("unexpected PRIVATE details", AdbErrorCode.COMMAND_FAILED),
    ],
)
def test_nonzero_exit_is_not_reported_as_empty_inventory(
    adb_executable, process_mock, message, code
):
    process_mock.return_value = subprocess.CompletedProcess([], 1, b"", message.encode())
    transport = AdbSubprocessTransport(adb_executable, authorized=True, simulation=False)
    with pytest.raises(AdbError) as caught:
        transport.execute(AdbRequest(operation=AdbReadOperation.DEVICES))
    assert caught.value.code == code
    assert "PRIVATE" not in str(caught.value)


@pytest.mark.parametrize("output", [b"x" * 65_537, b"\xff\xfe"])
def test_oversized_or_non_utf8_responses_stop(adb_executable, process_mock, output):
    process_mock.return_value = subprocess.CompletedProcess([], 0, output, b"")
    with pytest.raises(AdbError) as caught:
        AdbSubprocessTransport(adb_executable, authorized=True, simulation=False).execute(
            AdbRequest(operation=AdbReadOperation.DEVICES)
        )
    assert caught.value.code == AdbErrorCode.INVALID_RESPONSE


def test_only_known_host_startup_notices_are_accepted(adb_executable, process_mock):
    process_mock.return_value = subprocess.CompletedProcess(
        [],
        0,
        b"List of devices attached\n",
        b"* daemon not running; starting now at tcp:5037\n* daemon started successfully\n",
    )
    transport = AdbSubprocessTransport(adb_executable, authorized=True, simulation=False)
    assert transport.execute(AdbRequest(operation=AdbReadOperation.DEVICES)).startswith("List of")
    process_mock.return_value = subprocess.CompletedProcess(
        [], 0, b"", b"permission denied PRIVATE"
    )
    with pytest.raises(AdbError) as caught:
        transport.execute(AdbRequest(operation=AdbReadOperation.DEVICES))
    assert caught.value.code == AdbErrorCode.ACCESS_DENIED


def test_tool_resolution_is_explicit_and_does_not_run_adb(
    adb_executable, process_mock, monkeypatch
):
    assert resolve_adb_executable(adb_executable) == adb_executable
    which = Mock(return_value=str(adb_executable))
    monkeypatch.setattr("integrations.adb.transport.shutil.which", which)
    monkeypatch.setenv("PATH", str(adb_executable.parent))
    assert resolve_adb_executable() == adb_executable
    assert which.call_args.args == (str(adb_executable),)
    which.return_value = None
    with pytest.raises(AdbError) as caught:
        resolve_adb_executable()
    assert caught.value.code == AdbErrorCode.TOOL_NOT_FOUND
    process_mock.assert_not_called()


def test_path_resolution_ignores_cwd_and_relative_entries(
    adb_executable, process_mock, monkeypatch
):
    monkeypatch.chdir(adb_executable.parent)
    monkeypatch.setenv("PATH", os.pathsep.join(["", ".", "relative-tools"]))
    which = Mock(return_value=str(adb_executable))
    monkeypatch.setattr("integrations.adb.transport.shutil.which", which)
    with pytest.raises(AdbError) as caught:
        resolve_adb_executable()
    assert caught.value.code == AdbErrorCode.TOOL_NOT_FOUND
    which.assert_not_called()
    process_mock.assert_not_called()


@pytest.mark.parametrize("name", ["adb.cmd", "adb.bat", "adb.ps1", "fastboot.exe"])
def test_wrappers_and_other_binaries_are_not_executables(tmp_path, name, process_mock):
    path = tmp_path / name
    path.write_text("synthetic fixture", encoding="utf-8")
    with pytest.raises(AdbError) as caught:
        resolve_adb_executable(path)
    assert caught.value.code == AdbErrorCode.INVALID_EXECUTABLE
    process_mock.assert_not_called()


def test_relative_and_missing_executables_are_rejected(tmp_path, process_mock):
    with pytest.raises(AdbError) as caught:
        resolve_adb_executable(Path("adb.exe"))
    assert caught.value.code == AdbErrorCode.INVALID_EXECUTABLE
    missing = tmp_path / ("adb.exe" if os.name == "nt" else "adb")
    with pytest.raises(AdbError) as caught:
        resolve_adb_executable(missing)
    assert caught.value.code == AdbErrorCode.TOOL_NOT_FOUND
    process_mock.assert_not_called()


def test_full_diagnosis_through_mocked_process_boundary(adb_executable, process_mock, adb_values):
    def respond(argv, **kwargs):
        assert kwargs["shell"] is False
        if argv[5:] == ["devices", "-l"]:
            stdout = "List of devices attached\nSYNTHETIC-1 device\nSYNTHETIC-2 offline\n"
        elif argv[5:] == ["-s", "SYNTHETIC-1", "get-state"]:
            stdout = "device\n"
        else:
            assert argv[5:10] == ["-s", "SYNTHETIC-1", "shell", "-T", "getprop"]
            stdout = adb_values[DeviceProperty(argv[10])] + "\n"
        return subprocess.CompletedProcess(argv, 0, stdout.encode(), b"")

    process_mock.side_effect = respond
    inspector = AdbDeviceInspector(
        AdbSubprocessTransport(adb_executable, authorized=True, simulation=False)
    )
    result = inspector.inspect_device("SYNTHETIC-1")
    assert result.snapshot.identity.manufacturer == "Synthetic OEM"
    assert result.snapshot.serial == "SYNTHETIC-1"
    assert process_mock.call_count == len(DeviceProperty) + 4
