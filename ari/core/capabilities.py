from typing import Literal

from ari import __version__
from ari.core.models import DomainModel


class Capability(DomainModel):
    name: str
    phase: int
    status: Literal["implemented", "not_implemented"]
    detail: str


class CapabilityCatalog(DomainModel):
    capabilities: tuple[Capability, ...]


class ProjectStatus(DomainModel):
    name: str = "Android Root Intelligence"
    version: str = __version__
    phase: int = 1
    read_only: Literal[True] = True
    simulation: Literal[True] = True
    device_access: Literal[False] = False
    codex_connection: Literal["not_verified"] = "not_verified"


_PENDING = {
    2: ("detect_devices", "inspect_device", "get_device_properties", "inspect_adb_status"),
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
        Capability(name=name, phase=1, status="implemented", detail="Foundation metadata only")
        for name in ("get_project_status", "list_capabilities")
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
    return CapabilityCatalog(capabilities=implemented + pending)
