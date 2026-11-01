from typing import Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, Field, model_validator

from ari.core.models import DomainModel, Evidence, NonEmpty, Sha256, utc_now
from ari.device.models import DeviceIdentity


class KnowledgeEntry(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    identity: DeviceIdentity
    evidence: Evidence
    firmware_version: NonEmpty | None = None
    firmware_sha256: Sha256 | None = None
    documented_method: NonEmpty | None = None

    @model_validator(mode="after")
    def require_exact_identity(self) -> "KnowledgeEntry":
        self.identity.exact_key()
        return self


class AuditEvent(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    occurred_at: AwareDatetime = Field(default_factory=utc_now)
    operation: NonEmpty
    outcome: Literal["recorded", "blocked", "simulated", "succeeded", "failed"]
    result: NonEmpty
    snapshot_id: UUID | None = None
