import hashlib
import json
import os
import stat
import struct
import time
import zipfile
import zlib
from datetime import timedelta
from pathlib import Path

from ari.core.models import utc_now
from ari.device.models import DeviceIdentity
from ari.firmware.images import inspect_image, partition_hints, require
from ari.firmware.models import (
    FirmwareError,
    FirmwareErrorCode,
    FirmwareInput,
    FirmwareLimits,
    FirmwareReport,
    HashInput,
    HashResult,
    PropertyObservation,
    validate_relative_path,
)
from ari.firmware.storage import AuthorizedFirmwareStore

PROPERTIES = {
    "ro.product.manufacturer",
    "ro.product.model",
    "ro.boot.hardware.sku",
    "ro.boot.product.hardware.sku",
    "ro.build.fingerprint",
    "ro.build.version.release",
    "ro.build.id",
    "ro.product.cpu.abilist",
    "ro.product.cpu.abi",
    "ro.build.ab_update",
    "ab_update",
    "ota-type",
    "post-build",
    "ro.build.version.security_patch",
}
METADATA_PATHS = {
    "build.prop",
    "system/build.prop",
    "system/system/build.prop",
    "vendor/build.prop",
    "product/build.prop",
    "meta-inf/com/android/metadata",
    "meta/misc_info.txt",
}
LIMITATIONS = (
    "Static untrusted metadata; properties and header values are not device attestation",
    "No OEM/package signature or AVB signature/trust-chain verification is implemented",
    "Rollback indices are reported, never compared to device fuses or trusted stored counters",
    "Partition and slot suffixes are filename hints, not a measured layout or active slot",
    "No ramdisk execution/unpacking, payload.bin, sparse/ext4, encrypted, TAR or nested extraction",
    "Only allowlisted metadata/images are decompressed; other members are not content-validated",
    "No images are modified and no device or external process is accessed",
)


class Budget:
    def __init__(self, limits: FirmwareLimits):
        self.limits = limits
        self.deadline = time.monotonic() + limits.timeout_seconds

    def check(self) -> None:
        if time.monotonic() > self.deadline:
            raise FirmwareError(FirmwareErrorCode.RESOURCE_LIMIT)

    def digest(self, stream) -> tuple[str, int]:
        stream.seek(0)
        digest = hashlib.sha256()
        size = 0
        while chunk := stream.read(1024**2):
            self.check()
            size += len(chunk)
            if size > self.limits.max_file_bytes:
                raise FirmwareError(FirmwareErrorCode.RESOURCE_LIMIT)
            digest.update(chunk)
        self.check()
        return digest.hexdigest(), size


def parse_properties(data: bytes, member: str) -> list[PropertyObservation]:
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        raise FirmwareError(FirmwareErrorCode.CORRUPT) from None
    require("\x00" not in text)
    lines = text.splitlines()
    if len(lines) > 2048:
        raise FirmwareError(FirmwareErrorCode.RESOURCE_LIMIT)
    observations = []
    for line in lines:
        if line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = (part.strip() for part in line.split("=", 1))
        if name not in PROPERTIES or value.lower() in {"", "unknown", "null", "none"}:
            continue
        if len(value) > 4096:
            raise FirmwareError(FirmwareErrorCode.RESOURCE_LIMIT)
        require(not any(ord(character) < 32 for character in value))
        observations.append(PropertyObservation(member=member, name=name, value=value))
    return observations


def inspect_zip(stream, budget: Budget):
    size = os.fstat(stream.fileno()).st_size
    stream.seek(max(0, size - 65557))
    tail = stream.read(65557)
    position = tail.rfind(b"PK\x05\x06")
    require(position >= 0 and len(tail) - position >= 22)
    _, disk, directory_disk, disk_count, count, directory_size, directory_offset, comment = (
        struct.unpack_from("<4s4H2IH", tail, position)
    )
    require(disk == directory_disk == 0 and disk_count == count)
    require(position + 22 + comment == len(tail))
    if count == 65535 or directory_offset == 0xFFFFFFFF or directory_size == 0xFFFFFFFF:
        raise FirmwareError(FirmwareErrorCode.UNSUPPORTED)
    if count > budget.limits.max_entries or directory_size > budget.limits.max_directory_bytes:
        raise FirmwareError(FirmwareErrorCode.RESOURCE_LIMIT)
    require(directory_offset + directory_size == size - len(tail) + position)
    observations, images, skipped = [], [], 0
    with zipfile.ZipFile(stream) as archive:
        members = archive.infolist()
        require(len(members) == count)
        names, declared = set(), 0
        for member in members:
            budget.check()
            name = member.filename[:-1] if member.is_dir() else member.filename
            try:
                validate_relative_path(name)
            except ValueError:
                raise FirmwareError(FirmwareErrorCode.PATH_DENIED) from None
            require(member.orig_filename == member.filename)
            if name.casefold() in names:
                raise FirmwareError(FirmwareErrorCode.CORRUPT)
            names.add(name.casefold())
            mode = member.external_attr >> 16
            if stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}:
                raise FirmwareError(FirmwareErrorCode.PATH_DENIED)
            if (
                member.flag_bits & 1
                or member.compress_type not in {0, 8}
                or member.extract_version >= 45
            ):
                raise FirmwareError(FirmwareErrorCode.UNSUPPORTED)
            declared += member.file_size
            if declared > budget.limits.max_declared_bytes or member.file_size > (
                max(1, member.compress_size) * budget.limits.max_ratio
            ):
                raise FirmwareError(FirmwareErrorCode.RESOURCE_LIMIT)
            if member.is_dir():
                continue
            partition, _ = partition_hints(name)
            metadata = name.lower() in METADATA_PATHS
            image = name.lower().endswith(".img") and partition != "unknown"
            if not metadata and not image:
                skipped += 1
                continue
            limit = budget.limits.max_metadata_bytes if metadata else budget.limits.max_image_bytes
            if member.file_size > limit:
                raise FirmwareError(FirmwareErrorCode.RESOURCE_LIMIT)
            with archive.open(member) as content:
                data = content.read(limit + 1)
                require(len(data) == member.file_size)
            budget.check()
            if metadata:
                observations.extend(parse_properties(data, name))
                if len(observations) > 512:
                    raise FirmwareError(FirmwareErrorCode.RESOURCE_LIMIT)
            else:
                images.append(inspect_image(data, name))
    return observations, images, skipped


def resolve_identity(observations):
    values = {}
    for observation in observations:
        name = "ro.build.fingerprint" if observation.name == "post-build" else observation.name
        values.setdefault(name, set()).add(observation.value)
    conflicts = [
        f"Conflicting metadata for {name}" for name, items in values.items() if len(items) > 1
    ]

    def value(name):
        items = values.get(name, set())
        return next(iter(items)) if len(items) == 1 else None

    sku, odm = value("ro.boot.hardware.sku"), value("ro.boot.product.hardware.sku")
    variant = (
        json.dumps([sku, odm], ensure_ascii=False, separators=(",", ":")) if sku and odm else None
    )
    if variant and len(variant) > 4096:
        variant = None
    abi = value("ro.product.cpu.abilist") or value("ro.product.cpu.abi")
    identity = DeviceIdentity(
        manufacturer=value("ro.product.manufacturer"),
        model=value("ro.product.model"),
        variant=variant,
        build_fingerprint=value("ro.build.fingerprint"),
        android_version=value("ro.build.version.release"),
        architecture=abi.split(",")[0].strip() or None if abi else None,
    )
    ab_values = {
        item.value for item in observations if item.name in {"ab_update", "ro.build.ab_update"}
    }
    ab_values |= {
        "true" if item.value == "AB" else "false"
        for item in observations
        if item.name == "ota-type" and item.value in {"AB", "BLOCK"}
    }
    ab = "unknown"
    if ab_values == {"true"}:
        ab = "declared_ab"
    elif ab_values == {"false"}:
        ab = "declared_non_ab"
    elif ab_values:
        conflicts.append("Conflicting or unknown A/B declarations")
    return identity, value("ro.build.id"), ab, conflicts


class StaticFirmwareAnalyzer:
    def __init__(self, root: Path, *, limits: FirmwareLimits | None = None):
        self.store = AuthorizedFirmwareStore(root)
        self.limits = limits or FirmwareLimits()

    def verify_firmware_hash(self, request: HashInput) -> HashResult:
        request = HashInput.model_validate(request.model_dump(mode="python", warnings=False))
        if not request.authorized:
            raise FirmwareError(FirmwareErrorCode.AUTHORIZATION_REQUIRED)
        budget = Budget(self.limits)
        with self.store.open(request.artifact) as stream:
            if os.fstat(stream.fileno()).st_size > self.limits.max_file_bytes:
                raise FirmwareError(FirmwareErrorCode.RESOURCE_LIMIT)
            digest, size = budget.digest(stream)
            if budget.digest(stream) != (digest, size):
                raise FirmwareError(FirmwareErrorCode.CHANGED)
        return HashResult(
            artifact=request.artifact,
            sha256=digest,
            size_bytes=size,
            expected_sha256=request.expected_sha256,
            matches=digest == request.expected_sha256 if request.expected_sha256 else None,
        )

    def analyze_firmware(self, request: FirmwareInput) -> FirmwareReport:
        request = FirmwareInput.model_validate(request.model_dump(mode="python", warnings=False))
        if not request.authorized:
            raise FirmwareError(FirmwareErrorCode.AUTHORIZATION_REQUIRED)
        budget = Budget(self.limits)
        try:
            with self.store.open(request.artifact) as stream:
                size = os.fstat(stream.fileno()).st_size
                if size > self.limits.max_file_bytes:
                    raise FirmwareError(FirmwareErrorCode.RESOURCE_LIMIT)
                digest, _ = budget.digest(stream)
                stream.seek(0)
                suffix = Path(request.artifact).suffix.lower()
                if suffix == ".zip":
                    observations, images, skipped = inspect_zip(stream, budget)
                    container = "zip"
                elif suffix == ".img":
                    if size > self.limits.max_image_bytes:
                        raise FirmwareError(FirmwareErrorCode.RESOURCE_LIMIT)
                    data = stream.read(self.limits.max_image_bytes + 1)
                    observations, images, skipped = [], [inspect_image(data, request.artifact)], 0
                    container = "image"
                else:
                    raise FirmwareError(FirmwareErrorCode.UNSUPPORTED)
                if budget.digest(stream) != (digest, size):
                    raise FirmwareError(FirmwareErrorCode.CHANGED)
        except (zipfile.BadZipFile, zlib.error, EOFError, UnicodeError, struct.error, RuntimeError):
            raise FirmwareError(FirmwareErrorCode.CORRUPT) from None
        identity, build, ab, blockers = resolve_identity(observations)
        fields = ("manufacturer", "model", "variant", "build_fingerprint", "android_version")
        mismatch = any(
            getattr(identity, field) is not None
            and getattr(request.expected_identity, field) is not None
            and getattr(identity, field) != getattr(request.expected_identity, field)
            for field in fields
        )
        incomplete = any(
            getattr(identity, field) is None or getattr(request.expected_identity, field) is None
            for field in fields
        )
        if identity.architecture and request.expected_identity.architecture:
            mismatch |= identity.architecture != request.expected_identity.architecture
        if identity.android_version:

            def normalized_version(value):
                parts = value.split(".")
                if not all(part.isdigit() for part in parts):
                    return None
                numbers = [int(part) for part in parts]
                while len(numbers) > 1 and numbers[-1] == 0:
                    numbers.pop()
                return tuple(numbers)

            for image in images:
                if image.os_version and normalized_version(identity.android_version) is not None:
                    if normalized_version(image.os_version) != normalized_version(
                        identity.android_version
                    ):
                        blockers.append("Image OS version conflicts with package metadata")
                        mismatch = True
        if request.expected_build_id is None or build is None:
            incomplete = True
            blockers.append("Build ID correspondence is unverified")
        elif request.expected_build_id != build:
            mismatch = True
        match = "mismatch" if mismatch else "insufficient" if incomplete else "matched"
        if match != "matched":
            blockers.append(
                "Exact firmware identity/build/Android correspondence is not established"
            )
        expected = request.expected_sha256
        if expected is None or expected != digest:
            blockers.append("Independent expected SHA-256 is absent or does not match")
        source, hash_source = request.provenance.source, request.provenance.hash_source
        if source is None or hash_source is None or source.url == hash_source.url:
            blockers.append("Separate dated firmware provenance and digest sources are required")
        if source and source.kind != "manufacturer":
            blockers.append("Manufacturer firmware provenance is unverified")
        if any(
            item and utc_now() - item.verified_at > timedelta(days=180)
            for item in (source, hash_source)
        ):
            blockers.append("Firmware provenance evidence needs current verification")
        if not images:
            blockers.append("No supported boot or vbmeta image was inspected")
        if any(image.avb.flags for image in images):
            blockers.append("AVB verification-disable flags are present")
        blockers.extend(
            (
                "OEM authenticity and package/AVB signatures remain unverified",
                "Device antirollback counters and chain-specific index locations are unknown",
            )
        )
        integrity = HashResult(
            artifact=request.artifact,
            size_bytes=size,
            sha256=digest,
            expected_sha256=expected,
            matches=digest == expected if expected else None,
        )
        return FirmwareReport(
            integrity=integrity,
            container=container,
            identity=identity,
            expected_identity=request.expected_identity,
            expected_build_id=request.expected_build_id,
            identity_match=match,
            build_id=build,
            ab=ab,
            observed_slot_hints=tuple(
                sorted({image.slot_hint for image in images if image.slot_hint})
            ),
            observations=tuple(observations),
            images=tuple(images),
            uninspected_members=skipped,
            provenance=request.provenance,
            blockers=tuple(blockers),
            limitations=LIMITATIONS,
        )
