from typing import Literal, Protocol

from pydantic import AwareDatetime, Field

from ari.bootloader.contracts import BootloaderAssessment
from ari.core.models import DomainModel, NonEmpty, utc_now
from ari.device.models import DeviceIdentity
from ari.research.models import (
    Conclusion,
    ExcludedEvidence,
    ResearchEvidence,
    ResearchInput,
    ResearchSource,
)


class CompatibilityReport(DomainModel):
    identity: DeviceIdentity
    created_at: AwareDatetime = Field(default_factory=utc_now)
    bootloader: BootloaderAssessment
    magisk: Conclusion
    kernelsu: Conclusion
    blockers: tuple[NonEmpty, ...]
    evidence: tuple[ResearchEvidence, ...]
    sources: tuple[ResearchSource, ...]
    excluded_evidence: tuple[ExcludedEvidence, ...]
    limitations: tuple[NonEmpty, ...]


class RootPlan(DomainModel):
    """An evidence document, never a command list or execution authorization."""

    identity: DeviceIdentity
    theoretical_only: Literal[True] = True
    executable: Literal[False] = False
    status: Literal["blocked", "theoretical"]
    report: CompatibilityReport
    requirements: tuple[NonEmpty, ...]
    risks: tuple[NonEmpty, ...]
    stop_conditions: tuple[NonEmpty, ...]


class RootPlanner(Protocol):
    def create_root_plan(self, research: ResearchInput) -> RootPlan: ...
