import sys
from pathlib import Path

import anyio
import pytest
from mcp import Client, StdioServerParameters

from ari.mcp.server import create_server


@pytest.mark.anyio
async def test_mcp_exposes_only_foundation_tools():
    async with Client(create_server(), raise_exceptions=True) as client:
        result = await client.list_tools()
        assert {tool.name for tool in result.tools} == {"get_project_status", "list_capabilities"}
        for tool in result.tools:
            assert tool.annotations.read_only_hint is True
            assert tool.annotations.destructive_hint is False
            assert tool.input_schema.get("properties", {}) == {}
        status = await client.call_tool("get_project_status", {})
        assert not status.is_error
        assert status.structured_content["phase"] == 2
        assert status.structured_content["device_access"] is False
        assert status.structured_content["adb_read_only_available"] is True
        assert status.structured_content["codex_connection"] == "not_verified"
        catalog = await client.call_tool("list_capabilities", {})
        items = catalog.structured_content["capabilities"]
        assert next(item for item in items if item["name"] == "detect_devices")["status"] == (
            "implemented"
        )
        assert all(item["status"] == "not_implemented" for item in items if item["phase"] > 2)
        assert all(item["mcp_registered"] is False for item in items if item["phase"] == 2)


@pytest.mark.anyio
async def test_unimplemented_and_shell_tools_cannot_be_called():
    async with Client(create_server(), raise_exceptions=True) as client:
        for name in ("detect_devices", "unlock", "execute_shell"):
            result = await client.call_tool(name, {})
            assert result.is_error is True


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
    assert (data_dir / "ari.sqlite3").is_file()
    assert (data_dir / "logs" / "ari.jsonl").is_file()
