import json
from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ari.core.models import Confidence, Evidence, SourceReference
from ari.device.models import DeviceIdentity
from ari.firmware.contracts import FirmwareArtifact
from ari.knowledge.models import KnowledgeEntry
from ari.reporting.models import EvidenceReport


@pytest.mark.parametrize("confidence", [Confidence.CONFIRMED, Confidence.PROBABLE])
def test_non_unknown_evidence_requires_a_source(confidence):
    with pytest.raises(ValidationError, match="requires a source"):
        Evidence(statement="Unsupported claim", confidence=confidence)


def test_unknown_is_not_promoted_to_confirmed():
    assert Evidence(statement="Bootloader state unavailable").confidence == Confidence.UNKNOWN
    assert DeviceIdentity().variant is None


def test_source_requires_http_url_and_timezone():
    with pytest.raises(ValidationError):
        SourceReference(title="Bad source", url="file:///tmp/source", verified_at=datetime.now())
    with pytest.raises(ValidationError):
        SourceReference(
            title="Bad timestamp", url="https://example.invalid", verified_at=datetime.now()
        )


def test_extra_fields_and_blank_identity_are_rejected():
    with pytest.raises(ValidationError):
        DeviceIdentity(model="   ")
    with pytest.raises(ValidationError):
        DeviceIdentity(model="Test", command="fastboot flash boot")


def test_partial_identity_cannot_become_variant_knowledge():
    with pytest.raises(ValidationError, match="Exact manufacturer"):
        KnowledgeEntry(
            identity=DeviceIdentity(model="Test"), evidence=Evidence(statement="Unknown")
        )


def test_hash_format_does_not_imply_hash_was_computed(identity, tmp_path):
    with pytest.raises(ValidationError):
        FirmwareArtifact(path=tmp_path / "boot.img", identity=identity, sha256="invalid")
    artifact = FirmwareArtifact(path=tmp_path / "absent.img", identity=identity)
    assert artifact.sha256 is None
    assert artifact.partition == "unknown"


def test_report_preserves_uncertainty_and_provenance(source):
    evidence = Evidence(
        statement="Synthetic observation",
        confidence=Confidence.PROBABLE,
        source_ids=(source.id,),
    )
    report = EvidenceReport(title="Test only", evidence=(evidence,), sources=(source,))
    data = json.loads(report.as_json())
    assert data["evidence"][0]["confidence"] == "probable"
    assert data["sources"][0]["id"] == str(source.id)
    assert data["limitations"]
    with pytest.raises(ValidationError, match="missing an evidence source"):
        EvidenceReport(title="Incomplete", evidence=(evidence,))


def test_duplicate_evidence_sources_are_rejected():
    source_id = uuid4()
    with pytest.raises(ValidationError, match="unique"):
        Evidence(statement="Test", source_ids=(source_id, source_id))
