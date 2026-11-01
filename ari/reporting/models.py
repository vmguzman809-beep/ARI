from uuid import UUID, uuid4

from pydantic import AwareDatetime, Field, model_validator

from ari.core.models import DomainModel, Evidence, NonEmpty, SourceReference, utc_now


class EvidenceReport(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    title: NonEmpty
    created_at: AwareDatetime = Field(default_factory=utc_now)
    evidence: tuple[Evidence, ...] = ()
    sources: tuple[SourceReference, ...] = ()
    limitations: tuple[NonEmpty, ...] = ("Phase 1: no device inspection performed",)

    @model_validator(mode="after")
    def require_report_sources(self) -> "EvidenceReport":
        source_ids = {source.id for source in self.sources}
        if len(source_ids) != len(self.sources):
            raise ValueError("Report sources must have unique IDs")
        if any(not set(item.source_ids) <= source_ids for item in self.evidence):
            raise ValueError("Report is missing an evidence source")
        return self

    def as_json(self) -> str:
        return self.model_dump_json(indent=2)
