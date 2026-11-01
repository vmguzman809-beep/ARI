"""ADB output is untrusted data, not instructions or a reason to guess identity."""

from pydantic import TypeAdapter, ValidationError

from ari.device.adb import AdbConnection, AdbInventory, AdbSerial, AdbState
from ari.device.errors import AdbError, AdbErrorCode

_SERIAL = TypeAdapter(AdbSerial)


def validate_serial(serial: str) -> str:
    try:
        return _SERIAL.validate_python(serial)
    except ValidationError:
        raise AdbError(AdbErrorCode.INVALID_TARGET) from None


def _check_text(text: str, limit: int) -> None:
    if len(text.encode("utf-8")) > limit or any(
        ord(char) < 32 and char not in "\r\n\t" for char in text
    ):
        raise AdbError(AdbErrorCode.INVALID_RESPONSE)


def parse_devices(text: str) -> AdbInventory:
    _check_text(text, 65_536)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != "List of devices attached" or len(lines) > 257:
        raise AdbError(AdbErrorCode.INVALID_RESPONSE)
    devices = []
    seen = set()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 2:
            raise AdbError(AdbErrorCode.INVALID_RESPONSE)
        try:
            serial = validate_serial(parts[0])
        except AdbError:
            raise AdbError(AdbErrorCode.INVALID_RESPONSE) from None
        if serial in seen:
            raise AdbError(AdbErrorCode.AMBIGUOUS_TARGET)
        seen.add(serial)
        no_permissions = parts[1:3] == ["no", "permissions"]
        reported = "no permissions" if no_permissions else parts[1]
        state = AdbState(reported) if reported in AdbState._value2member_map_ else AdbState.UNKNOWN
        attributes = {}
        for token in parts[3 if no_permissions else 2 :]:
            key, separator, value = token.partition(":")
            if separator and key in {"product", "model", "device", "transport_id"}:
                if key in attributes or not value:
                    raise AdbError(AdbErrorCode.INVALID_RESPONSE)
                attributes[key] = value
        try:
            devices.append(
                AdbConnection(
                    serial=serial,
                    state=state,
                    reported_state=reported,
                    product_hint=attributes.get("product"),
                    model_hint=attributes.get("model"),
                    device_hint=attributes.get("device"),
                    transport_id=attributes.get("transport_id"),
                )
            )
        except ValidationError:
            raise AdbError(AdbErrorCode.INVALID_RESPONSE) from None
    return AdbInventory(devices=tuple(devices))


def parse_property(text: str) -> str | None:
    _check_text(text, 4096)
    lines = text.splitlines()
    if len(lines) > 1 or "\t" in text:
        raise AdbError(AdbErrorCode.INVALID_RESPONSE)
    value = lines[0].strip() if lines else ""
    return None if value.casefold() in {"", "unknown", "null", "<unknown>"} else value


def require_ready(state: str) -> None:
    code = {
        "offline": AdbErrorCode.DEVICE_OFFLINE,
        "unauthorized": AdbErrorCode.DEVICE_UNAUTHORIZED,
        "no permissions": AdbErrorCode.ACCESS_DENIED,
    }.get(state, AdbErrorCode.DEVICE_NOT_READY)
    if state != AdbState.DEVICE:
        raise AdbError(code)
