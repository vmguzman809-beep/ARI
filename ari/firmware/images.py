import hashlib
import struct
from pathlib import PurePosixPath

from ari.firmware.models import (
    AvbObservation,
    FirmwareError,
    FirmwareErrorCode,
    ImageObservation,
)


def require(condition: bool) -> None:
    if not condition:
        raise FirmwareError(FirmwareErrorCode.CORRUPT)


def aligned(size: int, page: int) -> int:
    return (size + page - 1) // page * page


def page_size_valid(page: int, header: int) -> None:
    require(2048 <= page <= 65536 and page & (page - 1) == 0 and page >= header)


def parse_vbmeta(data: bytes) -> AvbObservation:
    require(len(data) >= 256 and data[:4] == b"AVB0")
    major, minor = struct.unpack_from(">II", data, 4)
    if major != 1 or minor > 3:
        raise FirmwareError(FirmwareErrorCode.UNSUPPORTED)
    auth_size, aux_size, algorithm = struct.unpack_from(">QQI", data, 12)
    total = 256 + auth_size + aux_size
    require(total <= len(data) and auth_size % 64 == 0 and aux_size % 64 == 0)
    require(not any(data[176:256]))
    for position, block_size in (
        (32, auth_size),
        (48, auth_size),
        (64, aux_size),
        (80, aux_size),
        (96, aux_size),
    ):
        offset, length = struct.unpack_from(">QQ", data, position)
        require(offset + length <= block_size)
    descriptors_offset, descriptors_size = struct.unpack_from(">QQ", data, 96)
    cursor = 256 + auth_size + descriptors_offset
    end = cursor + descriptors_size
    descriptor_count = 0
    while cursor < end:
        require(end - cursor >= 16)
        _, length = struct.unpack_from(">QQ", data, cursor)
        require(length % 8 == 0 and cursor + 16 + length <= end)
        cursor += 16 + length
        descriptor_count += 1
        require(descriptor_count <= 256)
    key_offset, key_size = struct.unpack_from(">QQ", data, 64)
    key_start = 256 + auth_size + key_offset
    rollback, flags, location = struct.unpack_from(">QII", data, 112)
    require(flags & ~3 == 0)
    return AvbObservation(
        present=True,
        algorithm=algorithm,
        rollback_index=rollback,
        rollback_index_location=location,
        flags=flags,
        descriptor_count=descriptor_count,
        public_key_sha256=hashlib.sha256(data[key_start : key_start + key_size]).hexdigest()
        if key_size
        else None,
    )


def parse_avb(data: bytes) -> tuple[AvbObservation, int]:
    if data.startswith(b"AVB0"):
        return parse_vbmeta(data), len(data)
    if len(data) < 64 or data[-64:-60] != b"AVBf":
        return AvbObservation(), len(data)
    _, major, minor, original, offset, size, reserved = struct.unpack(">4sIIQQQ28s", data[-64:])
    require(major == 1 and minor == 0 and not any(reserved))
    require(original <= offset and size >= 256 and offset + size <= len(data) - 64)
    return parse_vbmeta(data[offset : offset + size]), original


def partition_hints(member: str) -> tuple[str, str | None]:
    name = PurePosixPath(member).stem
    slot = name[-1] if name.endswith(("_a", "_b")) else None
    partition = name[:-2] if slot else name
    if partition not in {"boot", "init_boot", "vendor_boot", "recovery", "vbmeta"}:
        partition = "unknown"
    return partition, slot


def decode_os(encoded: int) -> tuple[str | None, str | None]:
    if encoded == 0:
        return None, None
    major, minor, patch = (encoded >> 25) & 127, (encoded >> 18) & 127, (encoded >> 11) & 127
    month = encoded & 15
    year = 2000 + ((encoded >> 4) & 127)
    require(month <= 12)
    version = f"{major}.{minor}.{patch}" if encoded >> 11 else None
    return version, f"{year:04d}-{month:02d}" if month else None


def inspect_image(data: bytes, member: str) -> ImageObservation:
    require(len(data) >= 8)
    avb, payload_size = parse_avb(data)
    partition, slot = partition_hints(member)
    common = dict(
        member=member,
        partition_hint=partition,
        slot_hint=slot,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        avb=avb,
    )
    if data.startswith(b"AVB0"):
        return ImageObservation(format="vbmeta", **common)
    if data.startswith(b"ANDROID!"):
        require(payload_size >= 48)
        version = struct.unpack_from("<I", data, 40)[0]
        if version > 4:
            raise FirmwareError(FirmwareErrorCode.UNSUPPORTED)
        if version <= 2:
            header = (1632, 1648, 1660)[version]
            require(payload_size >= header)
            kernel = struct.unpack_from("<I", data, 8)[0]
            ramdisk = struct.unpack_from("<I", data, 16)[0]
            second = struct.unpack_from("<I", data, 24)[0]
            page = struct.unpack_from("<I", data, 36)[0]
            encoded_os = struct.unpack_from("<I", data, 44)[0]
            page_size_valid(page, header)
            end = page + aligned(kernel, page) + aligned(ramdisk, page) + aligned(second, page)
            if version >= 1:
                recovery_size, recovery_offset, header_size = struct.unpack_from("<IQI", data, 1632)
                require(header_size == header)
                if recovery_size:
                    require(recovery_offset == end)
                end += aligned(recovery_size, page)
            if version == 2:
                end += aligned(struct.unpack_from("<I", data, 1648)[0], page)
            signature = None
        else:
            header = 1580 if version == 3 else 1584
            require(payload_size >= header)
            kernel, ramdisk, encoded_os, header_size = struct.unpack_from("<IIII", data, 8)
            require(header_size == header and not any(data[24:40]))
            page = 4096
            signature = struct.unpack_from("<I", data, 1580)[0] if version == 4 else None
            end = page + aligned(kernel, page) + aligned(ramdisk, page)
            if signature:
                end += aligned(signature, page)
        require(kernel + ramdisk > 0 and end <= payload_size)
        os_version, security_patch = decode_os(encoded_os)
        return ImageObservation(
            format="android_boot",
            header_version=version,
            page_size=page,
            kernel_size=kernel,
            ramdisk_size=ramdisk,
            os_version=os_version,
            security_patch_month=security_patch,
            boot_signature_size=signature,
            **common,
        )
    if data.startswith(b"VNDRBOOT"):
        require(payload_size >= 12)
        version = struct.unpack_from("<I", data, 8)[0]
        if version not in {3, 4}:
            raise FirmwareError(FirmwareErrorCode.UNSUPPORTED)
        header = 2112 if version == 3 else 2128
        require(payload_size >= header)
        page = struct.unpack_from("<I", data, 12)[0]
        ramdisk = struct.unpack_from("<I", data, 24)[0]
        header_size, dtb = struct.unpack_from("<II", data, 2096)
        require(header_size == header)
        page_size_valid(page, header)
        end = aligned(header, page) + aligned(ramdisk, page) + aligned(dtb, page)
        if version == 4:
            table_size, count, entry_size, bootconfig = struct.unpack_from("<IIII", data, 2112)
            require(count <= 128 and table_size == count * entry_size)
            require(count == 0 or entry_size >= 108)
            table_start = end
            end += aligned(table_size, page) + aligned(bootconfig, page)
            require(end <= payload_size)
            for index in range(count):
                size, offset, kind = struct.unpack_from(
                    "<III", data, table_start + index * entry_size
                )
                require(offset + size <= ramdisk and kind <= 3)
        require(end <= payload_size)
        return ImageObservation(
            format="vendor_boot",
            header_version=version,
            page_size=page,
            ramdisk_size=ramdisk,
            **common,
        )
    raise FirmwareError(FirmwareErrorCode.UNSUPPORTED)
