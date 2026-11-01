from datetime import datetime, timedelta

from ari.core.models import utc_now
from ari.research.models import (
    Conclusion,
    EvidenceStatus,
    ExcludedEvidence,
    ResearchEvidence,
    ResearchInput,
    ResearchTopic,
)

MAX_SOURCE_AGE = timedelta(days=180)


def exclusion_reason(research: ResearchInput, item: ResearchEvidence, now: datetime) -> str | None:
    if item.scope != "exact_build":
        return "General or model evidence cannot establish exact-device compatibility"
    try:
        if item.target.identity.exact_key() != research.target.identity.exact_key():
            return "Exact manufacturer/model/variant/fingerprint mismatch"
    except ValueError:
        return "Exact target identity is incomplete"
    for field in ("android_version", "architecture"):
        observed = getattr(item.target.identity, field)
        requested = getattr(research.target.identity, field)
        if observed is not None and observed != requested:
            return "Reported platform mismatch"
    if item.topic != ResearchTopic.BOOTLOADER_STATE:
        for field in ("region", "operator"):
            requested = getattr(research.target, field)
            if requested is None or requested != getattr(item.target, field):
                return "Exact region/operator applicability is unverified"
    if item.topic == ResearchTopic.KERNELSU:
        for field in ("kernel_release", "kmi", "gki"):
            requested = getattr(research.target, field)
            if requested is None or requested != getattr(item.target, field):
                return "Kernel/GKI/KMI applicability is unverified"
    sources = {source.id: source for source in research.sources}
    if not item.source_ids:
        return "No verifiable source supplied"
    if (
        any(
            not timedelta(0) <= now - sources[source_id].verified_at <= MAX_SOURCE_AGE
            for source_id in item.source_ids
        )
        or not timedelta(0) <= now - item.observed_at <= MAX_SOURCE_AGE
    ):
        return "Evidence requires a current verification (maximum 180 days)"
    kinds = {sources[source_id].kind for source_id in item.source_ids}
    if item.topic in {ResearchTopic.BOOTLOADER_STATE, ResearchTopic.OEM_PERMISSION}:
        if "device_observation" not in kinds:
            return "Documentation does not measure the device state or OEM permission"
    elif item.topic in {ResearchTopic.MAGISK, ResearchTopic.KERNELSU}:
        if not kinds & {"project", "manufacturer"}:
            return "Project or manufacturer evidence is required for a definitive conclusion"
    elif "manufacturer" not in kinds:
        return "Manufacturer evidence is required for official unlock or restrictions"
    return None


def evaluate_claim(
    research: ResearchInput, topic: ResearchTopic, *, now: datetime | None = None
) -> Conclusion:
    now = now or utc_now()
    supplied = [item for item in research.evidence if item.topic == topic]
    candidates = [
        item
        for item in supplied
        if exclusion_reason(research, item, now) is None and item.finding != "unknown"
    ]
    evidence_ids = tuple(item.id for item in candidates)
    if len({item.finding for item in candidates}) > 1:
        return Conclusion(
            status=EvidenceStatus.UNVERIFIED,
            evidence_ids=evidence_ids,
            conflicting=True,
            reason="Conflicting applicable evidence; stop and resolve the disagreement",
        )
    if not candidates:
        return Conclusion(
            status=EvidenceStatus.UNVERIFIED if supplied else EvidenceStatus.UNKNOWN,
            reason="No current evidence establishes this finding for the exact target",
        )
    ranking = {status: rank for rank, status in enumerate(reversed(list(EvidenceStatus)))}
    strongest = max(candidates, key=lambda item: ranking[item.status])
    return Conclusion(
        value=strongest.finding if strongest.status == EvidenceStatus.CONFIRMED else "unknown",
        status=strongest.status,
        confidence=strongest.confidence,
        evidence_ids=evidence_ids,
        reason="Researcher-supplied evidence; no attestation or independent content verification",
    )


def excluded_evidence(research: ResearchInput) -> tuple[ExcludedEvidence, ...]:
    now = utc_now()
    return tuple(
        ExcludedEvidence(evidence_id=item.id, reason=reason)
        for item in research.evidence
        if (reason := exclusion_reason(research, item, now)) is not None
    )
