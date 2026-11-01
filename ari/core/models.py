"""Validated evidence; unknown values remain unknown rather than guessed."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

NonEmpty = Annotated[str, Field(min_length=1, max_length=4096, pattern=r"\S")]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def utc_now() -> datetime:
    return datetime.now(UTC)


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class Confidence(StrEnum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    UNKNOWN = "unknown"


class SourceReference(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    title: NonEmpty
    url: HttpUrl
    verified_at: AwareDatetime
    notes: str = ""


class Evidence(DomainModel):
    statement: NonEmpty
    confidence: Confidence = Confidence.UNKNOWN
    source_ids: tuple[UUID, ...] = ()
    observed_at: AwareDatetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def require_provenance(self) -> "Evidence":
        if self.confidence != Confidence.UNKNOWN and not self.source_ids:
            raise ValueError("Confirmed or probable evidence requires a source")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("Source IDs must be unique")
        return self
