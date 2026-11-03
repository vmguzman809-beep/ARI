"""Bounded JSON bytes parser. The caller owns local file acquisition and storage.

No paths, URL fetching, file opening, device transports or command interfaces.
Public functions sanitize validation failures; raw Pydantic errors are private.
MAX_SECONDS is checked after successful processing, not a guaranteed interruption.
"""

import json
import time

from pydantic import ValidationError

from ari.maintenance.errors import MaintenanceError
from ari.maintenance.models import Baseline, MaintenanceModel, PackageSnapshot

MAX_BYTES = 5 * 1024 * 1024
MAX_DEPTH = 16
# Post-processing elapsed-time rejection only: no timer, cancellation or hard deadline.
MAX_SECONDS = 5.0


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MaintenanceError("invalid_artifact")
        result[key] = value
    return result


def _reject_constant(_value):
    raise MaintenanceError("invalid_artifact")


def _depth_check(text: str) -> None:
    depth = 0
    quoted = escaped = False
    for index, char in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise MaintenanceError("limit_exceeded")
        elif char in "]}":
            depth -= 1
        if index % 4096 == 0 and depth < 0:
            raise MaintenanceError("invalid_artifact")


def _parse[T: MaintenanceModel](data: bytes, model: type[T]) -> T:
    start = time.monotonic()
    if type(data) is not bytes:
        raise MaintenanceError("invalid_artifact")
    if len(data) > MAX_BYTES:
        raise MaintenanceError("limit_exceeded")
    try:
        text = data.decode("utf-8", errors="strict")
        _depth_check(text)
        decoded = json.loads(
            text, object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
        if not isinstance(decoded, dict):
            raise MaintenanceError("invalid_artifact")
        result = model.model_validate_json(data, strict=True)
    except MaintenanceError:
        raise
    except (UnicodeError, ValueError, RecursionError):
        # Re-raise only a static code; do not expose inputs/paths/validation locations.
        raise MaintenanceError("invalid_artifact") from None
    if time.monotonic() - start > MAX_SECONDS:
        raise MaintenanceError("limit_exceeded")
    return result


def parse_snapshot(data: bytes) -> PackageSnapshot:
    return _parse(data, PackageSnapshot)


def parse_baseline(data: bytes) -> Baseline:
    return _parse(data, Baseline)


def validated[T: MaintenanceModel](value: T, model: type[T]) -> T:
    """Revalidate even model_construct/model_copy input at service boundaries."""
    try:
        if type(value) is not model:
            raise MaintenanceError("invalid_model")
        return model.model_validate(value, strict=True)
    except (ValidationError, ValueError, TypeError, AttributeError):
        raise MaintenanceError("invalid_model") from None
