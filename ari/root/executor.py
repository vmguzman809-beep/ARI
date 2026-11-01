from ari.core.errors import PhaseUnavailableError
from ari.security.policy import DeviceOperation


class DisabledRootExecutor:
    """No command, script, approval token or transport can be supplied here."""

    def execute(self, operation: DeviceOperation) -> None:
        if not isinstance(operation, DeviceOperation):
            raise TypeError("A typed DeviceOperation is required")
        raise PhaseUnavailableError("Root execution is unavailable in phase 4")
