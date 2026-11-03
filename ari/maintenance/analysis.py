"""Pure conservative policy, immutable baseline creation and offline comparisons."""

from datetime import UTC, datetime
from uuid import uuid4

from ari.maintenance.models import (
    Baseline,
    DriftReport,
    KnowledgeState,
    PackageDifference,
    PackageRiskAssessment,
    PackageSnapshot,
    snapshot_digest,
)
from ari.maintenance.parser import MaintenanceError, validated

# Conservative name hints, authored for ARI. Not a completeness claim or allowlist.
# Observed critical functions protect vendor packages regardless of spelling.
# Absence from these hints never grants modification permission.
_CRITICAL_NAMES = frozenset(
    {
        "android",
        "com.android.phone",
        "com.android.systemui",
        "com.android.settings",
        "com.android.permissioncontroller",
        "com.google.android.permissioncontroller",
        "com.android.packageinstaller",
        "com.google.android.packageinstaller",
        "com.android.providers.telephony",
        "com.android.providers.contacts",
        "com.android.providers.calendar",
        "com.android.providers.blockednumber",
        "com.android.networkstack",
        "com.android.carrierconfig",
        "com.android.euicc",
        "com.android.mms",
        "com.android.messaging",
        "com.android.dialer",
        "com.google.android.dialer",
        "com.google.android.apps.messaging",
        "com.android.managedprovisioning",
        "com.android.keychain",
    }
)
_CRITICAL_TOKENS = frozenset(
    {"ims", "telephony", "euicc", "systemui", "permissioncontroller", "inputmethod"}
)


def _contradictions(snapshot: PackageSnapshot) -> set[str]:
    claims: dict[tuple[str, str], set[str]] = {}
    conflicting = set()
    for item in snapshot.evidence:
        if item.state == KnowledgeState.CONTRADICTORY:
            conflicting.add(item.subject)
        if item.state == KnowledgeState.KNOWN and item.value is not None:
            claims.setdefault((item.subject, item.claim), set()).add(item.value)
    for (subject, _), values in claims.items():
        if len(values) > 1:
            conflicting.add(subject)
    conflicting.update(
        p.package_id for p in snapshot.packages if p.knowledge == KnowledgeState.CONTRADICTORY
    )
    return conflicting


def _uncertainty(snapshot: PackageSnapshot) -> tuple[str, ...]:
    reasons = []
    if snapshot.coverage != "complete" or not snapshot.packages or snapshot.limitations:
        reasons.append("incomplete_inventory")
    if not snapshot.identity.complete():
        reasons.append("incomplete_identity")
        # Only static field names, never identity values, enter diagnostic codes.
        reasons.extend(
            f"identity_{field}_missing"
            for field in type(snapshot.identity).model_fields
            if getattr(snapshot.identity, field) is None
        )
    if snapshot.user_scope.profile_kind == "unknown":
        reasons.append("unknown_profile")
    if _contradictions(snapshot):
        reasons.append("contradictory_evidence")
    if any(p.knowledge != KnowledgeState.KNOWN for p in snapshot.packages) or any(
        e.state != KnowledgeState.KNOWN for e in snapshot.evidence
    ):
        reasons.append("unresolved_observations")
    if any(p.origin == "unknown" for p in snapshot.packages):
        reasons.append("unknown_origin")
    if any(not p.functions_complete for p in snapshot.packages):
        reasons.append("incomplete_classification")
    package_ids = {p.package_id for p in snapshot.packages}
    if any(
        p.dependencies is None or any(d not in package_ids for d in p.dependencies)
        for p in snapshot.packages
    ):
        reasons.append("unresolved_dependencies")
    return tuple(reasons)


def assess_package_risks(snapshot: PackageSnapshot) -> tuple[PackageRiskAssessment, ...]:
    snapshot = validated(snapshot, PackageSnapshot)
    if not snapshot.packages:
        # An empty risk list could be mistaken for a clean inventory.
        raise MaintenanceError("inventory_empty")
    packages = {p.package_id: p for p in snapshot.packages}
    protected = {
        p.package_id
        for p in snapshot.packages
        if p.critical_functions
        or p.package_id in _CRITICAL_NAMES
        or set(p.package_id.lower().split(".")) & _CRITICAL_TOKENS
    }
    # Protect the transitive prerequisites of a protected package, including cycles.
    pending = list(protected)
    while pending:
        package = packages[pending.pop()]
        for dependency in package.dependencies or ():
            if dependency in packages and dependency not in protected:
                protected.add(dependency)
                pending.append(dependency)
    uncertainty = _uncertainty(snapshot)
    conflicts = _contradictions(snapshot)
    confidence = (
        "unknown"
        if uncertainty
        else "low"
        if any(e.confidence == "low" for e in snapshot.evidence)
        else "high"
    )
    results = []
    for package in snapshot.packages:
        reasons = list(uncertainty)
        if package.package_id in protected:
            decision = "protected"
            severity = "critical"
            reasons.append("critical_function_or_dependency")
        elif reasons:
            decision = "blocked"
            severity = "high"
        else:
            decision = "review_required"
            severity = "unknown"
            reasons.append("no_modification_authority")
        if package.package_id in conflicts:
            state = KnowledgeState.CONTRADICTORY
        elif package.knowledge == KnowledgeState.BLOCKED:
            state = KnowledgeState.BLOCKED
        elif uncertainty:
            state = KnowledgeState.UNKNOWN
        else:
            state = KnowledgeState.KNOWN
        results.append(
            PackageRiskAssessment(
                package_id=package.package_id,
                decision=decision,
                severity=severity,
                confidence=confidence,
                state=state,
                reasons=tuple(reasons),
                evidence_ids=package.evidence_ids,
            )
        )
    return tuple(results)


def create_baseline(snapshot: PackageSnapshot) -> Baseline:
    snapshot = validated(snapshot, PackageSnapshot)
    if _uncertainty(snapshot):
        raise MaintenanceError("baseline_incomplete")
    return Baseline(
        baseline_id=uuid4(),
        created_at=datetime.now(UTC),
        snapshot=snapshot,
        content_sha256=snapshot_digest(snapshot),
    )


def compare_snapshots(baseline: Baseline | None, current: PackageSnapshot) -> DriftReport:
    """Compare declared observations only; never verify install/uninstall events.

    No package differences are emitted for incompatible or incomplete evidence.
    Source-declared complete coverage cannot prove that unlisted packages are absent.
    """
    current = validated(current, PackageSnapshot)
    if baseline is None:
        return DriftReport(
            state=KnowledgeState.BLOCKED, comparable=False, reasons=("baseline_missing",)
        )
    try:
        baseline = validated(baseline, Baseline)
    except MaintenanceError:
        return DriftReport(
            state=KnowledgeState.BLOCKED, comparable=False, reasons=("baseline_invalid",)
        )
    previous = baseline.snapshot
    reasons = list(dict.fromkeys((*_uncertainty(previous), *_uncertainty(current))))
    if previous.identity != current.identity:
        reasons.append("identity_mismatch")
    if previous.user_scope != current.user_scope:
        reasons.append("profile_mismatch")
    if previous.captured_at > current.captured_at:
        reasons.append("capture_order_invalid")
    if reasons:
        state = (
            KnowledgeState.CONTRADICTORY
            if "contradictory_evidence" in reasons
            else KnowledgeState.BLOCKED
        )
        return DriftReport(state=state, comparable=False, reasons=tuple(reasons))
    before = {p.package_id: p for p in previous.packages}
    after = {p.package_id: p for p in current.packages}
    changes = []
    # Evidence IDs may differ across exports; they are provenance, not package state.
    fields = tuple(f for f in type(current.packages[0]).model_fields if f != "evidence_ids")
    for name in sorted(before.keys() | after.keys()):
        if name not in before or name not in after:
            changes.append(
                PackageDifference(
                    package_id=name,
                    fields=(),
                    kind="not_observed_before" if name not in before else "not_observed_after",
                )
            )
        else:
            different = tuple(
                f for f in fields if getattr(before[name], f) != getattr(after[name], f)
            )
            if different:
                changes.append(PackageDifference(package_id=name, fields=different, kind="changed"))
    return DriftReport(
        state=KnowledgeState.KNOWN,
        comparable=True,
        reasons=(),
        differences=tuple(changes),
        baseline_digest=baseline.content_sha256,
        current_digest=snapshot_digest(current),
    )
