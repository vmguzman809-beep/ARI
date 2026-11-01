"""Explicit synthetic server for real-Codex verification, never a production backend switch."""

from ari.core.runtime import AriRuntime
from ari.core.settings import Settings
from ari.device.adb import AdbReadOperation, AdbRequest, DeviceProperty
from ari.device.inspector import AdbDeviceInspector
from ari.mcp.server import create_server


class SyntheticTransport:
    def execute(self, request: AdbRequest) -> str:
        if request.operation == AdbReadOperation.DEVICES:
            return (
                "List of devices attached\n"
                "SYNTHETIC-CODEX-1 device\n"
                "SYNTHETIC-CODEX-2 offline\n"
                "SYNTHETIC-CODEX-3 unauthorized\n"
            )
        if request.operation == AdbReadOperation.STATE:
            return "device\n"
        values = {
            DeviceProperty.MANUFACTURER: "SYNTHETIC; NO HARDWARE",
            DeviceProperty.MODEL: "Codex Test Fixture",
            DeviceProperty.DEVICE: "synthetic_codename",
            DeviceProperty.PRODUCT_NAME: "synthetic_product",
            DeviceProperty.HARDWARE_SKU: "TEST-SKU",
            DeviceProperty.ODM_SKU: "TEST-ODM",
            DeviceProperty.BUILD_ID: "TEST.BUILD",
            DeviceProperty.FINGERPRINT: "synthetic/codex/fixture:0/test/release",
            DeviceProperty.ANDROID_RELEASE: "synthetic-only",
            DeviceProperty.SDK_LEVEL: "999",
            DeviceProperty.ABI_LIST: "arm64-v8a",
            DeviceProperty.CPU_ABI: "arm64-v8a",
        }
        return values[request.property] + "\n"


if __name__ == "__main__":
    with AriRuntime(Settings.from_environment()) as runtime:
        create_server(
            inspector_factory=lambda _: AdbDeviceInspector(
                SyntheticTransport(), repository=runtime.repository, run_id=runtime.run_id
            )
        ).run(transport="stdio")
