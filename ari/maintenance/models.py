"""Closed, deeply immutable contracts. Artifact contents remain private evidence."""

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ari.maintenance.errors import MaintenanceError

MAX_PACKAGES = 10_000
Text = Annotated[str, Field(min_length=1, max_length=512, pattern=r"^[^\x00-\x1f\x7f]+$")]
PackageId = Annotated[
    str,
    Field(
        min_length=1,
        max_length=255,
        pattern=r"^(android|[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+)$",
    ),
]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Code = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")]


class MaintenanceModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )

    def __repr_args__(self):
        # Explicit serialization is private evidence; accidental repr/str is not.
        return ()


class KnowledgeState(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    CONTRADICTORY = "contradictory"
    BLOCKED = "blocked"


class EnabledState(StrEnum):
    DEFAULT = "default"
    ENABLED = "enabled"
    DISABLED = "disabled"
    DISABLED_USER = "disabled_user"
    DISABLED_UNTIL_USED = "disabled_until_used"
    UNKNOWN = "unknown"


class CriticalFunction(StrEnum):
    TELEPHONY = "telephony"
    IMS = "ims"
    EMERGENCY = "emergency"
    SIM = "sim"
    ESIM = "esim"
    SMS = "sms"
    CONTACTS = "contacts"
    PERMISSIONS = "permissions"
    INSTALLER = "installer"
    HOME = "home"
    SYSTEM_UI = "system_ui"
    IME = "ime"
    CONNECTIVITY = "connectivity"
    DEVICE_ADMIN = "device_admin"
    ACCESSIBILITY = "accessibility"
    LOCK_SCREEN = "lock_screen"
    UPDATER = "updater"
    CALENDAR = "calendar"
    BLOCKED_NUMBERS = "blocked_numbers"


class DeviceIdentityRef(MaintenanceModel):
    device_ref: UUID
    manufacturer: Text | None = None
    model: Text | None = None
    hardware_sku: Text | None = None
    odm_sku: Text | None = None
    variant: Text | None = None
    build_id: Text | None = None
    fingerprint: Text | None = None
    region: Text | None = None
    operator: Text | None = None

    @model_validator(mode="after")
    def reject_ambiguous_identity(self) -> "DeviceIdentityRef":
        for name in type(self).model_fields:
            value = getattr(self, name)
            if isinstance(value, str) and (
                value != value.strip() or value.lower() in {"unknown", "null", "none", "?"}
            ):
                raise ValueError("Use null for missing identity")
        return self

    def complete(self) -> bool:
        return all(getattr(self, name) is not None for name in type(self).model_fields)


class UserScope(MaintenanceModel):
    user_id: Annotated[int, Field(ge=0, le=2**31 - 1)]
    profile_kind: Literal["personal", "work", "secondary", "system", "unknown"]
    parent_user_id: Annotated[int, Field(ge=0, le=2**31 - 1)] | None = None
    scope: Literal["user"] = "user"

    @model_validator(mode="after")
    def validate_parent(self) -> "UserScope":
        if self.parent_user_id == self.user_id:
            raise ValueError("Profile cannot parent itself")
        if self.profile_kind == "work" and self.parent_user_id is None:
            raise ValueError("Work profile requires parent scope")
        if self.profile_kind != "work" and self.parent_user_id is not None:
            raise ValueError("Parent scope requires a work profile")
        return self


class Provenance(MaintenanceModel):
    source_id: UUID
    kind: Literal["synthetic", "local_export", "documentary"]
    source_ref: Text
    verified_at: AwareDatetime


class EvidenceObservation(MaintenanceModel):
    evidence_id: UUID
    subject: PackageId
    claim: Code
    value: Text | None = None
    state: KnowledgeState
    confidence: Literal["high", "low", "unknown"]
    source_id: UUID
    observed_at: AwareDatetime

    @model_validator(mode="after")
    def validate_claim(self) -> "EvidenceObservation":
        if self.state == KnowledgeState.KNOWN:
            if self.value is None or self.confidence == "unknown":
                raise ValueError("Known evidence requires a value and confidence")
        elif self.value is not None or self.confidence != "unknown":
            raise ValueError("Unresolved evidence must remain unknown")
        return self


class PackageObservation(MaintenanceModel):
    package_id: PackageId
    version_code: Annotated[int, Field(ge=0, le=2**63 - 1)] | None = None
    version_name: Text | None = None
    origin: Literal["system", "user", "apex", "unknown"] = "unknown"
    installed: bool | None = None
    enabled_state: EnabledState = EnabledState.UNKNOWN
    effective_enabled: bool | None = None
    hidden: bool | None = None
    suspended: bool | None = None
    stopped: bool | None = None
    knowledge: KnowledgeState = KnowledgeState.UNKNOWN
    critical_functions: Annotated[tuple[CriticalFunction, ...], Field(max_length=32)] = ()
    functions_complete: bool = False
    dependencies: Annotated[tuple[PackageId, ...], Field(max_length=128)] | None = None
    evidence_ids: Annotated[tuple[UUID, ...], Field(max_length=64)] = ()

    @model_validator(mode="after")
    def validate_observation(self) -> "PackageObservation":
        for values in (self.critical_functions, self.dependencies or (), self.evidence_ids):
            if len(values) != len(set(values)):
                raise ValueError("Duplicate observation entries")
        if self.dependencies and self.package_id in self.dependencies:
            raise ValueError("Self dependency is ambiguous")
        if self.knowledge == KnowledgeState.KNOWN:
            if not self.evidence_ids:
                raise ValueError("Known package state requires evidence")
            if self.installed is None or self.enabled_state == EnabledState.UNKNOWN:
                raise ValueError("Known package state is incomplete")
            if any(
                v is None
                for v in (self.effective_enabled, self.hidden, self.suspended, self.stopped)
            ):
                raise ValueError("Known package flags are incomplete")
            if (self.enabled_state == EnabledState.ENABLED and self.effective_enabled is False) or (
                self.enabled_state in {EnabledState.DISABLED, EnabledState.DISABLED_USER}
                and self.effective_enabled is True
            ):
                raise ValueError("Conflicting enabled observations")
        if (
            self.critical_functions or self.functions_complete or self.dependencies is not None
        ) and (not self.evidence_ids):
            raise ValueError("Classification requires evidence")
        return self


class PackageSnapshot(MaintenanceModel):
    """Source declarations, not an authenticated or independently exhaustive inventory."""

    schema_version: Literal["ari.maintenance.snapshot.v1"] = "ari.maintenance.snapshot.v1"
    snapshot_id: UUID
    captured_at: AwareDatetime
    provenance: Provenance
    identity: DeviceIdentityRef
    user_scope: UserScope
    coverage: Literal["complete", "partial", "unknown"] = Field(
        description="Source-declared coverage; does not verify exhaustiveness or authenticity."
    )
    packages: Annotated[tuple[PackageObservation, ...], Field(max_length=MAX_PACKAGES)]
    evidence: Annotated[tuple[EvidenceObservation, ...], Field(max_length=20_000)] = ()
    limitations: Annotated[tuple[Code, ...], Field(max_length=64)] = ()

    @model_validator(mode="after")
    def validate_provenance(self) -> "PackageSnapshot":
        packages = {p.package_id: p for p in self.packages}
        evidence = {e.evidence_id: e for e in self.evidence}
        if len(packages) != len(self.packages) or len(evidence) != len(self.evidence):
            raise ValueError("Duplicate package or evidence IDs")
        if self.provenance.verified_at < self.captured_at:
            raise ValueError("Export verification predates capture")
        if self.provenance.verified_at > datetime.now(UTC):
            raise ValueError("Future provenance is invalid")
        for item in self.evidence:
            if item.subject not in packages or item.source_id != self.provenance.source_id:
                raise ValueError("Evidence provenance or subject mismatch")
            if item.observed_at > self.captured_at:
                raise ValueError("Observation postdates capture")
        for package in self.packages:
            for ref in package.evidence_ids:
                if ref not in evidence or evidence[ref].subject != package.package_id:
                    raise ValueError("Missing or mismatched package evidence")
        return self


def snapshot_digest(snapshot: PackageSnapshot) -> str:
    """Content binding only; not origin authentication or device attestation."""
    try:
        if type(snapshot) is not PackageSnapshot:
            raise ValueError("Invalid snapshot")
        snapshot = PackageSnapshot.model_validate(snapshot, strict=True)
    except (ValidationError, ValueError, TypeError, AttributeError):
        raise MaintenanceError("invalid_model") from None
    canonical = json.dumps(
        snapshot.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class Baseline(MaintenanceModel):
    schema_version: Literal["ari.maintenance.baseline.v1"] = "ari.maintenance.baseline.v1"
    baseline_id: UUID
    created_at: AwareDatetime
    policy_revision: Literal["phone-conservative-v1"] = "phone-conservative-v1"
    snapshot: PackageSnapshot
    content_sha256: Digest

    @model_validator(mode="after")
    def validate_binding(self) -> "Baseline":
        if self.created_at < self.snapshot.captured_at:
            raise ValueError("Baseline predates snapshot")
        if self.created_at > datetime.now(UTC):
            raise ValueError("Future baseline is invalid")
        if self.content_sha256 != snapshot_digest(self.snapshot):
            raise ValueError("Baseline digest mismatch")
        return self


class PackageRiskAssessment(MaintenanceModel):
    package_id: PackageId
    decision: Literal["protected", "blocked", "review_required"]
    severity: Literal["critical", "high", "unknown"]
    confidence: Literal["high", "low", "unknown"]
    state: KnowledgeState
    reasons: Annotated[tuple[Code, ...], Field(min_length=1, max_length=32)]
    evidence_ids: Annotated[tuple[UUID, ...], Field(max_length=64)] = ()
    policy_revision: Literal["phone-conservative-v1"] = "phone-conservative-v1"


class PackageDifference(MaintenanceModel):
    """Declared observation changes; missing entries never verify install/uninstall events."""

    package_id: PackageId
    fields: tuple[Code, ...]
    kind: Literal["changed", "not_observed_before", "not_observed_after"]


class DriftReport(MaintenanceModel):
    state: KnowledgeState
    comparable: bool
    reasons: Annotated[tuple[Code, ...], Field(max_length=32)]
    differences: Annotated[tuple[PackageDifference, ...], Field(max_length=20_000)] = ()
    baseline_digest: Digest | None = None
    current_digest: Digest | None = None


class MaintenanceSimulation(MaintenanceModel):
    """A review envelope, deliberately without intents or executable instructions."""

    mode: Literal["offline"] = "offline"
    executable: Literal[False] = False
    state: Literal["blocked", "review_required"] = "blocked"
    baseline_digest: Digest | None = None
    unresolved_requirements: Annotated[tuple[Code, ...], Field(min_length=1, max_length=32)]

    @field_validator("executable", mode="before")
    @classmethod
    def require_false(cls, value):
        if value is not False:
            raise ValueError("Execution is unavailable")
        return value


class RecoveryEvidenceReview(MaintenanceModel):
    mode: Literal["offline"] = "offline"
    executable: Literal[False] = False
    recoverability: Literal["unknown", "blocked", "conditional"]
    baseline_digest: Digest | None = None
    missing_states: Annotated[tuple[Code, ...], Field(min_length=1, max_length=32)]
    functional_verification_needed: Literal[True] = True

    @field_validator("executable", mode="before")
    @classmethod
    def require_false(cls, value):
        if value is not False:
            raise ValueError("Execution is unavailable")
        return value

    @field_validator("functional_verification_needed", mode="before")
    @classmethod
    def require_true(cls, value):
        if value is not True:
            raise ValueError("Functional verification is required")
        return value
