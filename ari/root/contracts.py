from typing import Protocol

from ari.core.models import DomainModel, Evidence, NonEmpty
from ari.device.models import DeviceIdentity


class RootPlan(DomainModel):
    """An evidence document, never a command list or execution authorization."""

    identity: DeviceIdentity
    requirements: tuple[NonEmpty, ...]
    risks: tuple[NonEmpty, ...]
    stop_conditions: tuple[NonEmpty, ...]
    evidence: tuple[Evidence, ...]


class RootPlanner(Protocol):
    def create_root_plan(self, identity: DeviceIdentity) -> RootPlan: ...
