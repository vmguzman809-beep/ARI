from pathlib import Path
from typing import Literal, Protocol

from ari.core.models import DomainModel, Evidence, Sha256
from ari.device.models import DeviceIdentity


class FirmwareArtifact(DomainModel):
    path: Path
    identity: DeviceIdentity
    sha256: Sha256 | None = None
    partition: Literal["boot", "init_boot", "recovery", "unknown"] = "unknown"
    evidence: tuple[Evidence, ...] = ()


class FirmwareAnalyzer(Protocol):
    def analyze_firmware(self, path: Path) -> FirmwareArtifact: ...
