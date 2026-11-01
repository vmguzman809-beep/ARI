import hashlib
import io
import json
import os
import struct
import zipfile
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from ari.core.models import utc_now
from ari.firmware.analyzer import Budget, StaticFirmwareAnalyzer
from ari.firmware.images import inspect_image
from ari.firmware.models import (
    FirmwareError,
    FirmwareErrorCode,
    FirmwareInput,
    FirmwareLimits,
    FirmwareProvenance,
    HashInput,
)
from ari.firmware.reporting import link_firmware_report
from ari.firmware.storage import AuthorizedFirmwareStore
from ari.research.models import ResearchInput, ResearchSource, ResearchTarget


def boot_blob(version=4, *, init=False, signature=False):
    page = 2048 if version <= 2 else 4096
    total = page * (2 if init else 3)
    if version in {1, 2}:
        total += page
    if version == 2:
        total += page
    if signature:
        total += page
    data = bytearray(total)
    data[:8] = b"ANDROID!"
    struct.pack_into("<I", data, 40, version)
    encoded = (14 << 25) | (26 << 4) | 11
    if version <= 2:
        struct.pack_into("<I", data, 8, 1)
        struct.pack_into("<I", data, 16, 1)
        struct.pack_into("<I", data, 36, page)
        struct.pack_into("<I", data, 44, encoded)
        if version >= 1:
            struct.pack_into("<IQI", data, 1632, 1, page * 3, 1648 if version == 1 else 1660)
        if version == 2:
            struct.pack_into("<I", data, 1648, 1)
    else:
        struct.pack_into(
            "<IIII", data, 8, 0 if init else 1, 1, encoded, 1580 if version == 3 else 1584
        )
        if version == 4:
            struct.pack_into("<I", data, 1580, page if signature else 0)
    return bytes(data)


def vendor_blob(version=4):
    data = bytearray(4096 * (3 if version == 3 else 5))
    data[:8] = b"VNDRBOOT"
    struct.pack_into("<II", data, 8, version, 4096)
    struct.pack_into("<I", data, 24, 1)
    struct.pack_into("<II", data, 2096, 2112 if version == 3 else 2128, 1)
    if version == 4:
        struct.pack_into("<IIII", data, 2112, 108, 1, 108, 1)
        struct.pack_into("<III", data, 4096 * 3, 1, 0, 1)
    return bytes(data)


def vbmeta_blob(*, flags=0, rollback=7):
    data = bytearray(256)
    data[:4] = b"AVB0"
    struct.pack_into(">II", data, 4, 1, 0)
    struct.pack_into(">QII", data, 112, rollback, flags, 3)
    return bytes(data)


def with_footer(data):
    metadata = vbmeta_blob()
    return (
        data
        + metadata
        + struct.pack(">4sIIQQQ28s", b"AVBf", 1, 0, len(data), len(data), len(metadata), b"\0" * 28)
    )


@pytest.fixture
def firmware_case(tmp_path, identity):
    expected = identity.model_copy(
        update={
            "variant": json.dumps(["TEST-A", "TEST-ODM"], separators=(",", ":")),
            "android_version": "14",
        }
    )
    properties = {
        "ro.product.manufacturer": expected.manufacturer,
        "ro.product.model": expected.model,
        "ro.boot.hardware.sku": "TEST-A",
        "ro.boot.product.hardware.sku": "TEST-ODM",
        "ro.build.fingerprint": expected.build_fingerprint,
        "ro.build.version.release": "14",
        "ro.build.id": "SYNTHETIC.BUILD",
        "ro.build.ab_update": "true",
    }
    artifact = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("IMAGES/boot_a.img", with_footer(boot_blob()))
        archive.writestr("IMAGES/init_boot_b.img", boot_blob(init=True))
        archive.writestr("IMAGES/vendor_boot.img", vendor_blob())
        archive.writestr("IMAGES/recovery.img", boot_blob(2))
        archive.writestr("IMAGES/vbmeta.img", vbmeta_blob())
        archive.writestr(
            "SYSTEM/build.prop", "\n".join(f"{name}={value}" for name, value in properties.items())
        )
        archive.writestr("META-INF/com/google/android/update-binary", "UNTRUSTED; never execute")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    source = ResearchSource(
        title="Synthetic firmware",
        url="https://example.invalid/firmware",
        verified_at=utc_now(),
        publisher="Synthetic OEM",
        kind="manufacturer",
    )
    checksums = source.model_copy(update={"url": "https://example.invalid/digests"})
    checksums = ResearchSource.model_validate(checksums.model_dump(mode="python", warnings=False))
    request = FirmwareInput(
        artifact=artifact.name,
        authorized=True,
        expected_identity=expected,
        expected_build_id="SYNTHETIC.BUILD",
        expected_sha256=digest,
        provenance=FirmwareProvenance(source=source, hash_source=checksums),
    )
    return artifact, StaticFirmwareAnalyzer(tmp_path), request


@pytest.mark.parametrize("version", [0, 1, 2, 3, 4])
def test_boot_header_versions_and_os_are_observations(version):
    result = inspect_image(boot_blob(version), "boot.img")
    assert result.header_version == version
    assert result.os_version == "14.0.0"
    assert result.security_patch_month == "2026-11"
    assert result.avb.signature_verified is False


@pytest.mark.parametrize("version", [3, 4])
def test_vendor_boot_headers_and_ramdisk_table_are_bounded(version):
    result = inspect_image(vendor_blob(version), "vendor_boot.img")
    assert result.format == "vendor_boot"
    assert result.ramdisk_size == 1


def test_init_boot_and_signature_are_not_executed_or_authenticated():
    result = inspect_image(boot_blob(init=True, signature=True), "init_boot_b.img")
    assert result.partition_hint == "init_boot" and result.slot_hint == "b"
    assert result.kernel_size == 0 and result.boot_signature_size == 4096
    assert result.avb.signature_verified is False


def test_avb_footer_indices_do_not_establish_antirollback_compatibility():
    result = inspect_image(with_footer(boot_blob()), "boot.img")
    assert result.avb.present and result.avb.rollback_index == 7
    assert result.avb.rollback_index_location == 3
    assert result.avb.antirollback_compatible == "unknown"
    assert result.avb.signature_verified is False


def test_package_identity_hash_slots_and_original_preservation(firmware_case):
    artifact, analyzer, request = firmware_case
    before = artifact.read_bytes()
    result = analyzer.analyze_firmware(request)
    assert result.identity_match == "matched"
    assert result.identity == request.expected_identity.model_copy(update={"architecture": None})
    assert result.integrity.matches is True and result.integrity.original_preserved is True
    assert result.ab == "declared_ab" and result.observed_slot_hints == ("a", "b")
    assert result.active_slot == "unknown" and result.status == "blocked"
    assert len(result.images) == 5 and result.uninspected_members == 1
    assert result.blockers
    assert artifact.read_bytes() == before
    assert sorted(path.name for path in artifact.parent.iterdir()) == [artifact.name]


@pytest.mark.parametrize(
    "field", ["manufacturer", "model", "variant", "build_fingerprint", "android_version"]
)
def test_incorrect_variants_and_builds_block_correspondence(firmware_case, field):
    _, analyzer, request = firmware_case
    expected = request.expected_identity.model_copy(update={field: "DIFFERENT-SYNTHETIC"})
    report = analyzer.analyze_firmware(request.model_copy(update={"expected_identity": expected}))
    assert report.identity_match == "mismatch" and report.status == "blocked"


@pytest.mark.parametrize("field", ["variant", "build_fingerprint", "android_version"])
def test_missing_target_identity_is_not_a_match(firmware_case, field):
    _, analyzer, request = firmware_case
    expected = request.expected_identity.model_copy(update={field: None})
    assert (
        analyzer.analyze_firmware(
            request.model_copy(update={"expected_identity": expected})
        ).identity_match
        == "insufficient"
    )


def test_hash_integrity_does_not_authenticate_provenance(firmware_case):
    _, analyzer, request = firmware_case
    result = analyzer.verify_firmware_hash(
        HashInput(artifact=request.artifact, authorized=True, expected_sha256="0" * 64)
    )
    assert result.matches is False and result.authenticity_verified is False
    report = analyzer.analyze_firmware(
        request.model_copy(update={"expected_sha256": None, "provenance": FirmwareProvenance()})
    )
    assert report.status == "blocked" and len(report.blockers) >= 4


def test_no_file_access_without_explicit_per_call_authorization(tmp_path, monkeypatch):
    store = Mock(side_effect=AssertionError("No file access"))
    monkeypatch.setattr(AuthorizedFirmwareStore, "open", store)
    analyzer = StaticFirmwareAnalyzer(tmp_path)
    for request in [
        HashInput(artifact="boot.img"),
        HashInput(artifact="boot.img", authorized=False),
    ]:
        with pytest.raises(FirmwareError) as caught:
            analyzer.verify_firmware_hash(request)
        assert caught.value.code == FirmwareErrorCode.AUTHORIZATION_REQUIRED
    store.assert_not_called()


@pytest.mark.parametrize(
    "path",
    [
        "../private.img",
        "/boot.img",
        "C:/boot.img",
        "\\\\server\\boot.img",
        "boot.img:secret",
        "CON.img",
        "COM1",
        "a//b.img",
        "boot.img.",
        " boot.img ",
        "a/../../b.img",
        "a\\boot.img",
        "$(private).img",
        "boot\x00.img",
        123,
    ],
)
def test_malicious_paths_fail_validation(path):
    with pytest.raises(ValidationError):
        HashInput(artifact=path, authorized=True)


@pytest.mark.parametrize(
    "data", [b"", b"ANDROID!", b"VNDRBOOT", b"AVB0", boot_blob()[:-4096], b"CrAU" + b"\0" * 100]
)
def test_corrupt_and_unsupported_images_are_safe(data):
    with pytest.raises(FirmwareError) as caught:
        inspect_image(data, "boot.img")
    assert caught.value.code in {FirmwareErrorCode.CORRUPT, FirmwareErrorCode.UNSUPPORTED}


@pytest.mark.parametrize(
    "member",
    ["../boot.img", "/boot.img", "a/../../boot.img", "boot.img:secret", "a\\boot.img", "CON.img"],
)
def test_zip_traversal_and_device_names_are_rejected(tmp_path, identity, member):
    artifact = tmp_path / "bad.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        info = zipfile.ZipInfo("synthetic-placeholder")
        info.filename = member
        info.orig_filename = member
        archive.writestr(info, boot_blob())
    with pytest.raises(FirmwareError):
        StaticFirmwareAnalyzer(tmp_path).analyze_firmware(
            FirmwareInput(artifact="bad.zip", authorized=True, expected_identity=identity)
        )
    assert len(list(tmp_path.iterdir())) == 1


def test_zip_links_and_case_collisions_are_rejected(tmp_path, identity):
    artifact = tmp_path / "bad.zip"
    info = zipfile.ZipInfo("boot.img")
    info.create_system = 3
    info.external_attr = 0o120777 << 16
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr(info, b"../private")
    request = FirmwareInput(artifact="bad.zip", authorized=True, expected_identity=identity)
    with pytest.raises(FirmwareError) as caught:
        StaticFirmwareAnalyzer(tmp_path).analyze_firmware(request)
    assert caught.value.code == FirmwareErrorCode.PATH_DENIED
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("boot.img", boot_blob())
        archive.writestr("BOOT.img", boot_blob())
    with pytest.raises(FirmwareError):
        StaticFirmwareAnalyzer(tmp_path).analyze_firmware(request)


def test_limits_cover_input_images_entries_central_directory_and_time(firmware_case, monkeypatch):
    artifact, _, request = firmware_case
    for limit in [
        FirmwareLimits(max_file_bytes=1),
        FirmwareLimits(max_image_bytes=1),
        FirmwareLimits(max_entries=1),
        FirmwareLimits(max_directory_bytes=1),
        FirmwareLimits(max_declared_bytes=1),
    ]:
        with pytest.raises(FirmwareError) as caught:
            StaticFirmwareAnalyzer(artifact.parent, limits=limit).analyze_firmware(request)
        assert caught.value.code == FirmwareErrorCode.RESOURCE_LIMIT
    budget = Budget(FirmwareLimits())
    monkeypatch.setattr("ari.firmware.analyzer.time.monotonic", lambda: budget.deadline + 1)
    with pytest.raises(FirmwareError):
        budget.digest(io.BytesIO(b"synthetic"))


def test_zip_bombs_and_conflicting_properties_are_not_accepted(tmp_path, identity):
    artifact = tmp_path / "bad.zip"
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("boot.img", b"\0" * 1024**2)
    request = FirmwareInput(artifact="bad.zip", authorized=True, expected_identity=identity)
    with pytest.raises(FirmwareError) as caught:
        StaticFirmwareAnalyzer(tmp_path).analyze_firmware(request)
    assert caught.value.code == FirmwareErrorCode.RESOURCE_LIMIT
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("build.prop", "ro.product.model=One\nro.product.model=Other")
    report = StaticFirmwareAnalyzer(tmp_path).analyze_firmware(request)
    assert report.identity.model is None
    assert any("Conflicting metadata" in blocker for blocker in report.blockers)


def test_hardlinks_and_redirected_handles_are_denied(tmp_path, monkeypatch):
    artifact = tmp_path / "boot.img"
    artifact.write_bytes(boot_blob())
    link = tmp_path / "alias.img"
    os.link(artifact, link)
    analyzer = StaticFirmwareAnalyzer(tmp_path)
    with pytest.raises(FirmwareError):
        analyzer.verify_firmware_hash(HashInput(artifact="alias.img", authorized=True))
    link.unlink()
    monkeypatch.setattr(
        "ari.firmware.storage.final_path", lambda _: tmp_path.parent / "private.img"
    )
    with pytest.raises(FirmwareError):
        analyzer.verify_firmware_hash(HashInput(artifact="boot.img", authorized=True))


def test_hash_change_between_passes_is_rejected(firmware_case, monkeypatch):
    _, analyzer, request = firmware_case
    monkeypatch.setattr(Budget, "digest", Mock(side_effect=[("0" * 64, 1), ("1" * 64, 1)]))
    with pytest.raises(FirmwareError) as caught:
        analyzer.verify_firmware_hash(HashInput(artifact=request.artifact, authorized=True))
    assert caught.value.code == FirmwareErrorCode.CHANGED


def test_firmware_links_to_theoretical_research_without_promoting_support(firmware_case):
    _, analyzer, request = firmware_case
    report = analyzer.analyze_firmware(request)
    research = ResearchInput(target=ResearchTarget(identity=request.expected_identity))
    result = link_firmware_report(report, research)
    assert result.plan.executable is False and result.plan.status == "blocked"
    assert result.compatibility.magisk.value == "unknown"
    assert result.firmware.identity_match == "matched"


@pytest.mark.parametrize("offset", [36, 1632])
def test_corrupt_old_boot_sizes_and_offsets(offset):
    data = bytearray(boot_blob(1))
    struct.pack_into("<I", data, offset, 0xFFFFFFFF)
    with pytest.raises(FirmwareError):
        inspect_image(bytes(data), "recovery.img")


@pytest.mark.parametrize("offset", [12, 64, 96])
def test_vbmeta_blocks_and_offsets_cannot_exceed_image(offset):
    data = bytearray(vbmeta_blob())
    struct.pack_into(">Q", data, offset, 0xFFFFFFFFFFFFFFFF)
    with pytest.raises(FirmwareError):
        inspect_image(bytes(data), "vbmeta.img")


def test_avb_footer_cannot_redirect_outside_original():
    data = bytearray(with_footer(boot_blob()))
    struct.pack_into(">Q", data, len(data) - 44, len(data) + 1)
    with pytest.raises(FirmwareError):
        inspect_image(bytes(data), "boot.img")


def test_vendor_ramdisk_table_cannot_reference_outside_ramdisk():
    data = bytearray(vendor_blob())
    struct.pack_into("<I", data, 4096 * 3 + 4, 0xFFFFFFFF)
    with pytest.raises(FirmwareError):
        inspect_image(bytes(data), "vendor_boot.img")


def test_missing_odm_and_conflicting_android_or_ab_metadata_block(firmware_case):
    artifact, analyzer, request = firmware_case
    with zipfile.ZipFile(artifact, "a") as archive:
        archive.writestr("vendor/build.prop", "ro.build.version.release=15\nab_update=false")
    report = analyzer.analyze_firmware(request)
    assert report.identity.android_version is None and report.ab == "unknown"
    assert report.status == "blocked" and report.integrity.matches is False


def test_archive_metadata_and_image_os_disagreement_is_mismatch(tmp_path, identity):
    artifact = tmp_path / "mismatch.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("boot.img", boot_blob())
        archive.writestr("build.prop", "ro.build.version.release=15")
    report = StaticFirmwareAnalyzer(tmp_path).analyze_firmware(
        FirmwareInput(artifact="mismatch.zip", authorized=True, expected_identity=identity)
    )
    assert report.identity_match == "mismatch"
    assert any("OS version conflicts" in blocker for blocker in report.blockers)


def test_raw_image_never_invents_variant_build_or_ab(tmp_path, identity):
    (tmp_path / "boot_a.img").write_bytes(boot_blob())
    report = StaticFirmwareAnalyzer(tmp_path).analyze_firmware(
        FirmwareInput(artifact="boot_a.img", authorized=True, expected_identity=identity)
    )
    assert report.identity.variant is None and report.build_id is None
    assert report.ab == "unknown" and report.observed_slot_hints == ("a",)
    assert report.identity_match == "insufficient"


def test_reparse_attribute_is_rejected_without_following(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from ari.firmware.storage import deny_links

    monkeypatch.setattr(
        type(tmp_path),
        "lstat",
        lambda _: SimpleNamespace(st_mode=0o100644, st_file_attributes=0x400),
    )
    with pytest.raises(FirmwareError) as caught:
        deny_links(tmp_path / "boot.img")
    assert caught.value.code == FirmwareErrorCode.PATH_DENIED


@pytest.mark.skipif(os.name != "nt", reason="Windows file sharing semantics")
def test_windows_handles_block_writes_and_parent_redirection(tmp_path):
    directory = tmp_path / "firmware"
    directory.mkdir()
    artifact = directory / "boot.img"
    data = boot_blob()
    artifact.write_bytes(data)
    with AuthorizedFirmwareStore(directory).open("boot.img") as stream:
        with pytest.raises(PermissionError):
            artifact.write_bytes(b"SYNTHETIC MODIFICATION ATTEMPT")
        with pytest.raises(PermissionError):
            directory.rename(tmp_path / "redirected")
        assert stream.read() == data
    assert artifact.read_bytes() == data


def test_corrupt_deflate_stream_has_typed_error_and_preserves_original(tmp_path, identity):
    artifact = tmp_path / "corrupt.zip"
    data = bytearray(boot_blob())
    data[4096:] = bytes(range(256)) * 32
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("boot.img", data)
    corrupted = bytearray(artifact.read_bytes())
    corrupted[30 + len("boot.img")] = 7
    artifact.write_bytes(corrupted)
    request = FirmwareInput(artifact="corrupt.zip", authorized=True, expected_identity=identity)
    with pytest.raises(FirmwareError) as caught:
        StaticFirmwareAnalyzer(tmp_path).analyze_firmware(request)
    assert caught.value.code == FirmwareErrorCode.CORRUPT
    assert artifact.read_bytes() == corrupted


def test_zip64_local_headers_are_rejected_even_for_small_members(tmp_path, identity):
    artifact = tmp_path / "zip64.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        with archive.open("boot.img", "w", force_zip64=True) as stream:
            stream.write(boot_blob())
    request = FirmwareInput(artifact="zip64.zip", authorized=True, expected_identity=identity)
    with pytest.raises(FirmwareError) as caught:
        StaticFirmwareAnalyzer(tmp_path).analyze_firmware(request)
    assert caught.value.code == FirmwareErrorCode.UNSUPPORTED
