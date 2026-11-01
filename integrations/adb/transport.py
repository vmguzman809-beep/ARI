"""The only process boundary: three typed read operations, no arbitrary argv API."""

import math
import os
import shutil
import subprocess
from pathlib import Path

from pydantic import ValidationError

from ari.device.adb import AdbReadOperation, AdbRequest
from ari.device.errors import AdbError, AdbErrorCode
from ari.security.policy import DeviceOperation, PhaseTwoPolicy

_HOST_ENV = frozenset(
    {
        "SYSTEMROOT",
        "WINDIR",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "HOMEDRIVE",
        "HOMEPATH",
        "HOME",
        "PATH",
        "PATHEXT",
        "TEMP",
        "TMP",
    }
)


def resolve_adb_executable(configured_path: Path | None = None) -> Path:
    """Resolve a native executable from an explicit absolute path or PATH, without running it."""
    name = "adb.exe" if os.name == "nt" else "adb"
    if configured_path is not None and not isinstance(configured_path, Path):
        raise AdbError(AdbErrorCode.INVALID_EXECUTABLE)
    if configured_path is None:
        # Windows which("adb.exe") can implicitly search CWD. Search only absolute
        # PATH entries and pass a full filename to avoid a project-local executable.
        found = None
        for directory in os.get_exec_path():
            if Path(directory).is_absolute():
                found = shutil.which(str(Path(directory) / name))
                if found is not None:
                    break
        if found is None:
            raise AdbError(AdbErrorCode.TOOL_NOT_FOUND)
        configured_path = Path(found)
    if not configured_path.is_absolute() or configured_path.name.casefold() != name:
        raise AdbError(AdbErrorCode.INVALID_EXECUTABLE)
    try:
        resolved = configured_path.resolve(strict=True)
    except (OSError, RuntimeError):
        raise AdbError(AdbErrorCode.TOOL_NOT_FOUND) from None
    if not resolved.is_file() or resolved.name.casefold() != name:
        raise AdbError(AdbErrorCode.INVALID_EXECUTABLE)
    return resolved


def _classify_failure(text: str) -> AdbErrorCode:
    text = text.casefold()
    if "unauthorized" in text:
        return AdbErrorCode.DEVICE_UNAUTHORIZED
    if "offline" in text:
        return AdbErrorCode.DEVICE_OFFLINE
    if "more than one" in text:
        return AdbErrorCode.AMBIGUOUS_TARGET
    if "no devices" in text:
        return AdbErrorCode.NO_DEVICES
    if "not found" in text or "disconnected" in text:
        return AdbErrorCode.DEVICE_NOT_FOUND
    if "permission denied" in text or "no permissions" in text:
        return AdbErrorCode.ACCESS_DENIED
    if "cannot connect" in text or "cannot start" in text or "server version" in text:
        return AdbErrorCode.SERVER_UNAVAILABLE
    return AdbErrorCode.COMMAND_FAILED


class AdbSubprocessTransport:
    def __init__(
        self,
        executable: Path | None = None,
        *,
        authorized: bool = False,
        simulation: bool = True,
        timeout_seconds: float = 5.0,
    ) -> None:
        if type(authorized) is not bool or type(simulation) is not bool:
            raise ValueError("Authorization and simulation must be explicit booleans")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or not 0.1 <= timeout_seconds <= 10
        ):
            raise ValueError("ADB timeout must be finite and between 0.1 and 10 seconds")
        self._configured_path = executable
        self._executable: Path | None = None
        self._authorized = authorized
        self._simulation = simulation
        self._timeout = timeout_seconds

    def execute(self, request: AdbRequest) -> str:
        if not isinstance(request, AdbRequest):
            raise AdbError(AdbErrorCode.INVALID_REQUEST)
        # Revalidate even instances forged through Pydantic's model_construct/model_copy.
        try:
            request = AdbRequest.model_validate(request.model_dump(warnings=False))
        except ValidationError:
            raise AdbError(AdbErrorCode.INVALID_REQUEST) from None
        decision = PhaseTwoPolicy().evaluate(
            DeviceOperation.INSPECT, authorized=self._authorized, simulation=self._simulation
        )
        if not decision.allowed:
            code = (
                AdbErrorCode.AUTHORIZATION_REQUIRED
                if not self._authorized
                else AdbErrorCode.SIMULATION_ENABLED
            )
            raise AdbError(code)
        if self._executable is None:
            self._executable = resolve_adb_executable(self._configured_path)
        argv = [str(self._executable), "-H", "127.0.0.1", "-P", "5037"]
        if request.operation == AdbReadOperation.DEVICES:
            argv += ["devices", "-l"]
        else:
            argv += ["-s", request.serial]
            if request.operation == AdbReadOperation.STATE:
                argv += ["get-state"]
            else:
                argv += ["shell", "-T", "getprop", request.property.value]
        env = {key: value for key, value in os.environ.items() if key.upper() in _HOST_ENV}
        try:
            result = subprocess.run(
                argv,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                shell=False,
                timeout=self._timeout,
                check=False,
                env=env,
                cwd=str(self._executable.parent),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except subprocess.TimeoutExpired:
            raise AdbError(AdbErrorCode.TIMEOUT) from None
        except FileNotFoundError:
            raise AdbError(AdbErrorCode.TOOL_NOT_FOUND) from None
        except PermissionError:
            raise AdbError(AdbErrorCode.ACCESS_DENIED) from None
        except OSError:
            raise AdbError(AdbErrorCode.COMMAND_FAILED) from None
        if len(result.stdout) + len(result.stderr) > 65_536:
            raise AdbError(AdbErrorCode.INVALID_RESPONSE)
        if result.returncode != 0:
            details = (result.stderr + result.stdout).decode("utf-8", errors="replace")
            raise AdbError(_classify_failure(details))
        stderr = result.stderr.decode("utf-8", errors="replace")
        notices = {
            "* daemon not running; starting now at tcp:5037",
            "* daemon started successfully",
        }
        unexpected = "\n".join(line for line in stderr.splitlines() if line.strip() not in notices)
        if unexpected.strip():
            raise AdbError(_classify_failure(unexpected))
        try:
            return result.stdout.decode("utf-8")
        except UnicodeDecodeError:
            raise AdbError(AdbErrorCode.INVALID_RESPONSE) from None
