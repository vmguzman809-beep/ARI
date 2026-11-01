from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from ari.core.models import Confidence, DomainModel, NonEmpty, SourceReference, utc_now
from ari.device.models import DeviceIdentity


class EvidenceStatus(StrEnum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


class ResearchTopic(StrEnum):
    BOOTLOADER_STATE = "bootloader_state"
    OFFICIAL_UNLOCK = "official_unlock"
    OEM_PERMISSION = "oem_permission"
    REGIONAL_RESTRICTION = "regional_restriction"
    CARRIER_RESTRICTION = "carrier_restriction"
    MAGISK = "magisk"
    KERNELSU = "kernelsu"


FINDINGS = {
    ResearchTopic.BOOTLOADER_STATE: {"locked", "unlocked", "unknown"},
    ResearchTopic.OFFICIAL_UNLOCK: {"documented", "unavailable", "unknown"},
    ResearchTopic.OEM_PERMISSION: {"allowed", "denied", "unknown"},
    ResearchTopic.REGIONAL_RESTRICTION: {"restricted", "clear", "unknown"},
    ResearchTopic.CARRIER_RESTRICTION: {"restricted", "clear", "unknown"},
    ResearchTopic.MAGISK: {"supported", "unsupported", "unknown"},
    ResearchTopic.KERNELSU: {"supported", "unsupported", "unknown"},
}


class ResearchSource(SourceReference):
    publisher: NonEmpty
    kind: Literal["manufacturer", "project", "platform", "community", "device_observation"]

    @model_validator(mode="after")
    def reject_url_credentials(self) -> "ResearchSource":
        if self.url.username is not None or self.url.password is not None:
            raise ValueError("Source URLs must not contain credentials")
        return self


class ResearchTarget(DomainModel):
    identity: DeviceIdentity
    region: NonEmpty | None = None
    operator: NonEmpty | None = None
    kernel_release: NonEmpty | None = None
    kmi: NonEmpty | None = None
    gki: StrictBool | None = None


class ResearchEvidence(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    topic: ResearchTopic
    finding: NonEmpty = "unknown"
    statement: NonEmpty
    status: EvidenceStatus = EvidenceStatus.UNKNOWN
    confidence: Confidence = Confidence.UNKNOWN
    source_ids: Annotated[tuple[UUID, ...], Field(max_length=16)] = ()
    observed_at: AwareDatetime = Field(default_factory=utc_now)
    scope: Literal["general", "model", "exact_build"] = "general"
    target: ResearchTarget | None = None

    @model_validator(mode="after")
    def validate_claim(self) -> "ResearchEvidence":
        if self.finding not in FINDINGS[self.topic]:
            raise ValueError("Finding is not valid for this topic")
        expected = {
            EvidenceStatus.CONFIRMED: Confidence.CONFIRMED,
            EvidenceStatus.PROBABLE: Confidence.PROBABLE,
            EvidenceStatus.UNVERIFIED: Confidence.UNKNOWN,
            EvidenceStatus.UNKNOWN: Confidence.UNKNOWN,
        }
        if self.confidence != expected[self.status]:
            raise ValueError("Confidence and evidence status disagree")
        if self.status != EvidenceStatus.UNKNOWN and not self.source_ids:
            raise ValueError("Research claims require dated sources")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("Source IDs must be unique")
        if self.scope == "exact_build":
            if self.target is None:
                raise ValueError("Exact evidence requires a target")
            self.target.identity.exact_key()
        if self.scope == "model" and (
            self.target is None
            or self.target.identity.manufacturer is None
            or self.target.identity.model is None
        ):
            raise ValueError("Model evidence requires manufacturer and model")
        return self


class ResearchInput(DomainModel):
    target: ResearchTarget
    sources: Annotated[tuple[ResearchSource, ...], Field(max_length=64)] = ()
    evidence: Annotated[tuple[ResearchEvidence, ...], Field(max_length=128)] = ()

    @model_validator(mode="after")
    def validate_provenance(self) -> "ResearchInput":
        source_ids = {source.id for source in self.sources}
        if len(source_ids) != len(self.sources):
            raise ValueError("Research sources must have unique IDs")
        if len({item.id for item in self.evidence}) != len(self.evidence):
            raise ValueError("Research evidence must have unique IDs")
        if any(not set(item.source_ids) <= source_ids for item in self.evidence):
            raise ValueError("Research is missing an evidence source")
        now = utc_now()
        if any(source.verified_at > now for source in self.sources) or any(
            item.observed_at > now for item in self.evidence
        ):
            raise ValueError("Research dates must not be in the future")
        return self


class Conclusion(DomainModel):
    value: NonEmpty = "unknown"
    status: EvidenceStatus = EvidenceStatus.UNKNOWN
    confidence: Confidence = Confidence.UNKNOWN
    evidence_ids: tuple[UUID, ...] = ()
    conflicting: bool = False
    reason: NonEmpty


class ExcludedEvidence(DomainModel):
    evidence_id: UUID
    reason: NonEmpty
