import pytest
from pydantic import ValidationError

from ari.core.errors import PhaseUnavailableError
from ari.core.settings import Settings
from ari.root.executor import DisabledRootExecutor
from ari.security.policy import DeviceOperation, PhaseOnePolicy


@pytest.mark.parametrize("operation", list(DeviceOperation))
def test_every_device_operation_is_denied_even_in_simulation(operation):
    decision = PhaseOnePolicy().evaluate(operation)
    assert decision.allowed is False
    assert decision.simulation is True
    with pytest.raises(PhaseUnavailableError, match="phase 1"):
        DisabledRootExecutor().execute(operation)


def test_arbitrary_commands_are_not_an_operation():
    with pytest.raises(TypeError, match="typed DeviceOperation"):
        DisabledRootExecutor().execute("fastboot flash boot evil.img")


@pytest.mark.parametrize("field", ["read_only", "simulation"])
def test_config_cannot_enable_device_writes(tmp_path, field):
    with pytest.raises(ValidationError):
        Settings.model_validate({"data_dir": tmp_path, field: False})


def test_only_storage_location_is_read_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("ARI_DATA_DIR", str(tmp_path / "datos ñ"))
    monkeypatch.setenv("ARI_READ_ONLY", "false")
    monkeypatch.setenv("ARI_SIMULATION", "false")
    settings = Settings.from_environment()
    assert settings.data_dir == (tmp_path / "datos ñ").resolve()
    assert settings.read_only is True
    assert settings.simulation is True
    assert not settings.data_dir.exists()


def test_empty_data_directory_is_invalid(monkeypatch):
    monkeypatch.setenv("ARI_DATA_DIR", " ")
    with pytest.raises(ValueError, match="empty"):
        Settings.from_environment()
