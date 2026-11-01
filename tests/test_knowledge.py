from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ari.core.errors import SchemaVersionError
from ari.core.models import Confidence, Evidence
from ari.device.models import DeviceIdentity, DeviceSnapshot
from ari.knowledge.database import Database
from ari.knowledge.models import AuditEvent, KnowledgeEntry
from ari.knowledge.repository import KnowledgeRepository


def make_entry(identity, source):
    return KnowledgeEntry(
        identity=identity,
        evidence=Evidence(
            statement="Synthetic finding, not an Android compatibility result",
            confidence=Confidence.CONFIRMED,
            source_ids=(source.id,),
        ),
        firmware_version="fixture-1",
        firmware_sha256="a" * 64,
        documented_method="synthetic-only",
    )


def test_storage_survives_reopen(database, repository, identity, source):
    snapshot = DeviceSnapshot(identity=identity, serial="TEST-ONLY", provenance="Mock fixture")
    entry = make_entry(identity, source)
    event = AuditEvent(
        run_id=uuid4(),
        snapshot_id=snapshot.id,
        operation="fixture_recorded",
        outcome="simulated",
        result="No device accessed",
    )
    repository.record_snapshot(snapshot)
    repository.add_source(source)
    repository.add_entry(entry)
    repository.record_event(event)
    database.close()
    reopened = Database(database.path)
    try:
        reopened.initialize()
        stored = KnowledgeRepository(reopened)
        assert stored.get_snapshot(snapshot.id) == snapshot
        assert stored.get_source(source.id) == source
        assert stored.find_entries(identity) == (entry,)
        assert stored.events_for_run(event.run_id) == (event,)
        assert stored.events_for_run(uuid4()) == ()
    finally:
        reopened.close()


@pytest.mark.parametrize("field", ["manufacturer", "model", "variant", "build_fingerprint"])
def test_knowledge_does_not_cross_identity_boundaries(repository, identity, source, field):
    repository.add_source(source)
    repository.add_entry(make_entry(identity, source))
    different = DeviceIdentity.model_validate({**identity.model_dump(), field: "DIFFERENT"})
    assert repository.find_entries(different) == ()


def test_incomplete_query_is_rejected(repository):
    with pytest.raises(ValueError, match="Exact manufacturer"):
        repository.find_entries(DeviceIdentity(model="Test Phone"))


def test_unknown_source_rolls_back_entry(repository, identity, source):
    with pytest.raises(ValueError, match="persisted first"):
        repository.add_entry(make_entry(identity, source))
    assert repository.find_entries(identity) == ()


def test_foreign_keys_prevent_orphan_history(repository):
    event = AuditEvent(
        run_id=uuid4(), snapshot_id=uuid4(), operation="test", outcome="blocked", result="test"
    )
    with pytest.raises(IntegrityError):
        repository.record_event(event)
    assert repository.events_for_run(event.run_id) == ()


def test_schema_initialization_is_idempotent(database, repository, identity):
    snapshot = DeviceSnapshot(identity=identity, provenance="Synthetic fixture")
    repository.record_snapshot(snapshot)
    database.initialize()
    assert repository.get_snapshot(snapshot.id) == snapshot
    assert repository.get_snapshot(uuid4()) is None
    assert repository.get_source(uuid4()) is None


def test_future_schema_is_rejected_without_rewriting(database):
    with database.engine.begin() as connection:
        connection.execute(text("UPDATE schema_version SET version = 99"))
    with pytest.raises(SchemaVersionError):
        database.initialize()
    with database.engine.connect() as connection:
        assert connection.execute(text("SELECT version FROM schema_version")).scalar_one() == 99


def test_unversioned_database_is_not_adopted(tmp_path):
    db = Database(tmp_path / "existing.sqlite3")
    try:
        with db.engine.begin() as connection:
            connection.execute(text("CREATE TABLE user_data (value TEXT)"))
            connection.execute(text("INSERT INTO user_data VALUES ('preserve me')"))
        with pytest.raises(SchemaVersionError, match="Unversioned"):
            db.initialize()
        with db.engine.connect() as connection:
            assert (
                connection.execute(text("SELECT value FROM user_data")).scalar_one()
                == "preserve me"
            )
    finally:
        db.close()
