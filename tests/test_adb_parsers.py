import pytest

from ari.device.adb import AdbState
from ari.device.errors import AdbError, AdbErrorCode
from ari.device.parsers import parse_devices, parse_property


def test_inventory_with_zero_devices_is_distinct_from_failure():
    assert parse_devices("List of devices attached\r\n\r\n").devices == ()
    with pytest.raises(AdbError) as caught:
        parse_devices("")
    assert caught.value.code == AdbErrorCode.INVALID_RESPONSE


def test_inventory_retains_states_and_separates_hints():
    inventory = parse_devices(
        "List of devices attached\r\n"
        "SYNTH-1 device usb:1-2 product:demo model:Hint_Model device:code transport_id:1\r\n"
        "SYNTH-2 unauthorized transport_id:2\r\n"
        "emulator-5554 offline\r\n"
        "[::1]:5555 recovery\r\n"
        "SYNTH-3 no permissions (test fixture only)\r\n"
        "SYNTH-4 sideload\r\n"
        "SYNTH-5 bootloader\r\n"
        "SYNTH-6 unrecognized\r\n"
    )
    assert [device.state for device in inventory.devices] == [
        AdbState.DEVICE,
        AdbState.UNAUTHORIZED,
        AdbState.OFFLINE,
        AdbState.RECOVERY,
        AdbState.NO_PERMISSIONS,
        AdbState.SIDELOAD,
        AdbState.BOOTLOADER,
        AdbState.UNKNOWN,
    ]
    assert inventory.devices[0].model_hint == "Hint_Model"
    assert inventory.devices[0].transport_id == 1
    assert inventory.devices[-1].reported_state == "unrecognized"
    assert inventory.observed_at.tzinfo is not None


@pytest.mark.parametrize(
    "text",
    [
        "unexpected header\n",
        "List of devices attached\njust-a-serial\n",
        "List of devices attached\n--reboot device\n",
        "List of devices attached\nSERIAL;root device\n",
        "List of devices attached\nSYNTH device model:A model:B\n",
        "List of devices attached\nSYNTH device transport_id:bad\n",
        "List of devices attached\nSYNTH device transport_id:0\n",
        "List of devices attached\nSYNTH device model:\n",
        "List of devices attached\nSYNTH device\x00\n",
        "List of devices attached\n" + "x" * 65_536,
        "List of devices attached\n" + "\n".join(f"S{i} device" for i in range(257)),
    ],
)
def test_malformed_inventory_does_not_produce_guessed_devices(text):
    with pytest.raises(AdbError) as caught:
        parse_devices(text)
    assert caught.value.code == AdbErrorCode.INVALID_RESPONSE


def test_duplicate_serials_are_ambiguous():
    with pytest.raises(AdbError) as caught:
        parse_devices("List of devices attached\nSYNTH device\nSYNTH device\n")
    assert caught.value.code == AdbErrorCode.AMBIGUOUS_TARGET


@pytest.mark.parametrize("text", ["", "\n", "unknown\r\n", "NULL", "<unknown>", "   "])
def test_absent_or_unknown_property_stays_unknown(text):
    assert parse_property(text) is None


def test_property_is_data_without_execution_or_fingerprint_parsing():
    assert parse_property("Synthetic; $(not-a-command)\r\n") == "Synthetic; $(not-a-command)"
    assert parse_property("test/name/device:release/id\n") == "test/name/device:release/id"


@pytest.mark.parametrize("text", ["a\nb", "a\n\n", "a\tb", "a\x00b", "a\x1bb", "a" * 4097])
def test_multiline_control_or_oversized_properties_are_rejected(text):
    with pytest.raises(AdbError) as caught:
        parse_property(text)
    assert caught.value.code == AdbErrorCode.INVALID_RESPONSE
