from typing import Literal

from ari import __version__
from ari.core.models import DomainModel


class Capability(DomainModel):
    name: str
    phase: int
    status: Literal["implemented", "not_implemented"]
    detail: str
    mcp_registered: bool = False


class CapabilityCatalog(DomainModel):
    capabilities: tuple[Capability, ...]


class ProjectStatus(DomainModel):
    name: str = "Android Root Intelligence"
    version: str = __version__
    phase: int = 3
    read_only: Literal[True] = True
    simulation: Literal[True] = True
    device_access: Literal[False] = False
    adb_read_only_available: Literal[True] = True
    codex_connection: Literal["verify_on_client"] = "verify_on_client"


_ADB_READS = ("detect_devices", "inspect_device", "get_device_properties", "inspect_adb_status")
_PENDING = {
    4: (
        "inspect_fastboot_status",
        "inspect_bootloader",
        "analyze_unlock_compatibility",
        "research_root_methods",
        "check_root_compatibility",
        "create_root_plan",
    ),
    5: ("analyze_firmware", "verify_firmware_hash"),
    6: ("verify_root_status", "generate_device_report", "create_recovery_plan"),
}


def list_capabilities() -> CapabilityCatalog:
    implemented = tuple(
        Capability(
            name=name,
            phase=1,
            status="implemented",
            detail="Foundation metadata only",
            mcp_registered=True,
        )
        for name in ("get_project_status", "list_capabilities")
    )
    adb = tuple(
        Capability(
            name=name,
            phase=2,
            status="implemented",
            detail="Python and MCP read-only ADB; per-call opt-in; hardware verification separate",
            mcp_registered=True,
        )
        for name in _ADB_READS
    )
    pending = tuple(
        Capability(
            name=name,
            phase=phase,
            status="not_implemented",
            detail="Contract/roadmap only; not registered as an MCP tool",
        )
        for phase, names in _PENDING.items()
        for name in names
    )
    return CapabilityCatalog(capabilities=implemented + adb + pending)
