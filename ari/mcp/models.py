"""Closed MCP inputs; only firmware accepts a confined relative artifact path."""

from typing import Literal

from pydantic import StrictBool

from ari.core.models import DomainModel
from ari.device.adb import AdbSerial
from ari.device.errors import AdbErrorCode
from ari.firmware.models import FirmwareErrorCode, FirmwareInput, HashInput
from ari.research.models import ResearchInput


class EmptyInput(DomainModel):
    pass


class ReadInput(DomainModel):
    authorized: StrictBool = False
    simulation: StrictBool = True


class TargetInput(ReadInput):
    serial: AdbSerial


class ResearchToolInput(DomainModel):
    research: ResearchInput


class FirmwareToolInput(DomainModel):
    request: FirmwareInput


class HashToolInput(DomainModel):
    request: HashInput


class SafeFailure(DomainModel):
    code: (
        AdbErrorCode
        | FirmwareErrorCode
        | Literal["invalid_arguments", "unknown_tool", "internal_error"]
    )
    message: Literal["ARI stopped this read-only request; consult the error code."] = (
        "ARI stopped this read-only request; consult the error code."
    )


class ErrorResponse(DomainModel):
    ok: Literal[False] = False
    error: SafeFailure


INPUTS = {
    "get_project_status": EmptyInput,
    "list_capabilities": EmptyInput,
    "detect_devices": ReadInput,
    "inspect_adb_status": TargetInput,
    "get_device_properties": TargetInput,
    "inspect_device": TargetInput,
    "analyze_unlock_compatibility": ResearchToolInput,
    "check_root_compatibility": ResearchToolInput,
    "create_root_plan": ResearchToolInput,
    "analyze_firmware": FirmwareToolInput,
    "verify_firmware_hash": HashToolInput,
}
