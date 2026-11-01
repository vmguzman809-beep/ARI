from unittest.mock import Mock

import pytest
from mcp import Client

from ari.core.models import utc_now
from ari.mcp.server import create_server

RESEARCH_TOOLS = ("analyze_unlock_compatibility", "check_root_compatibility", "create_root_plan")


@pytest.mark.anyio
@pytest.mark.parametrize("legacy", [False, True])
async def test_research_tools_never_construct_device_backend(identity, legacy):
    factory = Mock(side_effect=AssertionError("Hardware forbidden"))
    async with Client(
        create_server(inspector_factory=factory), **({"mode": "legacy"} if legacy else {})
    ) as client:
        arguments = {"research": {"target": {"identity": identity.model_dump(mode="json")}}}
        assessment = await client.call_tool("analyze_unlock_compatibility", arguments)
        report = await client.call_tool("check_root_compatibility", arguments)
        plan = await client.call_tool("create_root_plan", arguments)
        assert not assessment.is_error and not report.is_error and not plan.is_error
        assert assessment.structured_content["unlock_capability"] == "unverified"
        assert report.structured_content["blockers"]
        assert plan.structured_content["executable"] is False
    factory.assert_not_called()


@pytest.mark.anyio
@pytest.mark.parametrize("tool", RESEARCH_TOOLS)
@pytest.mark.parametrize(
    "field", ["shell", "command", "backend", "executable", "path", "authorized", "serial"]
)
async def test_research_rejects_free_parameters_and_hardware_consent(tool, field, caplog, capsys):
    async with Client(create_server()) as client:
        result = await client.call_tool(
            tool, {"research": {"target": {"identity": {}}}, field: "PRIVATE"}
        )
        assert result.is_error
        assert result.structured_content["error"]["code"] == "invalid_arguments"
        assert "PRIVATE" not in result.model_dump_json()
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err + caplog.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    "research",
    [
        {"target": {"identity": {"command": "PRIVATE"}}},
        {"target": {"identity": {}, "gki": "true"}},
        {"target": {"identity": {}}, "sources": [{"url": "file:///PRIVATE"}]},
        {
            "target": {"identity": {}},
            "evidence": [{"topic": "magisk", "finding": "PRIVATE", "statement": "PRIVATE"}],
        },
    ],
)
async def test_nested_research_validation_is_safe_before_sdk_logging(research, caplog, capsys):
    async with Client(create_server()) as client:
        result = await client.call_tool("check_root_compatibility", {"research": research})
        assert result.structured_content["error"]["code"] == "invalid_arguments"
        assert "PRIVATE" not in result.model_dump_json()
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err + caplog.text


@pytest.mark.anyio
async def test_research_sources_roundtrip_without_network_or_logs(caplog, capsys):
    source = {
        "publisher": "Synthetic",
        "kind": "project",
        "title": "Synthetic research",
        "url": "https://example.invalid/PRIVATE",
        "verified_at": utc_now().isoformat(),
    }
    async with Client(create_server()) as client:
        result = await client.call_tool(
            "check_root_compatibility",
            {"research": {"target": {"identity": {}}, "sources": [source]}},
        )
        assert not result.is_error
        assert result.structured_content["sources"][0]["url"] == source["url"]
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err + caplog.text


@pytest.mark.anyio
@pytest.mark.parametrize("invalid_output", [False, True])
async def test_research_internal_failures_do_not_reach_sdk_logs(
    monkeypatch, caplog, capsys, invalid_output
):
    backend = Mock(return_value="PRIVATE INVALID OUTPUT")
    if not invalid_output:
        backend.side_effect = RuntimeError("PRIVATE RESEARCH EXCEPTION")
    monkeypatch.setattr("ari.mcp.server.assess_root", backend)
    async with Client(create_server()) as client:
        result = await client.call_tool(
            "check_root_compatibility", {"research": {"target": {"identity": {}}}}
        )
        assert result.is_error
        assert result.structured_content["error"]["code"] == "internal_error"
        assert "PRIVATE" not in result.model_dump_json()
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err + caplog.text
