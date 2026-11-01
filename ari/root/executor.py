from ari.security.policy import DeviceOperation, PhaseOnePolicy


class DisabledRootExecutor:
    """No command, script, approval token or transport can be supplied here."""

    def execute(self, operation: DeviceOperation) -> None:
        PhaseOnePolicy().require(operation)
