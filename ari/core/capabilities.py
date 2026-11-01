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
    phase: int = 5
    read_only: Literal[True] = True
    simulation: Literal[True] = True
    device_access: Literal[False] = False
    adb_read_only_available: Literal[True] = True
    codex_connection: Literal["verify_on_client"] = "verify_on_client"
    offline_research_available: Literal[True] = True
    modification_available: Literal[False] = False
    static_firmware_available: Literal[True] = True


_ADB_READS = ("detect_devices", "inspect_device", "get_device_properties", "inspect_adb_status")
_RESEARCH = ("analyze_unlock_compatibility", "check_root_compatibility", "create_root_plan")
_FIRMWARE = ("analyze_firmware", "verify_firmware_hash")
_PENDING = {
    4: (
        "inspect_fastboot_status",
        "inspect_bootloader",
        "research_root_methods",
    ),
    6: ("verify_root_status", "generate_device_report", "create_recovery_plan"),
}
_PENDING_DETAILS = {
    "research_root_methods": "Automatic web retrieval pending; Codex supplies reviewed sources",
    "inspect_bootloader": "Hardware probing pending; offline evidence assessment is available",
    "inspect_fastboot_status": "Fastboot is prohibited in phase 5; no backend is implemented",
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
            detail=_PENDING_DETAILS.get(
                name, "Contract/roadmap only; not registered as an MCP tool"
            ),
        )
        for phase, names in _PENDING.items()
        for name in names
    )
    research = tuple(
        Capability(
            name=name,
            phase=4,
            status="implemented",
            detail="Offline dated-evidence evaluation; no network, hardware or execution",
            mcp_registered=True,
        )
        for name in _RESEARCH
    )
    firmware = tuple(
        Capability(
            name=name,
            phase=5,
            status="implemented",
            mcp_registered=True,
            detail="Bounded static analysis inside an authorized local firmware directory",
        )
        for name in _FIRMWARE
    )
    return CapabilityCatalog(capabilities=implemented + adb + research + firmware + pending)
