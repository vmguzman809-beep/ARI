"""Stable, sanitized errors: never include process arguments or device output."""

from enum import StrEnum

from ari.core.errors import AriError


class AdbErrorCode(StrEnum):
    AUTHORIZATION_REQUIRED = "authorization_required"
    SIMULATION_ENABLED = "simulation_enabled"
    TOOL_NOT_FOUND = "tool_not_found"
    INVALID_EXECUTABLE = "invalid_executable"
    INVALID_REQUEST = "invalid_request"
    INVALID_TARGET = "invalid_target"
    TIMEOUT = "timeout"
    ACCESS_DENIED = "access_denied"
    SERVER_UNAVAILABLE = "server_unavailable"
    COMMAND_FAILED = "command_failed"
    NO_DEVICES = "no_devices"
    DEVICE_NOT_FOUND = "device_not_found"
    DEVICE_OFFLINE = "device_offline"
    DEVICE_UNAUTHORIZED = "device_unauthorized"
    DEVICE_NOT_READY = "device_not_ready"
    AMBIGUOUS_TARGET = "ambiguous_target"
    INVALID_RESPONSE = "invalid_response"
    DEVICE_CHANGED = "device_changed"


class AdbError(AriError):
    def __init__(self, code: AdbErrorCode) -> None:
        self.code = code
        super().__init__(f"ADB read-only operation stopped: {code.value}")
