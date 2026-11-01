"""Small transaction boundaries; SQL parameters never contain executable instructions."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ari.core.models import SourceReference
from ari.device.models import DeviceIdentity, DeviceSnapshot
from ari.knowledge.database import (
    AuditRow,
    Database,
    FindingRow,
    FindingSourceRow,
    SnapshotRow,
    SourceRow,
)
from ari.knowledge.models import AuditEvent, KnowledgeEntry


class KnowledgeRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def record_snapshot(self, snapshot: DeviceSnapshot) -> UUID:
        with Session(self.database.engine) as session, session.begin():
            session.add(SnapshotRow(id=str(snapshot.id), payload=snapshot.model_dump(mode="json")))
        return snapshot.id

    def get_snapshot(self, snapshot_id: UUID) -> DeviceSnapshot | None:
        with Session(self.database.engine) as session:
            row = session.get(SnapshotRow, str(snapshot_id))
            return DeviceSnapshot.model_validate(row.payload) if row else None

    def add_source(self, source: SourceReference) -> UUID:
        with Session(self.database.engine) as session, session.begin():
            session.add(SourceRow(id=str(source.id), payload=source.model_dump(mode="json")))
        return source.id

    def get_source(self, source_id: UUID) -> SourceReference | None:
        with Session(self.database.engine) as session:
            row = session.get(SourceRow, str(source_id))
            return SourceReference.model_validate(row.payload) if row else None

    def add_entry(self, entry: KnowledgeEntry) -> UUID:
        with Session(self.database.engine) as session, session.begin():
            for source_id in entry.evidence.source_ids:
                if session.get(SourceRow, str(source_id)) is None:
                    raise ValueError(f"Source must be persisted first: {source_id}")
            session.add(
                FindingRow(
                    id=str(entry.id),
                    exact_key=entry.identity.exact_key(),
                    payload=entry.model_dump(mode="json"),
                )
            )
            session.flush()
            session.add_all(
                FindingSourceRow(entry_id=str(entry.id), source_id=str(source_id))
                for source_id in entry.evidence.source_ids
            )
        return entry.id

    def find_entries(self, identity: DeviceIdentity) -> tuple[KnowledgeEntry, ...]:
        key = identity.exact_key()
        with Session(self.database.engine) as session:
            rows = session.scalars(
                select(FindingRow).where(FindingRow.exact_key == key).order_by(FindingRow.id)
            )
            return tuple(KnowledgeEntry.model_validate(row.payload) for row in rows)

    def record_event(self, event: AuditEvent) -> UUID:
        with Session(self.database.engine) as session, session.begin():
            session.add(
                AuditRow(
                    id=str(event.id),
                    run_id=str(event.run_id),
                    snapshot_id=str(event.snapshot_id) if event.snapshot_id else None,
                    payload=event.model_dump(mode="json"),
                )
            )
        return event.id

    def events_for_run(self, run_id: UUID) -> tuple[AuditEvent, ...]:
        with Session(self.database.engine) as session:
            events = (
                AuditEvent.model_validate(row.payload)
                for row in session.scalars(select(AuditRow).where(AuditRow.run_id == str(run_id)))
            )
            return tuple(
                sorted(
                    events,
                    key=lambda event: event.occurred_at,
                )
            )
