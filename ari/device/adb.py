"""Typed ADB read operations shared by the domain and the external adapter."""

from enum import StrEnum
from typing import Annotated, Protocol

from pydantic import AwareDatetime, Field, StringConstraints, model_validator

from ari.core.models import DomainModel, NonEmpty, utc_now
from ari.device.models import DeviceSnapshot

AdbSerial = Annotated[
    str,
    StringConstraints(
        strip_whitespace=False,
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9\[][A-Za-z0-9._:\[\]-]*$",
    ),
]


class AdbState(StrEnum):
    DEVICE = "device"
    OFFLINE = "offline"
    UNAUTHORIZED = "unauthorized"
    NO_PERMISSIONS = "no permissions"
    RECOVERY = "recovery"
    SIDELOAD = "sideload"
    BOOTLOADER = "bootloader"
    UNKNOWN = "unknown"


class DeviceProperty(StrEnum):
    MANUFACTURER = "ro.product.manufacturer"
    MODEL = "ro.product.model"
    DEVICE = "ro.product.device"
    PRODUCT_NAME = "ro.product.name"
    HARDWARE_SKU = "ro.boot.hardware.sku"
    ODM_SKU = "ro.boot.product.hardware.sku"
    BUILD_ID = "ro.build.id"
    FINGERPRINT = "ro.build.fingerprint"
    ANDROID_RELEASE = "ro.build.version.release"
    SDK_LEVEL = "ro.build.version.sdk"
    ABI_LIST = "ro.product.cpu.abilist"
    CPU_ABI = "ro.product.cpu.abi"


class AdbReadOperation(StrEnum):
    DEVICES = "devices"
    STATE = "state"
    PROPERTY = "property"


class AdbRequest(DomainModel):
    operation: AdbReadOperation
    serial: AdbSerial | None = None
    property: DeviceProperty | None = None

    @model_validator(mode="after")
    def require_bounded_target(self) -> "AdbRequest":
        if self.operation == AdbReadOperation.DEVICES:
            if self.serial is not None or self.property is not None:
                raise ValueError("Inventory cannot accept a target or property")
        elif self.serial is None:
            raise ValueError("An explicit serial is required")
        if (self.operation == AdbReadOperation.PROPERTY) != (self.property is not None):
            raise ValueError("Only property reads require a whitelisted property")
        return self


class AdbReadTransport(Protocol):
    def execute(self, request: AdbRequest) -> str: ...


class AdbConnection(DomainModel):
    serial: AdbSerial
    state: AdbState
    reported_state: NonEmpty
    observed_at: AwareDatetime = Field(default_factory=utc_now)
    product_hint: NonEmpty | None = None
    model_hint: NonEmpty | None = None
    device_hint: NonEmpty | None = None
    transport_id: int | None = Field(default=None, gt=0)


class AdbInventory(DomainModel):
    observed_at: AwareDatetime = Field(default_factory=utc_now)
    devices: tuple[AdbConnection, ...] = ()


class PropertyReading(DomainModel):
    name: DeviceProperty
    value: NonEmpty | None
    observed_at: AwareDatetime = Field(default_factory=utc_now)


class AdbProperties(DomainModel):
    serial: AdbSerial
    readings: tuple[PropertyReading, ...]

    @model_validator(mode="after")
    def require_complete_allowlist(self) -> "AdbProperties":
        names = [reading.name for reading in self.readings]
        if len(names) != len(DeviceProperty) or set(names) != set(DeviceProperty):
            raise ValueError("Each whitelisted property must have exactly one reading")
        return self

    def value(self, name: DeviceProperty) -> str | None:
        return next(reading.value for reading in self.readings if reading.name == name)

    @property
    def missing(self) -> tuple[DeviceProperty, ...]:
        return tuple(reading.name for reading in self.readings if reading.value is None)


class DeviceInspection(DomainModel):
    snapshot: DeviceSnapshot
    properties: AdbProperties
    limitations: tuple[NonEmpty, ...]
