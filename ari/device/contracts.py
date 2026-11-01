from typing import Protocol

from ari.device.models import DeviceSnapshot


class DeviceInspector(Protocol):
    """Future bounded adapter; implementations must select an explicit target."""

    def detect_devices(self) -> tuple[DeviceSnapshot, ...]: ...

    def inspect_device(self, serial: str) -> DeviceSnapshot: ...
