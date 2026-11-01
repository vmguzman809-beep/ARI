import hashlib
from unittest.mock import Mock

import pytest
from mcp import Client

from ari.firmware.models import FirmwareError, FirmwareErrorCode
from ari.mcp.server import create_server
from tests.test_firmware import boot_blob


@pytest.mark.anyio
@pytest.mark.parametrize("legacy", [False, True])
async def test_hash_and_analysis_are_authorized_static_and_theoretical(tmp_path, identity, legacy):
    data = boot_blob()
    artifact = tmp_path / "boot.img"
    artifact.write_bytes(data)
    factory = Mock(side_effect=AssertionError("Hardware forbidden"))
    async with Client(
        create_server(firmware_root=tmp_path, inspector_factory=factory),
        **({"mode": "legacy"} if legacy else {}),
    ) as client:
        request = {"artifact": "boot.img", "authorized": True}
        result = await client.call_tool("verify_firmware_hash", {"request": request})
        assert not result.is_error
        assert result.structured_content["sha256"] == hashlib.sha256(data).hexdigest()
        denied = await client.call_tool(
            "verify_firmware_hash", {"request": {"artifact": "boot.img"}}
        )
        assert denied.structured_content["error"]["code"] == "file_authorization_required"
        result = await client.call_tool(
            "analyze_firmware",
            {
                "request": {
                    **request,
                    "expected_identity": identity.model_dump(mode="json"),
                    "research": {"target": {"identity": identity.model_dump(mode="json")}},
                }
            },
        )
        assert not result.is_error
        assert result.structured_content["plan"]["executable"] is False
        assert result.structured_content["firmware"]["identity_match"] == "insufficient"
    factory.assert_not_called()
    assert artifact.read_bytes() == data


@pytest.mark.anyio
@pytest.mark.parametrize(
    "arguments",
    [
        {"request": {"artifact": "../PRIVATE.img", "authorized": True}},
        {"request": {"artifact": "C:/PRIVATE.img", "authorized": True}},
        {"request": {"artifact": "\\\\PRIVATE\\boot.img", "authorized": True}},
        {"request": {"artifact": "boot.img:PRIVATE", "authorized": True}},
        {"request": {"artifact": "boot.img", "authorized": "true"}},
        {"request": {"artifact": "boot.img", "authorized": True, "shell": "PRIVATE"}},
        {"request": {"artifact": "boot.img"}, "root": "PRIVATE"},
        {"request": {"artifact": "boot.img", "backend": "PRIVATE"}},
    ],
)
async def test_invalid_paths_and_process_parameters_never_reach_sdk_logs(arguments, caplog, capsys):
    async with Client(create_server()) as client:
        result = await client.call_tool("verify_firmware_hash", arguments)
        assert result.is_error
        assert result.structured_content["error"]["code"] == "invalid_arguments"
        assert "PRIVATE" not in result.model_dump_json()
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err + caplog.text


@pytest.mark.anyio
@pytest.mark.parametrize("code", list(FirmwareErrorCode))
async def test_file_errors_are_static_and_do_not_disclose_path(code, monkeypatch, caplog, capsys):
    factory = Mock(side_effect=FirmwareError(code))
    monkeypatch.setattr("ari.mcp.server.StaticFirmwareAnalyzer", factory)
    async with Client(create_server()) as client:
        result = await client.call_tool(
            "verify_firmware_hash", {"request": {"artifact": "PRIVATE.img", "authorized": True}}
        )
        assert result.structured_content["error"]["code"] == code.value
        assert "PRIVATE" not in result.model_dump_json()
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err + caplog.text


@pytest.mark.anyio
async def test_unexpected_file_exception_is_sanitized(monkeypatch, caplog, capsys):
    monkeypatch.setattr(
        "ari.mcp.server.StaticFirmwareAnalyzer", Mock(side_effect=RuntimeError("PRIVATE DATA"))
    )
    async with Client(create_server()) as client:
        result = await client.call_tool(
            "verify_firmware_hash", {"request": {"artifact": "PRIVATE.img", "authorized": True}}
        )
        assert result.structured_content["error"]["code"] == "internal_error"
        assert "PRIVATE" not in result.model_dump_json()
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err + caplog.text
