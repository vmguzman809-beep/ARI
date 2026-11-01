"""Read-only diagnosis orchestration, independent of the process implementation."""

import json
from uuid import UUID, uuid4

from ari.device.adb import (
    AdbConnection,
    AdbInventory,
    AdbProperties,
    AdbReadOperation,
    AdbReadTransport,
    AdbRequest,
    DeviceInspection,
    DeviceProperty,
    PropertyReading,
)
from ari.device.errors import AdbError, AdbErrorCode
from ari.device.models import DeviceIdentity, DeviceSnapshot
from ari.device.parsers import parse_devices, parse_property, require_ready, validate_serial
from ari.knowledge.models import AuditEvent
from ari.knowledge.repository import KnowledgeRepository


class AdbDeviceInspector:
    def __init__(
        self,
        transport: AdbReadTransport,
        *,
        repository: KnowledgeRepository | None = None,
        run_id: UUID | None = None,
    ) -> None:
        self._transport = transport
        self._repository = repository
        self.run_id = run_id or uuid4()

    def _event(
        self, operation: str, error: AdbError | None = None, *, snapshot_id: UUID | None = None
    ) -> None:
        if self._repository is not None:
            self._repository.record_event(
                AuditEvent(
                    run_id=self.run_id,
                    operation=operation,
                    outcome="failed" if error else "succeeded",
                    result=error.code.value if error else "Read-only ADB observation captured",
                    snapshot_id=snapshot_id,
                )
            )

    def detect_devices(self) -> AdbInventory:
        try:
            result = parse_devices(
                self._transport.execute(AdbRequest(operation=AdbReadOperation.DEVICES))
            )
        except AdbError as error:
            self._event("detect_devices", error)
            raise
        self._event("detect_devices")
        return result

    def inspect_adb_status(self, serial: str) -> AdbConnection:
        """Return a fresh inventory observation, including offline/unauthorized states."""
        try:
            serial = validate_serial(serial)
            inventory = self.detect_devices()
            if not inventory.devices:
                raise AdbError(AdbErrorCode.NO_DEVICES)
            connection = next(
                (device for device in inventory.devices if device.serial == serial), None
            )
            if connection is None:
                raise AdbError(AdbErrorCode.DEVICE_NOT_FOUND)
        except AdbError as error:
            self._event("inspect_adb_status", error)
            raise
        self._event("inspect_adb_status")
        return connection

    def _require_ready(self, serial: str) -> None:
        state = self._transport.execute(AdbRequest(operation=AdbReadOperation.STATE, serial=serial))
        # Unknown or malformed states are never treated as a ready Android system.
        require_ready(state.strip())

    def get_device_properties(self, serial: str) -> AdbProperties:
        try:
            serial = validate_serial(serial)
            connection = self.inspect_adb_status(serial)
            require_ready(connection.state)
            self._require_ready(serial)
            readings = tuple(
                PropertyReading(
                    name=name,
                    value=parse_property(
                        self._transport.execute(
                            AdbRequest(
                                operation=AdbReadOperation.PROPERTY, serial=serial, property=name
                            )
                        )
                    ),
                )
                for name in DeviceProperty
            )
            result = AdbProperties(serial=serial, readings=readings)
            final_fingerprint = parse_property(
                self._transport.execute(
                    AdbRequest(
                        operation=AdbReadOperation.PROPERTY,
                        serial=serial,
                        property=DeviceProperty.FINGERPRINT,
                    )
                )
            )
            if final_fingerprint != result.value(DeviceProperty.FINGERPRINT):
                raise AdbError(AdbErrorCode.DEVICE_CHANGED)
            self._require_ready(serial)
        except AdbError as error:
            self._event("get_device_properties", error)
            raise
        self._event("get_device_properties")
        return result

    def inspect_device(self, serial: str) -> DeviceInspection:
        properties = self.get_device_properties(serial)
        value = properties.value
        sku, odm_sku = value(DeviceProperty.HARDWARE_SKU), value(DeviceProperty.ODM_SKU)
        variant = (
            json.dumps([sku, odm_sku], ensure_ascii=False, separators=(",", ":"))
            if sku is not None and odm_sku is not None
            else None
        )
        if variant is not None and len(variant) > 4096:
            variant = None
        abi_list = value(DeviceProperty.ABI_LIST)
        architecture = abi_list.split(",")[0].strip() if abi_list else value(DeviceProperty.CPU_ABI)
        identity = DeviceIdentity(
            manufacturer=value(DeviceProperty.MANUFACTURER),
            model=value(DeviceProperty.MODEL),
            variant=variant,
            build_fingerprint=value(DeviceProperty.FINGERPRINT),
            android_version=value(DeviceProperty.ANDROID_RELEASE),
            architecture=architecture or None,
        )
        snapshot = DeviceSnapshot(
            identity=identity,
            serial=properties.serial,
            provenance="ADB devices -l/get-state/allowlisted getprop; device-reported values",
        )
        limitations = [
            "Device-reported values are not attestation or proof of firmware/root compatibility",
            "Property reads are sequential; equal fingerprints do not prove an atomic snapshot",
        ]
        if properties.missing:
            limitations.append("Some whitelisted properties were absent or unknown")
        if variant is None:
            limitations.append(
                "Exact variant unavailable; both hardware SKU and ODM SKU are required"
            )
        result = DeviceInspection(
            snapshot=snapshot, properties=properties, limitations=tuple(limitations)
        )
        if self._repository is not None:
            self._repository.record_snapshot(snapshot)
        self._event("inspect_device", snapshot_id=snapshot.id)
        return result
