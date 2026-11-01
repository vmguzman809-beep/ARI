from typing import Protocol

from ari.core.models import DomainModel, Evidence, NonEmpty
from ari.device.models import DeviceSnapshot


class RecoveryPlan(DomainModel):
    observations: tuple[Evidence, ...]
    missing_information: tuple[NonEmpty, ...]
    stop_conditions: tuple[NonEmpty, ...]


class RecoveryPlanner(Protocol):
    def create_recovery_plan(self, device: DeviceSnapshot) -> RecoveryPlan: ...
