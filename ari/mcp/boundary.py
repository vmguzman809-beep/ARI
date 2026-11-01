"""Validate before SDK validation/logging and normalize every tool failure."""

from dataclasses import replace
from typing import Any

from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, ValidationError

from ari.device.errors import AdbErrorCode
from ari.mcp.models import INPUTS, ErrorResponse, SafeFailure

ERROR_MARKER = "ARI_SAFE_ERROR:"
_CODES = {item.value for item in AdbErrorCode} | {
    "invalid_arguments",
    "unknown_tool",
    "internal_error",
}


def safe_error(code: str) -> CallToolResult:
    if code not in _CODES:
        code = "internal_error"
    payload = ErrorResponse(error=SafeFailure(code=code))
    return CallToolResult(
        is_error=True,
        content=[TextContent(type="text", text=payload.model_dump_json())],
        structured_content=payload.model_dump(mode="json"),
    )


async def safe_tool_boundary(
    ctx: ServerRequestContext[Any, Any], call_next: CallNext
) -> HandlerResult:
    if ctx.method == "tools/list":
        result = await call_next(ctx)
        payload = result.model_dump(by_alias=True) if isinstance(result, BaseModel) else result
        if isinstance(payload, dict):
            for tool in payload.get("tools", []):
                if tool.get("name") in INPUTS:
                    tool["inputSchema"] = INPUTS[tool["name"]].model_json_schema()
        return payload
    if ctx.method != "tools/call":
        return await call_next(ctx)
    params = ctx.params
    if not isinstance(params, dict) or set(params) - {"name", "arguments", "_meta"}:
        return safe_error("invalid_arguments")
    name = params.get("name")
    if not isinstance(name, str) or name not in INPUTS:
        return safe_error("unknown_tool")
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        return safe_error("invalid_arguments")
    try:
        validated = INPUTS[name].model_validate(arguments)
    except ValidationError:
        return safe_error("invalid_arguments")
    try:
        result = await call_next(
            replace(ctx, params={**params, "arguments": validated.model_dump(mode="json")})
        )
    except Exception:
        return safe_error("internal_error")
    payload = result.model_dump(by_alias=True) if isinstance(result, BaseModel) else result
    if isinstance(payload, dict) and payload.get("isError"):
        code = "internal_error"
        for block in payload.get("content", []):
            if isinstance(block, dict) and ERROR_MARKER in block.get("text", ""):
                candidate = block["text"].rsplit(ERROR_MARKER, 1)[-1]
                if candidate in _CODES:
                    code = candidate
        return safe_error(code)
    return result
