import json

import pytest

from ari.device.adb import AdbReadOperation, AdbState, DeviceProperty
from ari.device.errors import AdbError, AdbErrorCode
from ari.device.inspector import AdbDeviceInspector


def test_inspection_preserves_properties_identity_dates_and_provenance(
    mock_adb_transport, repository
):
    inspector = AdbDeviceInspector(mock_adb_transport, repository=repository)
    inspection = inspector.inspect_device("SYNTHETIC-1")
    snapshot = inspection.snapshot
    assert snapshot.identity.manufacturer == "Synthetic OEM"
    assert snapshot.identity.model == "Test Phone"
    assert snapshot.identity.model != inspector.detect_devices().devices[0].model_hint
    assert json.loads(snapshot.identity.variant) == ["TEST-A", "TEST-ODM-1"]
    assert snapshot.identity.architecture == "arm64-v8a"
    assert snapshot.identity.android_version == "test-only"
    assert snapshot.identity.build_fingerprint == "synthetic/test/device:1/build/release"
    assert inspection.properties.value(DeviceProperty.BUILD_ID) == "TEST.BUILD.1"
    assert inspection.properties.value(DeviceProperty.SDK_LEVEL) == "999"
    assert all(reading.observed_at.tzinfo is not None for reading in inspection.properties.readings)
    assert snapshot.observed_at.tzinfo is not None
    assert "ADB" in snapshot.provenance
    assert inspection.limitations
    assert repository.get_snapshot(snapshot.id) == snapshot
    assert {event.operation for event in repository.events_for_run(inspector.run_id)} == {
        "detect_devices",
        "inspect_adb_status",
        "get_device_properties",
        "inspect_device",
    }
    assert all(
        "SYNTHETIC-1" not in event.result for event in repository.events_for_run(inspector.run_id)
    )
    event = next(
        event
        for event in repository.events_for_run(inspector.run_id)
        if event.operation == "inspect_device"
    )
    assert event.snapshot_id == snapshot.id


def test_only_one_inventory_request_occurs_during_detection(mock_adb_transport):
    inventory = AdbDeviceInspector(mock_adb_transport).detect_devices()
    assert len(inventory.devices) == 1
    assert mock_adb_transport.execute.call_count == 1
    assert mock_adb_transport.execute.call_args.args[0].operation == AdbReadOperation.DEVICES


@pytest.mark.parametrize(
    "serial", [None, "", "--reboot", "A;reboot", "A&&root", "A\nshell", " A ", "A" * 256]
)
def test_invalid_or_missing_target_never_queries_any_device(mock_adb_transport, serial):
    with pytest.raises(AdbError) as caught:
        AdbDeviceInspector(mock_adb_transport).inspect_device(serial)
    assert caught.value.code == AdbErrorCode.INVALID_TARGET
    mock_adb_transport.execute.assert_not_called()


def test_empty_inventory_missing_target_and_explicit_multi_device_selection(mock_adb_transport):
    inspector = AdbDeviceInspector(mock_adb_transport)
    original = mock_adb_transport.execute.side_effect

    def respond(request):
        if request.operation == AdbReadOperation.DEVICES:
            return "List of devices attached\nSYNTHETIC-1 offline\nSYNTHETIC-2 device\n"
        return original(request)

    mock_adb_transport.execute.side_effect = respond
    result = inspector.inspect_device("SYNTHETIC-2")
    assert result.snapshot.serial == "SYNTHETIC-2"
    assert all(
        call.args[0].serial == "SYNTHETIC-2"
        for call in mock_adb_transport.execute.call_args_list
        if call.args[0].operation != AdbReadOperation.DEVICES
    )
    with pytest.raises(AdbError) as caught:
        inspector.inspect_device("ABSENT")
    assert caught.value.code == AdbErrorCode.DEVICE_NOT_FOUND
    mock_adb_transport.execute.return_value = "List of devices attached\n"
    mock_adb_transport.execute.side_effect = None
    assert inspector.detect_devices().devices == ()
    with pytest.raises(AdbError) as caught:
        inspector.inspect_device("SYNTHETIC-2")
    assert caught.value.code == AdbErrorCode.NO_DEVICES


@pytest.mark.parametrize(
    ("state", "code"),
    [
        ("offline", AdbErrorCode.DEVICE_OFFLINE),
        ("unauthorized", AdbErrorCode.DEVICE_UNAUTHORIZED),
        ("recovery", AdbErrorCode.DEVICE_NOT_READY),
        ("sideload", AdbErrorCode.DEVICE_NOT_READY),
        ("no permissions", AdbErrorCode.ACCESS_DENIED),
        ("unrecognized", AdbErrorCode.DEVICE_NOT_READY),
    ],
)
def test_non_ready_target_has_status_but_no_property_reads(mock_adb_transport, state, code):
    mock_adb_transport.execute.side_effect = None
    mock_adb_transport.execute.return_value = f"List of devices attached\nSYNTHETIC-1 {state}\n"
    inspector = AdbDeviceInspector(mock_adb_transport)
    status = inspector.inspect_adb_status("SYNTHETIC-1")
    assert status.state != AdbState.DEVICE
    with pytest.raises(AdbError) as caught:
        inspector.inspect_device("SYNTHETIC-1")
    assert caught.value.code == code
    assert all(
        call.args[0].operation == AdbReadOperation.DEVICES
        for call in mock_adb_transport.execute.call_args_list
    )


def test_absent_properties_and_variant_are_not_guessed_from_codename(
    mock_adb_transport, adb_values
):
    adb_values[DeviceProperty.HARDWARE_SKU] = "unknown"
    adb_values[DeviceProperty.MANUFACTURER] = ""
    adb_values[DeviceProperty.ABI_LIST] = ""
    result = AdbDeviceInspector(mock_adb_transport).inspect_device("SYNTHETIC-1")
    assert result.snapshot.identity.variant is None
    assert result.snapshot.identity.manufacturer is None
    assert result.snapshot.identity.architecture == "arm64-v8a"
    assert result.properties.value(DeviceProperty.DEVICE) == "test_codename"
    assert DeviceProperty.HARDWARE_SKU in result.properties.missing
    with pytest.raises(ValueError, match="Exact manufacturer"):
        result.snapshot.identity.exact_key()


def test_odm_variants_never_share_exact_identity_keys(mock_adb_transport, adb_values):
    inspector = AdbDeviceInspector(mock_adb_transport)
    first = inspector.inspect_device("SYNTHETIC-1").snapshot.identity
    adb_values[DeviceProperty.ODM_SKU] = "TEST-ODM-2"
    second = inspector.inspect_device("SYNTHETIC-1").snapshot.identity
    assert first.exact_key() != second.exact_key()


@pytest.mark.parametrize("failure", ["timeout", "disconnected", "changed", "offline", "multiline"])
def test_partial_or_changed_inspection_is_not_saved(mock_adb_transport, repository, failure):
    inspector = AdbDeviceInspector(mock_adb_transport, repository=repository)
    original = mock_adb_transport.execute.side_effect
    fingerprints = states = 0

    def respond(request):
        nonlocal fingerprints, states
        if request.operation == AdbReadOperation.STATE:
            states += 1
            if failure == "offline" and states == 2:
                return "offline\n"
        if request.property == DeviceProperty.FINGERPRINT:
            fingerprints += 1
            if failure == "changed" and fingerprints == 2:
                return "different/fingerprint\n"
        if request.property == DeviceProperty.MODEL:
            if failure in {"timeout", "disconnected"}:
                raise AdbError(
                    AdbErrorCode.TIMEOUT if failure == "timeout" else AdbErrorCode.DEVICE_NOT_FOUND
                )
            if failure == "multiline":
                return "one\ntwo\n"
        return original(request)

    mock_adb_transport.execute.side_effect = respond
    with pytest.raises(AdbError) as caught:
        inspector.inspect_device("SYNTHETIC-1")
    assert (
        caught.value.code
        == {
            "timeout": AdbErrorCode.TIMEOUT,
            "disconnected": AdbErrorCode.DEVICE_NOT_FOUND,
            "changed": AdbErrorCode.DEVICE_CHANGED,
            "offline": AdbErrorCode.DEVICE_OFFLINE,
            "multiline": AdbErrorCode.INVALID_RESPONSE,
        }[failure]
    )
    events = repository.events_for_run(inspector.run_id)
    assert events[-1].outcome == "failed"
    assert not any(event.operation == "inspect_device" for event in events)
    with repository.database.engine.connect() as connection:
        from sqlalchemy import text

        assert connection.execute(text("SELECT count(*) FROM device_snapshots")).scalar_one() == 0
