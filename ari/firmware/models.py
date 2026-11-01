import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BeforeValidator, Field, StrictBool, model_validator

from ari.core.models import DomainModel, NonEmpty, Sha256, utc_now
from ari.device.models import DeviceIdentity
from ari.research.models import ResearchInput, ResearchSource


def validate_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 240 or value != value.strip():
        raise ValueError("Invalid relative artifact path")
    for part in value.split("/"):
        if (
            part in {"", ".", ".."}
            or not re.fullmatch(r"[A-Za-z0-9_. -]{1,80}", part)
            or part.endswith((" ", "."))
            or re.fullmatch(r"(?i:con|prn|aux|nul|com[0-9]|lpt[0-9])", part.split(".")[0])
        ):
            raise ValueError("Invalid relative artifact path")
    return value


ArtifactPath = Annotated[str, BeforeValidator(validate_relative_path), Field(max_length=240)]


class FirmwareErrorCode(StrEnum):
    AUTHORIZATION_REQUIRED = "file_authorization_required"
    PATH_DENIED = "artifact_path_denied"
    NOT_FOUND = "artifact_not_found"
    CHANGED = "artifact_changed"
    CORRUPT = "firmware_corrupt"
    UNSUPPORTED = "firmware_unsupported"
    RESOURCE_LIMIT = "firmware_resource_limit"


class FirmwareError(Exception):
    def __init__(self, code: FirmwareErrorCode):
        self.code = code
        super().__init__("ARI stopped static firmware analysis; consult the error code.")


class FirmwareLimits(DomainModel):
    max_file_bytes: int = Field(default=2 * 1024**3, ge=1, le=2 * 1024**3)
    max_image_bytes: int = Field(default=64 * 1024**2, ge=1, le=64 * 1024**2)
    max_metadata_bytes: int = Field(default=65536, ge=1, le=65536)
    max_entries: int = Field(default=128, ge=1, le=128)
    max_directory_bytes: int = Field(default=1024**2, ge=1, le=1024**2)
    max_declared_bytes: int = Field(default=4 * 1024**3, ge=1, le=4 * 1024**3)
    max_ratio: int = Field(default=200, ge=1, le=200)
    timeout_seconds: float = Field(default=30.0, gt=0, le=30)


class FileInput(DomainModel):
    artifact: ArtifactPath
    authorized: StrictBool = False


class HashInput(FileInput):
    expected_sha256: Sha256 | None = None


class FirmwareProvenance(DomainModel):
    source: ResearchSource | None = None
    hash_source: ResearchSource | None = None

    @model_validator(mode="after")
    def require_past_dates(self) -> "FirmwareProvenance":
        if any(
            source is not None and source.verified_at > utc_now()
            for source in (self.source, self.hash_source)
        ):
            raise ValueError("Firmware source dates must not be in the future")
        return self


class FirmwareInput(HashInput):
    expected_identity: DeviceIdentity
    expected_build_id: NonEmpty | None = None
    provenance: FirmwareProvenance = Field(default_factory=FirmwareProvenance)
    research: ResearchInput | None = None


class HashResult(DomainModel):
    artifact: ArtifactPath
    size_bytes: int
    sha256: Sha256
    expected_sha256: Sha256 | None = None
    matches: bool | None = None
    original_preserved: Literal[True] = True
    authenticity_verified: Literal[False] = False


class AvbObservation(DomainModel):
    present: bool = False
    algorithm: int | None = None
    rollback_index: int | None = None
    rollback_index_location: int | None = None
    flags: int | None = None
    descriptor_count: int = 0
    public_key_sha256: Sha256 | None = None
    signature_verified: Literal[False] = False
    antirollback_compatible: Literal["unknown"] = "unknown"


class ImageObservation(DomainModel):
    member: ArtifactPath
    format: Literal["android_boot", "vendor_boot", "vbmeta"]
    partition_hint: Literal["boot", "init_boot", "vendor_boot", "recovery", "vbmeta", "unknown"]
    slot_hint: Literal["a", "b"] | None = None
    size_bytes: int
    sha256: Sha256
    header_version: int | None = None
    page_size: int | None = None
    kernel_size: int | None = None
    ramdisk_size: int | None = None
    os_version: NonEmpty | None = None
    security_patch_month: NonEmpty | None = None
    boot_signature_size: int | None = None
    avb: AvbObservation


class PropertyObservation(DomainModel):
    member: ArtifactPath
    name: NonEmpty
    value: NonEmpty


class FirmwareReport(DomainModel):
    ari_version: Literal["0.5.0"] = "0.5.0"
    created_at: AwareDatetime = Field(default_factory=utc_now)
    integrity: HashResult
    container: Literal["zip", "image"]
    identity: DeviceIdentity
    expected_identity: DeviceIdentity
    expected_build_id: NonEmpty | None = None
    identity_match: Literal["matched", "mismatch", "insufficient"]
    build_id: NonEmpty | None = None
    ab: Literal["declared_ab", "declared_non_ab", "unknown"] = "unknown"
    observed_slot_hints: tuple[Literal["a", "b"], ...] = ()
    active_slot: Literal["unknown"] = "unknown"
    observations: tuple[PropertyObservation, ...] = ()
    images: tuple[ImageObservation, ...] = ()
    uninspected_members: int = 0
    provenance: FirmwareProvenance
    status: Literal["blocked"] = "blocked"
    blockers: tuple[NonEmpty, ...]
    limitations: tuple[NonEmpty, ...]
