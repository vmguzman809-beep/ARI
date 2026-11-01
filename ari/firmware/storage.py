import ctypes
import os
import stat
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path

from ari.firmware.models import FirmwareError, FirmwareErrorCode, validate_relative_path


def deny_links(path: Path) -> None:
    attributes = path.lstat()
    if stat.S_ISLNK(attributes.st_mode) or getattr(attributes, "st_file_attributes", 0) & 0x400:
        raise FirmwareError(FirmwareErrorCode.PATH_DENIED)


def open_readonly(path: Path, *, directory: bool = False) -> int:
    if os.name != "nt":
        return os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    import msvcrt
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create.restype = wintypes.HANDLE
    access = 0x80 if directory else 0x80000000
    flags = 0x00200000 | (0x02000000 if directory else 0)
    handle = create(str(path), access, 1, None, 3, flags, None)
    if handle == wintypes.HANDLE(-1).value:
        raise FirmwareError(FirmwareErrorCode.PATH_DENIED)
    try:
        return msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except Exception:
        close = kernel.CloseHandle
        close.argtypes = (wintypes.HANDLE,)
        close(handle)
        raise


def final_path(descriptor: int) -> Path:
    if os.name == "nt":
        import msvcrt
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        resolve = kernel.GetFinalPathNameByHandleW
        resolve.argtypes = (wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD)
        resolve.restype = wintypes.DWORD
        buffer = ctypes.create_unicode_buffer(32768)
        length = resolve(msvcrt.get_osfhandle(descriptor), buffer, len(buffer), 0)
        if not 0 < length < len(buffer) or not buffer.value.startswith("\\\\?\\"):
            raise FirmwareError(FirmwareErrorCode.PATH_DENIED)
        return Path(buffer.value[4:])
    if sys.platform.startswith("linux"):
        return Path(os.readlink(f"/proc/self/fd/{descriptor}"))
    raise FirmwareError(FirmwareErrorCode.UNSUPPORTED)


class AuthorizedFirmwareStore:
    def __init__(self, root: Path):
        self.root = root.absolute()

    def check_path(self, candidate: Path) -> None:
        for path in reversed((candidate, *candidate.parents)):
            deny_links(path)

    @contextmanager
    def lock_parents(self, candidate: Path):
        with ExitStack() as stack:
            if os.name == "nt":
                for parent in reversed(candidate.parents):
                    deny_links(parent)
                    descriptor = open_readonly(parent, directory=True)
                    stack.callback(os.close, descriptor)
                    if final_path(descriptor) != parent:
                        raise FirmwareError(FirmwareErrorCode.PATH_DENIED)
                    deny_links(parent)
            yield

    @contextmanager
    def open(self, artifact: str):
        try:
            validate_relative_path(artifact)
            candidate = self.root.joinpath(*artifact.split("/"))
            self.check_path(candidate)
            attributes = candidate.lstat()
            if not stat.S_ISREG(attributes.st_mode) or attributes.st_nlink != 1:
                raise FirmwareError(FirmwareErrorCode.PATH_DENIED)
            with self.lock_parents(candidate), os.fdopen(open_readonly(candidate), "rb") as stream:
                initial = os.fstat(stream.fileno())
                if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1:
                    raise FirmwareError(FirmwareErrorCode.PATH_DENIED)
                self.check_path(candidate)
                if final_path(stream.fileno()) != candidate or not candidate.is_relative_to(
                    self.root
                ):
                    raise FirmwareError(FirmwareErrorCode.PATH_DENIED)
                current = candidate.stat()
                if (initial.st_dev, initial.st_ino) != (current.st_dev, current.st_ino):
                    raise FirmwareError(FirmwareErrorCode.CHANGED)
                yield stream
                final = os.fstat(stream.fileno())
                if (initial.st_size, initial.st_mtime_ns, initial.st_ino) != (
                    final.st_size,
                    final.st_mtime_ns,
                    final.st_ino,
                ):
                    raise FirmwareError(FirmwareErrorCode.CHANGED)
                self.check_path(candidate)
                if final_path(stream.fileno()) != candidate:
                    raise FirmwareError(FirmwareErrorCode.CHANGED)
        except FileNotFoundError:
            raise FirmwareError(FirmwareErrorCode.NOT_FOUND) from None
        except (OSError, ValueError):
            raise FirmwareError(FirmwareErrorCode.PATH_DENIED) from None
