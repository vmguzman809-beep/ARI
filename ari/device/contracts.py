from typing import Protocol

from ari.device.adb import AdbConnection, AdbInventory, AdbProperties, DeviceInspection


class DeviceInspector(Protocol):
    """Read-only diagnosis. Inventory hints never substitute for property observations."""

    def detect_devices(self) -> AdbInventory: ...

    def inspect_device(self, serial: str) -> DeviceInspection: ...

    def get_device_properties(self, serial: str) -> AdbProperties: ...

    def inspect_adb_status(self, serial: str) -> AdbConnection: ...
