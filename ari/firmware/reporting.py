from ari.core.models import Confidence, DomainModel
from ari.firmware.models import FirmwareReport
from ari.research.models import Conclusion, EvidenceStatus, ResearchInput
from ari.root.contracts import CompatibilityReport, RootPlan
from ari.root.research import create_root_plan


class FirmwareIntelligenceReport(DomainModel):
    firmware: FirmwareReport
    compatibility: CompatibilityReport | None = None
    plan: RootPlan | None = None


def link_firmware_report(
    firmware: FirmwareReport, research: ResearchInput | None
) -> FirmwareIntelligenceReport:
    if research is None:
        return FirmwareIntelligenceReport(firmware=firmware)
    plan = create_root_plan(research)
    blockers = list(firmware.blockers)
    if research.target.identity != firmware.expected_identity:
        blockers.append("Firmware target does not match the research identity")
    unknown = Conclusion(
        reason="Static firmware cannot confirm root compatibility or authorize execution",
        status=EvidenceStatus.UNVERIFIED,
        confidence=Confidence.UNKNOWN,
    )
    compatibility = plan.report.model_copy(
        update={
            "blockers": plan.report.blockers + tuple(blockers),
            "magisk": unknown if plan.report.magisk.value == "supported" else plan.report.magisk,
            "kernelsu": unknown
            if plan.report.kernelsu.value == "supported"
            else plan.report.kernelsu,
        }
    )
    plan = plan.model_copy(
        update={
            "status": "blocked",
            "report": compatibility,
            "stop_conditions": plan.stop_conditions + tuple(blockers),
        }
    )
    return FirmwareIntelligenceReport(firmware=firmware, compatibility=compatibility, plan=plan)
