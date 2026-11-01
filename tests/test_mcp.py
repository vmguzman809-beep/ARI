import json
import sys
from pathlib import Path
from unittest.mock import Mock

import anyio
import pytest
from mcp import Client, StdioServerParameters

from ari.device.errors import AdbError, AdbErrorCode
from ari.device.inspector import AdbDeviceInspector
from ari.mcp.server import create_server

TOOLS = {
    "get_project_status",
    "list_capabilities",
    "detect_devices",
    "inspect_adb_status",
    "get_device_properties",
    "inspect_device",
}
TARGETED = ("inspect_adb_status", "get_device_properties", "inspect_device")
CONSENT = {"authorized": True, "simulation": False}


@pytest.mark.anyio
async def test_mcp_exposes_only_six_read_only_tools_with_closed_schemas():
    async with Client(create_server(), raise_exceptions=True) as client:
        result = await client.list_tools()
        assert {tool.name for tool in result.tools} == TOOLS
        for tool in result.tools:
            assert tool.annotations.read_only_hint is True
            assert tool.annotations.destructive_hint is False
            assert tool.input_schema["additionalProperties"] is False
            assert tool.output_schema
            if tool.name in TARGETED:
                assert tool.input_schema["required"] == ["serial"]
                assert tool.input_schema["properties"]["serial"]["pattern"]
            if tool.name not in {"get_project_status", "list_capabilities"}:
                assert tool.input_schema["properties"]["authorized"]["default"] is False
                assert tool.input_schema["properties"]["simulation"]["default"] is True
        status = await client.call_tool("get_project_status", {})
        assert not status.is_error
        assert status.structured_content["phase"] == 3
        assert status.structured_content["device_access"] is False
        assert status.structured_content["adb_read_only_available"] is True
        assert status.structured_content["codex_connection"] == "verify_on_client"
        catalog = await client.call_tool("list_capabilities", {})
        items = catalog.structured_content["capabilities"]
        assert next(item for item in items if item["name"] == "detect_devices")["status"] == (
            "implemented"
        )
        assert all(item["status"] == "not_implemented" for item in items if item["phase"] > 2)
        assert all(item["mcp_registered"] is True for item in items if item["phase"] == 2)


@pytest.mark.anyio
async def test_unimplemented_and_shell_tools_cannot_be_called():
    async with Client(create_server(), raise_exceptions=True) as client:
        for name in ("unlock", "execute_shell", "reboot", "flash", "erase", "root"):
            result = await client.call_tool(name, {})
            assert result.is_error is True
            assert result.structured_content["error"]["code"] == "unknown_tool"


@pytest.mark.stdio
@pytest.mark.anyio
async def test_stdio_entrypoint_uses_isolated_storage(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    data_dir = tmp_path / "MCP datos ñ con espacios"
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ari.mcp.server"],
        cwd=str(project_root),
        env={"ARI_DATA_DIR": str(data_dir)},
    )
    with anyio.fail_after(20):
        async with Client(parameters) as client:
            result = await client.call_tool("get_project_status", {})
            assert not result.is_error
            assert result.structured_content["device_access"] is False
            error = await client.call_tool("detect_devices", {})
            assert error.structured_content["error"]["code"] == "authorization_required"
    assert (data_dir / "ari.sqlite3").is_file()
    assert (data_dir / "logs" / "ari.jsonl").is_file()
    events = [
        json.loads(line)["event"]
        for line in (data_dir / "logs" / "ari.jsonl").read_text().splitlines()
    ]
    assert events == ["runtime_started", "runtime_stopped"]


@pytest.mark.anyio
@pytest.mark.parametrize("legacy", [False, True])
async def test_all_read_apis_return_typed_results_with_mock_transport(
    mock_adb_transport, repository, legacy
):
    inspector = AdbDeviceInspector(mock_adb_transport, repository=repository)
    factory = Mock(return_value=inspector)
    async with Client(
        create_server(inspector_factory=factory), **({"mode": "legacy"} if legacy else {})
    ) as client:
        inventory = await client.call_tool("detect_devices", CONSENT)
        assert not inventory.is_error
        assert inventory.structured_content["devices"][0]["serial"] == "SYNTHETIC-1"
        for name in TARGETED:
            result = await client.call_tool(name, {"serial": "SYNTHETIC-1", **CONSENT})
            assert not result.is_error
            if name == "inspect_device":
                snapshot = result.structured_content["snapshot"]
                assert snapshot["identity"]["manufacturer"] == "Synthetic OEM"
            else:
                assert result.structured_content["serial"] == "SYNTHETIC-1"
        # A successful call does not authorize the next call.
        denied = await client.call_tool("inspect_device", {"serial": "SYNTHETIC-1"})
        assert denied.structured_content["error"]["code"] == "authorization_required"
    assert factory.call_count == 4


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("arguments", "code"),
    [
        ({}, "authorization_required"),
        ({"authorized": True}, "simulation_enabled"),
        ({"authorized": False, "simulation": False}, "authorization_required"),
    ],
)
async def test_defaults_never_construct_backend(arguments, code):
    factory = Mock()
    async with Client(create_server(inspector_factory=factory)) as client:
        result = await client.call_tool("detect_devices", arguments)
        assert result.is_error
        assert result.structured_content["error"]["code"] == code
    factory.assert_not_called()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("inspect_device", {}),
        ("inspect_device", {"serial": None}),
        ("inspect_device", {"serial": "PRIVATE;reboot"}),
        ("inspect_device", {"serial": " PRIVATE "}),
        ("detect_devices", {"authorized": "true"}),
        ("detect_devices", {"simulation": 0}),
        ("get_project_status", {"PRIVATE_SECRET_FIELD": "PRIVATE_VALUE"}),
        ("inspect_device", {"serial": "PRIVATE", "command": "PRIVATE_COMMAND"}),
        ("get_device_properties", {"serial": "PRIVATE", "executable": "PRIVATE_PATH"}),
    ],
)
async def test_invalid_inputs_are_safe_before_backend_or_sdk_logging(
    tool, arguments, caplog, capsys
):
    factory = Mock()
    async with Client(create_server(inspector_factory=factory)) as client:
        result = await client.call_tool(tool, arguments)
        assert result.is_error
        assert result.structured_content["error"]["code"] == "invalid_arguments"
        assert "PRIVATE" not in result.model_dump_json()
    factory.assert_not_called()
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err + caplog.text


@pytest.mark.anyio
async def test_returning_another_serial_is_rejected(mock_adb_transport):
    inspector = AdbDeviceInspector(mock_adb_transport)
    wrong = inspector.inspect_device("SYNTHETIC-1")
    backend = Mock()
    backend.inspect_device.return_value = wrong
    async with Client(create_server(inspector_factory=lambda _: backend)) as client:
        result = await client.call_tool("inspect_device", {"serial": "SYNTHETIC-OTHER", **CONSENT})
        assert result.is_error
        assert result.structured_content["error"]["code"] == "device_changed"


def test_startup_errors_are_static_and_do_not_leak(monkeypatch, capsys):
    from ari.mcp import server

    monkeypatch.setattr(server, "AriRuntime", Mock(side_effect=RuntimeError("PRIVATE_PATH")))
    with pytest.raises(SystemExit) as caught:
        server.main()
    assert caught.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "ARI MCP: startup_or_lifecycle_failed\n"


@pytest.mark.anyio
@pytest.mark.parametrize("code", list(AdbErrorCode))
async def test_domain_failures_preserve_only_safe_codes(code, caplog, capsys):
    inspector = Mock()
    inspector.inspect_device.side_effect = AdbError(code)
    async with Client(create_server(inspector_factory=lambda _: inspector)) as client:
        result = await client.call_tool("inspect_device", {"serial": "PRIVATE", **CONSENT})
        assert result.is_error
        assert result.structured_content["error"]["code"] == code.value
        assert "PRIVATE" not in result.model_dump_json()
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err + caplog.text


@pytest.mark.anyio
async def test_unexpected_backend_exception_and_invalid_output_do_not_leak(caplog, capsys):
    inspector = Mock()
    inspector.inspect_device.side_effect = RuntimeError("PRIVATE SERIAL AND PATH")
    async with Client(create_server(inspector_factory=lambda _: inspector)) as client:
        result = await client.call_tool("inspect_device", {"serial": "PRIVATE", **CONSENT})
        assert result.structured_content["error"]["code"] == "internal_error"
        inspector.inspect_device.side_effect = None
        inspector.inspect_device.return_value = "PRIVATE INVALID OUTPUT"
        other = await client.call_tool("inspect_device", {"serial": "PRIVATE", **CONSENT})
        assert other.structured_content["error"]["code"] == "internal_error"
        assert "PRIVATE" not in result.model_dump_json() + other.model_dump_json()
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err + caplog.text
