import hashlib
import json
from uuid import UUID, uuid4

from pydantic import AwareDatetime, Field

from ari.core.models import DomainModel, NonEmpty, utc_now


class DeviceIdentity(DomainModel):
    manufacturer: NonEmpty | None = None
    model: NonEmpty | None = None
    variant: NonEmpty | None = None
    build_fingerprint: NonEmpty | None = None
    android_version: NonEmpty | None = None
    architecture: NonEmpty | None = None

    def exact_key(self) -> str:
        """Incomplete identity cannot be used to share variant-specific knowledge."""
        parts = (self.manufacturer, self.model, self.variant, self.build_fingerprint)
        if any(value is None for value in parts):
            raise ValueError("Exact manufacturer/model/variant/build_fingerprint required")
        encoded = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class DeviceSnapshot(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    identity: DeviceIdentity
    serial: NonEmpty | None = None
    observed_at: AwareDatetime = Field(default_factory=utc_now)
    provenance: NonEmpty
