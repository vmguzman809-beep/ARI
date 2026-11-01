"""Versioned SQLite foundation. Schema changes require explicit future migrations."""

from pathlib import Path
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ari.core.errors import SchemaVersionError

SCHEMA_VERSION = 1


class Base(DeclarativeBase):
    pass


class SchemaRow(Base):
    __tablename__ = "schema_version"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer)


class SnapshotRow(Base):
    __tablename__ = "device_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class SourceRow(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class FindingRow(Base):
    __tablename__ = "knowledge_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    exact_key: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class FindingSourceRow(Base):
    __tablename__ = "knowledge_sources"
    entry_id: Mapped[str] = mapped_column(ForeignKey("knowledge_entries.id"), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), primary_key=True)


class AuditRow(Base):
    __tablename__ = "operation_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("device_snapshots.id"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


def _enable_foreign_keys(connection: Any, _record: Any) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        # URL.create handles spaces and non-ASCII characters without string escaping.
        from sqlalchemy import URL

        self.engine: Engine = create_engine(URL.create("sqlite", database=str(self.path)))
        event.listen(self.engine, "connect", _enable_foreign_keys)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.engine.begin() as connection:
            tables = set(inspect(connection).get_table_names())
            if tables:
                if "schema_version" not in tables:
                    raise SchemaVersionError("Unversioned database; automatic adoption refused")
                rows = connection.execute(SchemaRow.__table__.select()).all()
                if len(rows) != 1 or rows[0].id != 1 or rows[0].version != SCHEMA_VERSION:
                    raise SchemaVersionError(
                        "Unsupported SQLite schema; explicit migration required"
                    )
                if tables != set(Base.metadata.tables):
                    raise SchemaVersionError("Incomplete or unexpected SQLite schema")
                return
            Base.metadata.create_all(connection)
            connection.execute(SchemaRow.__table__.insert().values(id=1, version=SCHEMA_VERSION))

    def close(self) -> None:
        self.engine.dispose()
