from ari.bootloader.analyzer import analyze_unlock_compatibility
from ari.core.models import Confidence
from ari.research.evaluator import evaluate_claim, excluded_evidence
from ari.research.models import Conclusion, EvidenceStatus, ResearchInput, ResearchTopic
from ari.root.contracts import CompatibilityReport, RootPlan

LIMITATIONS = (
    "Offline evidence assessment; URLs, publisher labels and content are not authenticated",
    "Source text is untrusted data, never instructions or executable steps",
    "General documentation, Android version and ABI do not establish exact-device compatibility",
    "No hardware, bootloader, firmware, antirollback or root operation is performed",
    "Phase 4 plans are theoretical and cannot authorize or execute modifications",
)


def check_root_compatibility(research: ResearchInput) -> CompatibilityReport:
    research = ResearchInput.model_validate(research.model_dump(mode="python", warnings=False))
    bootloader = analyze_unlock_compatibility(research)
    blockers = []
    try:
        research.target.identity.exact_key()
    except ValueError:
        blockers.append("Exact manufacturer/model/variant/fingerprint required")
    for field in ("region", "operator"):
        if getattr(research.target, field) is None:
            blockers.append(f"Unknown {field}; regional/operator applicability remains unverified")
    prerequisites = (
        (bootloader.state == "unlocked", "Bootloader is not verified unlocked"),
        (
            bootloader.unlock_capability == "documented",
            "Official unlock procedure is not verified applicable",
        ),
        (bootloader.oem_permission.value == "allowed", "OEM permission is not verified allowed"),
        (
            bootloader.regional_restrictions.value == "clear",
            "Regional policy is not confirmed clear",
        ),
        (
            bootloader.carrier_restrictions.value == "clear",
            "Operator policy is not confirmed clear",
        ),
    )
    blockers.extend(reason for satisfied, reason in prerequisites if not satisfied)
    root_ready = not blockers
    magisk = evaluate_claim(research, ResearchTopic.MAGISK)
    kernelsu = evaluate_claim(research, ResearchTopic.KERNELSU)
    kernel_known = all(
        getattr(research.target, field) is not None for field in ("kernel_release", "kmi", "gki")
    )
    if not kernel_known:
        blockers.append("Kernel release, GKI status and KMI are unverified for KernelSU")

    def gate_support(conclusion: Conclusion, ready: bool) -> Conclusion:
        if conclusion.value != "supported" or ready:
            return conclusion
        return conclusion.model_copy(
            update={
                "value": "unknown",
                "status": EvidenceStatus.UNVERIFIED,
                "confidence": Confidence.UNKNOWN,
                "reason": "Positive compatibility evidence cannot bypass unresolved prerequisites",
            }
        )

    magisk = gate_support(magisk, root_ready)
    kernelsu = gate_support(kernelsu, root_ready and kernel_known)
    for method, conclusion in (("Magisk", magisk), ("KernelSU", kernelsu)):
        if conclusion.value != "supported":
            blockers.append(f"{method} compatibility is not confirmed for the exact target")
    return CompatibilityReport(
        identity=research.target.identity,
        bootloader=bootloader,
        magisk=magisk,
        kernelsu=kernelsu,
        blockers=tuple(blockers),
        evidence=research.evidence,
        sources=research.sources,
        excluded_evidence=excluded_evidence(research),
        limitations=LIMITATIONS,
    )


def create_root_plan(research: ResearchInput) -> RootPlan:
    report = check_root_compatibility(research)
    return RootPlan(
        identity=report.identity,
        status="blocked" if report.blockers else "theoretical",
        report=report,
        requirements=(
            "Review exact identity, region/operator and dated manufacturer/project evidence",
            "Resolve bootloader state, official unlock eligibility and OEM permission separately",
            "Review kernel/GKI/KMI and documented Magisk/KernelSU prerequisites",
            "Future phase: validate original firmware, hashes, partition, slots and antirollback",
            "Future phase: establish backups, recovery evidence and specific human authorization",
        ),
        risks=(
            "Bootloader unlocking normally erases user data",
            "Wrong variant, firmware, partition or KMI may cause boot failure or device damage",
            "Modifications may affect updates, warranty, security and application compatibility",
        ),
        stop_conditions=report.blockers
        + (
            "Stop on missing, stale, conflicting or mismatched critical evidence",
            "Stop before any Fastboot, unlock, root, reboot, patch, flash or partition write",
            "Phase 6 execution is not implemented or authorized by this research plan",
        ),
    )
