"""Explicit lifecycle: importing ARI never creates storage or launches processes."""

from types import TracebackType
from uuid import uuid4

from ari.core.logging import close_logging, configure_logging
from ari.core.settings import Settings
from ari.knowledge.database import Database
from ari.knowledge.models import AuditEvent
from ari.knowledge.repository import KnowledgeRepository


class AriRuntime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.run_id = uuid4()
        self.database = Database(settings.database_path)
        self.repository = KnowledgeRepository(self.database)
        self._started = False

    def __enter__(self) -> "AriRuntime":
        if self._started:
            raise RuntimeError("Runtime is already open")
        logger = configure_logging(self.settings.log_path, self.run_id)
        try:
            self.database.initialize()
            self.repository.record_event(
                AuditEvent(
                    run_id=self.run_id,
                    operation="runtime_started",
                    outcome="recorded",
                    result="Phase 1 foundation initialized; no device access",
                )
            )
            logger.info("runtime_started")
        except Exception:
            logger.error("runtime_start_failed")
            self.database.close()
            close_logging()
            raise
        self._started = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.database.close()
        close_logging()
        self._started = False
