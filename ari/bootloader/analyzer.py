from ari.bootloader.contracts import BootloaderAssessment
from ari.research.evaluator import evaluate_claim
from ari.research.models import ResearchInput, ResearchTopic


def analyze_unlock_compatibility(research: ResearchInput) -> BootloaderAssessment:
    research = ResearchInput.model_validate(research.model_dump(mode="python", warnings=False))
    state = evaluate_claim(research, ResearchTopic.BOOTLOADER_STATE)
    unlock = evaluate_claim(research, ResearchTopic.OFFICIAL_UNLOCK)
    return BootloaderAssessment(
        state=state.value,
        unlock_capability=unlock.value if unlock.value != "unknown" else "unverified",
        state_evidence=state,
        unlock_evidence=unlock,
        oem_permission=evaluate_claim(research, ResearchTopic.OEM_PERMISSION),
        regional_restrictions=evaluate_claim(research, ResearchTopic.REGIONAL_RESTRICTION),
        carrier_restrictions=evaluate_claim(research, ResearchTopic.CARRIER_RESTRICTION),
    )
