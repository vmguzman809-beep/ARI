from enum import StrEnum

from ari.core.errors import PhaseUnavailableError
from ari.core.models import DomainModel


class DeviceOperation(StrEnum):
    INSPECT = "inspect"
    PREPARE_IMAGE = "prepare_image"
    UNLOCK = "unlock"
    WRITE_PARTITION = "write_partition"
    WIPE = "wipe"
    REBOOT = "reboot"


class PolicyDecision(DomainModel):
    allowed: bool
    simulation: bool = True
    reason: str


class PhaseOnePolicy:
    def evaluate(self, operation: DeviceOperation) -> PolicyDecision:
        if not isinstance(operation, DeviceOperation):
            raise TypeError("A typed DeviceOperation is required")
        return PolicyDecision(
            allowed=False,
            reason=f"{operation.value}: device operations are unavailable in phase 1",
        )

    def require(self, operation: DeviceOperation) -> None:
        decision = self.evaluate(operation)
        if not decision.allowed:
            raise PhaseUnavailableError(decision.reason)
