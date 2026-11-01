import json
import logging
from unittest.mock import patch
from uuid import uuid4

import pytest

from ari.core.logging import close_logging, configure_logging
from ari.core.runtime import AriRuntime
from ari.core.settings import Settings


def test_runtime_explicitly_initializes_local_storage(tmp_path, capsys):
    settings = Settings(data_dir=tmp_path / "runtime")
    runtime = AriRuntime(settings)
    assert not settings.data_dir.exists()
    with runtime:
        assert settings.database_path.is_file()
        assert runtime.repository.events_for_run(runtime.run_id)[0].operation == "runtime_started"
        with pytest.raises(RuntimeError, match="already open"):
            runtime.__enter__()
    output = capsys.readouterr()
    assert output.out == ""
    assert [json.loads(line)["event"] for line in output.err.splitlines()] == [
        "runtime_started",
        "runtime_stopped",
    ]
    assert logging.getLogger("ari").handlers == []


def test_logs_do_not_leak_free_text_exceptions_or_extra_fields(tmp_path, capsys):
    log_path = tmp_path / "logs" / "ari.jsonl"
    run_id = uuid4()
    logger = configure_logging(log_path, run_id)
    try:
        logger.info("runtime_started", extra={"serial": "sensitive123"})
        logger.info("sensitive123")
        try:
            raise ValueError("secret exception data")
        except ValueError:
            logger.exception("device properties sensitive123")
        # Reconfiguration must close prior handlers, not duplicate output.
        logger = configure_logging(log_path, run_id)
        logger.info("device_operation_blocked")
    finally:
        close_logging()
    output = capsys.readouterr()
    data = log_path.read_text(encoding="utf-8")
    assert output.out == ""
    assert "sensitive123" not in data + output.err
    assert "secret exception data" not in data + output.err
    events = [json.loads(line) for line in data.splitlines()]
    assert len(events) == 4
    assert all(event["run_id"] == str(run_id) for event in events)
    assert events[1]["event"] == "unstructured_event_redacted"
    assert events[-1]["event"] == "device_operation_blocked"


def test_failed_startup_closes_logs_and_database(tmp_path):
    runtime = AriRuntime(Settings(data_dir=tmp_path / "failure"))
    with patch.object(runtime.database, "initialize", side_effect=RuntimeError("fixture failure")):
        with patch.object(runtime.database, "close") as close:
            with pytest.raises(RuntimeError, match="fixture failure"):
                runtime.__enter__()
            close.assert_called_once()
    assert logging.getLogger("ari").handlers == []
