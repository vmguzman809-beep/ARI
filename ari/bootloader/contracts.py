from typing import Literal, Protocol

from ari.core.models import DomainModel
from ari.research.models import Conclusion, ResearchInput


class BootloaderAssessment(DomainModel):
    state: Literal["locked", "unlocked", "unknown"] = "unknown"
    unlock_capability: Literal["documented", "unavailable", "unverified"] = "unverified"
    state_evidence: Conclusion
    unlock_evidence: Conclusion
    oem_permission: Conclusion
    regional_restrictions: Conclusion
    carrier_restrictions: Conclusion


class BootloaderAnalyzer(Protocol):
    def analyze_unlock_compatibility(self, research: ResearchInput) -> BootloaderAssessment: ...
