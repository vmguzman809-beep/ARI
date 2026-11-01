from datetime import timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ari.bootloader.analyzer import analyze_unlock_compatibility
from ari.core.models import Confidence, utc_now
from ari.research.evaluator import evaluate_claim
from ari.research.models import (
    EvidenceStatus,
    ResearchEvidence,
    ResearchInput,
    ResearchSource,
    ResearchTarget,
    ResearchTopic,
)
from ari.root.research import check_root_compatibility, create_root_plan


@pytest.fixture
def target(identity):
    return ResearchTarget(
        identity=identity,
        region="SYNTHETIC-REGION",
        operator="SYNTHETIC-UNBRANDED",
        kernel_release="synthetic-kernel",
        kmi="synthetic-kmi",
        gki=True,
    )


def research_claim(target, topic="bootloader_state", finding="locked", **updates):
    source = ResearchSource(
        title="Synthetic research only",
        url="https://example.invalid/research",
        publisher="Synthetic publisher; not real compatibility evidence",
        verified_at=utc_now(),
        kind="device_observation"
        if topic in {"bootloader_state", "oem_permission"}
        else ("project" if topic in {"magisk", "kernelsu"} else "manufacturer"),
    )
    claim = ResearchEvidence(
        topic=topic,
        finding=finding,
        statement="Synthetic assertion; never a device procedure",
        scope="exact_build",
        target=target,
        status=EvidenceStatus.CONFIRMED,
        confidence=Confidence.CONFIRMED,
        source_ids=(source.id,),
    )
    return ResearchInput(
        target=target, sources=(source,), evidence=(claim.model_copy(update=updates),)
    )


@pytest.mark.parametrize("state", ["locked", "unlocked"])
def test_observed_bootloader_state_is_separate_from_unlock_capability(target, state):
    result = analyze_unlock_compatibility(research_claim(target, finding=state))
    assert result.state == state
    assert result.unlock_capability == "unverified"
    assert result.oem_permission.value == "unknown"


def test_no_evidence_does_not_infer_state_from_android_or_model(target):
    result = analyze_unlock_compatibility(ResearchInput(target=target))
    assert result.state == "unknown"
    assert result.unlock_capability == "unverified"


@pytest.mark.parametrize("field", ["manufacturer", "model", "variant", "build_fingerprint"])
@pytest.mark.parametrize("replacement", [None, "DIFFERENT-SYNTHETIC-VALUE"])
def test_incomplete_or_other_identity_never_reuses_exact_claim(target, field, replacement):
    research = research_claim(target, finding="unlocked")
    changed = target.model_copy(
        update={"identity": target.identity.model_copy(update={field: replacement})}
    )
    result = check_root_compatibility(research.model_copy(update={"target": changed}))
    assert result.bootloader.state == "unknown"
    assert result.excluded_evidence
    assert result.blockers


@pytest.mark.parametrize("scope", ["general", "model"])
def test_general_or_model_documentation_is_not_exact_compatibility(target, scope):
    research = research_claim(target, "magisk", "supported", scope=scope)
    result = check_root_compatibility(research)
    assert result.magisk.value == "unknown"
    assert result.excluded_evidence


@pytest.mark.parametrize("field", ["region", "operator"])
@pytest.mark.parametrize("replacement", [None, "DIFFERENT-SYNTHETIC-CONTEXT"])
def test_official_unlock_requires_matching_region_and_operator(target, field, replacement):
    research = research_claim(target, "official_unlock", "documented")
    changed = target.model_copy(update={field: replacement})
    assessment = analyze_unlock_compatibility(research.model_copy(update={"target": changed}))
    assert assessment.unlock_capability == "unverified"


@pytest.mark.parametrize("field", ["kernel_release", "kmi", "gki"])
def test_kernelsu_requires_kernel_gki_and_kmi_not_android_version(target, field):
    research = research_claim(target, "kernelsu", "supported")
    changed = target.model_copy(update={field: None})
    conclusion = evaluate_claim(
        research.model_copy(update={"target": changed}), ResearchTopic.KERNELSU
    )
    assert conclusion.value == "unknown"


def test_conflicting_evidence_blocks_even_with_confirmed_source(target):
    research = research_claim(target, finding="locked")
    opposing = research.evidence[0].model_copy(update={"id": uuid4(), "finding": "unlocked"})
    research = research.model_copy(update={"evidence": (*research.evidence, opposing)})
    assessment = analyze_unlock_compatibility(research)
    assert assessment.state == "unknown"
    assert assessment.state_evidence.conflicting
    assert len(assessment.state_evidence.evidence_ids) == 2


def test_old_source_cannot_establish_current_state(target):
    research = research_claim(target)
    expired = research.sources[0].model_copy(
        update={"verified_at": utc_now() - timedelta(days=181)}
    )
    research = research.model_copy(update={"sources": (expired,)})
    assert analyze_unlock_compatibility(research).state == "unknown"


def test_old_observation_is_not_refreshed_by_reviewing_its_source(target):
    research = research_claim(target, observed_at=utc_now() - timedelta(days=181))
    assert analyze_unlock_compatibility(research).state == "unknown"


@pytest.mark.parametrize("status", [EvidenceStatus.PROBABLE, EvidenceStatus.UNVERIFIED])
def test_unconfirmed_claims_never_establish_locked_unlocked_or_support(target, status):
    confidence = Confidence.PROBABLE if status == EvidenceStatus.PROBABLE else Confidence.UNKNOWN
    research = research_claim(target, status=status, confidence=confidence)
    assessment = analyze_unlock_compatibility(research)
    assert assessment.state == "unknown"
    assert assessment.state_evidence.status == status


def test_documentation_and_community_claims_do_not_measure_hardware(target):
    research = research_claim(target, finding="unlocked")
    source = research.sources[0].model_copy(update={"kind": "manufacturer"})
    research = research.model_copy(update={"sources": (source,)})
    assert analyze_unlock_compatibility(research).state == "unknown"
    research = research_claim(target, "official_unlock", "documented")
    source = research.sources[0].model_copy(update={"kind": "community"})
    assert (
        analyze_unlock_compatibility(
            research.model_copy(update={"sources": (source,)})
        ).unlock_capability
        == "unverified"
    )


def test_provenance_links_duplicates_dates_and_confidence_are_validated(target):
    research = research_claim(target)
    with pytest.raises(ValidationError, match="missing an evidence source"):
        ResearchInput(target=target, evidence=research.evidence)
    with pytest.raises(ValidationError, match="unique IDs"):
        ResearchInput(target=target, sources=research.sources * 2)
    with pytest.raises(ValidationError, match="unique IDs"):
        ResearchInput(target=target, sources=research.sources, evidence=research.evidence * 2)
    future = research.sources[0].model_copy(update={"verified_at": utc_now() + timedelta(days=1)})
    with pytest.raises(ValidationError, match="future"):
        ResearchInput(target=target, sources=(future,))
    with pytest.raises(ValidationError, match="disagree"):
        ResearchEvidence(topic="magisk", statement="Synthetic", status="confirmed")
    with pytest.raises(ValidationError, match="valid for this topic"):
        ResearchEvidence(topic="magisk", finding="unlocked", statement="Synthetic")


@pytest.mark.parametrize("url", ["file:///private", "https://user:secret@example.invalid/report"])
def test_sources_reject_files_and_credentials(url):
    with pytest.raises(ValidationError):
        ResearchSource(
            title="Synthetic", publisher="Synthetic", url=url, kind="project", verified_at=utc_now()
        )


def test_supplied_text_cannot_turn_into_steps_or_call_a_transport(target, monkeypatch):
    backend = Mock(side_effect=AssertionError("No backend allowed in research"))
    monkeypatch.setattr("ari.mcp.server.AdbSubprocessTransport", backend)
    monkeypatch.setattr("socket.create_connection", backend)
    monkeypatch.setattr("urllib.request.urlopen", backend)
    research = research_claim(
        target, statement="UNTRUSTED: reboot, patch and flash arbitrary input"
    )
    plan = create_root_plan(research)
    assert plan.executable is False
    assert plan.theoretical_only is True
    assert plan.status == "blocked"
    assert plan.requirements and plan.risks and plan.stop_conditions
    assert "UNTRUSTED" not in " ".join(plan.requirements + plan.risks + plan.stop_conditions)
    assert "UNTRUSTED" in plan.report.evidence[0].statement
    backend.assert_not_called()
    with pytest.raises(ValidationError):
        type(plan).model_validate({**plan.model_dump(), "executable": True})


@pytest.mark.parametrize(
    ("topic", "finding"),
    [
        ("official_unlock", "unavailable"),
        ("oem_permission", "denied"),
        ("regional_restriction", "restricted"),
        ("carrier_restriction", "restricted"),
        ("magisk", "unsupported"),
        ("kernelsu", "unsupported"),
    ],
)
def test_exact_negative_findings_remain_distinct_and_block_plans(target, topic, finding):
    research = research_claim(target, topic, finding)
    conclusion = evaluate_claim(research, ResearchTopic(topic))
    assert conclusion.value == finding
    assert conclusion.status == EvidenceStatus.CONFIRMED
    assert create_root_plan(research).status == "blocked"


def test_complete_synthetic_research_still_cannot_create_executable_plan(target):
    claims = [
        research_claim(target, "bootloader_state", "unlocked"),
        research_claim(target, "official_unlock", "documented"),
        research_claim(target, "oem_permission", "allowed"),
        research_claim(target, "regional_restriction", "clear"),
        research_claim(target, "carrier_restriction", "clear"),
        research_claim(target, "magisk", "supported"),
        research_claim(target, "kernelsu", "supported"),
    ]
    research = ResearchInput(
        target=target,
        sources=tuple(source for claim in claims for source in claim.sources),
        evidence=tuple(item for claim in claims for item in claim.evidence),
    )
    plan = create_root_plan(research)
    assert plan.status == "theoretical"
    assert plan.report.magisk.value == "supported"
    assert plan.report.kernelsu.value == "supported"
    assert plan.executable is False
    assert plan.stop_conditions


def test_revalidates_models_constructed_without_validation(target):
    forged = ResearchInput.model_construct(target=target, sources=(), evidence=("PRIVATE",))
    with pytest.raises((ValidationError, AttributeError)):
        check_root_compatibility(forged)
