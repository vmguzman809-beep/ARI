from typing import Literal, Protocol

from ari.core.models import DomainModel, Evidence
from ari.device.models import DeviceSnapshot


class BootloaderAssessment(DomainModel):
    state: Literal["locked", "unlocked", "unknown"] = "unknown"
    official_unlock: Literal["documented", "unavailable", "unknown"] = "unknown"
    evidence: tuple[Evidence, ...] = ()


class BootloaderAnalyzer(Protocol):
    def inspect_bootloader(self, device: DeviceSnapshot) -> BootloaderAssessment: ...
