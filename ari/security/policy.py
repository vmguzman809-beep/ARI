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


class PhaseTwoPolicy:
    def evaluate(
        self, operation: DeviceOperation, *, authorized: bool = False, simulation: bool = True
    ) -> PolicyDecision:
        if not isinstance(operation, DeviceOperation):
            raise TypeError("A typed DeviceOperation is required")
        if operation != DeviceOperation.INSPECT:
            reason = "Device modifications are unavailable in phase 2"
        elif authorized is not True:
            reason = "Owner authorization is required for read-only diagnosis"
        elif simulation is not False:
            reason = "Simulation enabled; no device process may start"
        else:
            return PolicyDecision(allowed=True, simulation=False, reason="Authorized read-only ADB")
        return PolicyDecision(allowed=False, simulation=simulation, reason=reason)
