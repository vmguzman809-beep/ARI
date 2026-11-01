"""Explicit maintenance check using the installed Codex MCP client, without SDK or model turns.

This is not a user CLI. Run separately from pytest; no ADB process or physical device is used.
The first connection reads actual project config. The second overrides only that ephemeral
test session to use tests/codex_fixture_server.py, which has no hardware backend.
"""

import ctypes
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {
    "get_project_status",
    "list_capabilities",
    "detect_devices",
    "inspect_adb_status",
    "get_device_properties",
    "inspect_device",
    "analyze_unlock_compatibility",
    "check_root_compatibility",
    "create_root_plan",
    "analyze_firmware",
    "verify_firmware_hash",
}
CONSENT = {"authorized": True, "simulation": False}


class RpcFailure(Exception):
    """Safe test-harness error. Raw client logs remain in ignored local storage."""

    def __init__(self, message: str, *, rpc_code: int | None = None):
        self.rpc_code = rpc_code
        super().__init__(message)


class CodexClient:
    def __init__(self, binary: str, label: str) -> None:
        self.binary = binary
        self.label = label
        self.counter = 0
        self.messages = queue.Queue()

    def __enter__(self):
        self.stderr = (ROOT / ".ari" / f"codex-{self.label}.stderr.log").open("w", encoding="utf-8")
        try:
            self.process = subprocess.Popen(
                [self.binary, "app-server", "--listen", "stdio://"],
                cwd=ROOT,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self.stderr,
                text=True,
                encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception:
            self.stderr.close()
            raise
        self.reader = threading.Thread(target=self._receive, daemon=True)
        self.reader.start()
        try:
            self.request(
                "initialize",
                {
                    "clientInfo": {"name": "ari_connection_verifier", "version": "0.5.0"},
                    "capabilities": {"experimentalApi": True},
                },
            )
            self._send({"method": "initialized", "params": {}})
        except Exception:
            self.__exit__()
            raise
        return self

    def _receive(self):
        for line in self.process.stdout:
            try:
                self.messages.put(json.loads(line))
            except json.JSONDecodeError:
                self.messages.put({"invalid_json": True})
        self.messages.put(None)

    def _send(self, message):
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def request(self, method: str, params: dict):
        self.counter += 1
        request_id = self.counter
        self._send({"id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + 30
        while True:
            if time.monotonic() >= deadline:
                raise RpcFailure("Codex RPC timeout")
            try:
                response = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                raise RpcFailure("Codex RPC timeout") from None
            if response is None or response.get("invalid_json"):
                raise RpcFailure("Codex disconnected or returned invalid JSON")
            if response.get("id") == request_id and "method" not in response:
                if "error" in response:
                    raise RpcFailure(
                        f"Codex rejected {method}", rpc_code=response["error"].get("code")
                    )
                return response["result"]
            if "id" in response and "method" in response:
                # Never approve an unrelated server request during connection testing.
                self._send(
                    {
                        "id": response["id"],
                        "error": {
                            "code": -32601,
                            "message": "Unsupported during ARI verification",
                        },
                    }
                )

    def call(self, name: str, arguments: dict):
        return self.request(
            "mcpServer/tool/call",
            {
                "threadId": self.thread_id,
                "server": "ari",
                "tool": name,
                "arguments": arguments,
            },
        )

    def __exit__(self, *_):
        self.process.stdin.close()
        forced = False
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            forced = True
            self.process.terminate()
            self.process.wait(timeout=5)
        self.reader.join(timeout=2)
        self.process.stdout.close()
        self.stderr.close()
        if forced or self.process.returncode != 0:
            raise RpcFailure("Codex did not close normally")


def lifecycle(path: Path) -> tuple[dict[str, int], set[str]]:
    started, stopped = {}, set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event["event"] == "runtime_started":
                started[event["run_id"]] = event.get("process_id", 0)
            elif event["event"] == "runtime_stopped":
                stopped.add(event["run_id"])
    return started, stopped


def process_exited(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE, read-only wait handle
        if not handle:
            return ctypes.get_last_error() == 87  # ERROR_INVALID_PARAMETER: PID is gone
        try:
            return kernel.WaitForSingleObject(handle, 0) == 0
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)  # POSIX existence check only; never used on Windows
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def success(result: dict) -> dict:
    if result.get("isError") is not False:
        raise RpcFailure("Expected a successful tool result")
    return result["structuredContent"]


def failure(result: dict, code: str) -> None:
    if (
        not result.get("isError")
        or result.get("structuredContent", {}).get("error", {}).get("code") != code
    ):
        raise RpcFailure("Expected a specific safe error code")


def configuration_summary(response: dict, project: Path) -> dict[str, bool]:
    """Report configuration scope only; this is never proof of a model's native tools."""
    project_layer = any(
        layer.get("name", {}).get("type") == "project"
        and Path(layer["name"].get("dotCodexFolder", "")).resolve() == project / ".codex"
        for layer in response.get("layers") or []
    )
    entry = response.get("config", {}).get("mcp_servers", {}).get("ari", {})
    return {
        "project_layer_loaded": project_layer,
        "ari_enabled": entry.get("enabled") is True,
        "exact_read_only_allowlist": set(entry.get("enabled_tools") or []) == TOOLS,
    }


def verify(binary: str, *, synthetic: bool) -> dict:
    label = "synthetic" if synthetic else "production"
    data_dir = ROOT / ".ari" / "codex-synthetic" if synthetic else ROOT / ".ari"
    log = data_dir / "logs" / "ari.jsonl"
    before, _ = lifecycle(log)
    cases = []
    with CodexClient(binary, label) as client:
        if not synthetic:
            effective = client.request("config/read", {"cwd": str(ROOT), "includeLayers": True})
            summary = configuration_summary(effective, ROOT)
            assert all(summary.values()), "Project-scoped MCP configuration is incomplete"
            cases += ["effective_project_configuration", "project_layer_loaded"]
        params = {"cwd": str(ROOT), "ephemeral": True}
        if synthetic:
            params["config"] = {
                "mcp_servers.ari.command": sys.executable,
                "mcp_servers.ari.args": [str(ROOT / "tests" / "codex_fixture_server.py")],
                "mcp_servers.ari.env.ARI_DATA_DIR": str(data_dir),
            }
        started = client.request("thread/start", params)
        assert started["thread"]["ephemeral"] is True
        client.thread_id = started["thread"]["id"]
        status = client.request(
            "mcpServerStatus/list",
            {
                "threadId": client.thread_id,
                "serverName": "ari",
                "detail": "toolsAndAuthOnly",
            },
        )
        ari = next(server for server in status["data"] if server["name"] == "ari")
        assert ari["runtimeStatus"] == "connected"
        assert ari["serverInfo"]["version"] == "0.5.0"
        assert set(ari["tools"]) == TOOLS
        for tool in ari["tools"].values():
            assert tool["annotations"]["readOnlyHint"] is True
            assert tool["annotations"]["destructiveHint"] is False
            assert tool["inputSchema"]["additionalProperties"] is False
            assert tool["outputSchema"]
        cases += ["startup_connected", "eleven_read_only_tools_and_typed_schemas"]
        assert success(client.call("get_project_status", {}))["phase"] == 5
        assert len(success(client.call("list_capabilities", {}))["capabilities"]) == 17
        cases += ["metadata_call", "capabilities_call"]
        failure(client.call("detect_devices", {}), "authorization_required")
        failure(client.call("detect_devices", {"authorized": True}), "simulation_enabled")
        failure(client.call("inspect_device", {"serial": "SYNTHETIC;invalid"}), "invalid_arguments")
        failure(client.call("inspect_device", {}), "invalid_arguments")
        try:
            failure(client.call("reboot", {}), "unknown_tool")
        except RpcFailure as error:
            # Codex can reject an unadvertised tool before forwarding it to the server.
            if error.rpc_code is None:
                raise
        assert success(client.call("get_project_status", {}))["phase"] == 5
        cases += [
            "default_authorization_denied",
            "simulation_denied",
            "invalid_serial_denied",
            "missing_serial_denied",
            "reboot_not_registered",
        ]
        research = {"research": {"target": {"identity": {"model": "SYNTHETIC-RESEARCH"}}}}
        assert success(client.call("analyze_unlock_compatibility", research))["state"] == "unknown"
        assert (
            success(client.call("check_root_compatibility", research))["magisk"]["value"]
            == "unknown"
        )
        plan = success(client.call("create_root_plan", research))
        assert plan["executable"] is False and plan["status"] == "blocked"
        failure(
            client.call("create_root_plan", {**research, "shell": "SYNTHETIC"}), "invalid_arguments"
        )
        cases += [
            "offline_bootloader",
            "offline_compatibility",
            "theoretical_plan",
            "research_extra_rejected",
        ]
        failure(
            client.call("verify_firmware_hash", {"request": {"artifact": "SYNTHETIC.img"}}),
            "file_authorization_required",
        )
        failure(
            client.call(
                "analyze_firmware",
                {"request": {"artifact": "SYNTHETIC.img", "expected_identity": {}}},
            ),
            "file_authorization_required",
        )
        failure(
            client.call(
                "verify_firmware_hash",
                {"request": {"artifact": "../SYNTHETIC.img", "authorized": True}},
            ),
            "invalid_arguments",
        )
        cases += [
            "hash_requires_file_authorization",
            "analysis_requires_file_authorization",
            "path_traversal_rejected",
        ]
        if synthetic:
            file_request = {"artifact": "SYNTHETIC-CODEX.img", "authorized": True}
            before_hash = success(client.call("verify_firmware_hash", {"request": file_request}))
            analysis = success(
                client.call(
                    "analyze_firmware",
                    {
                        "request": {
                            **file_request,
                            "expected_identity": {},
                            "research": {"target": {"identity": {}}},
                        }
                    },
                )
            )
            assert analysis["firmware"]["images"][0]["header_version"] == 3
            assert analysis["plan"]["executable"] is False
            assert analysis["firmware"]["integrity"]["sha256"] == before_hash["sha256"]
            assert (
                success(client.call("verify_firmware_hash", {"request": file_request}))["sha256"]
                == before_hash["sha256"]
            )
            cases += [
                "synthetic_static_hash",
                "synthetic_static_analysis",
                "synthetic_original_preserved",
            ]
            inventory = success(client.call("detect_devices", CONSENT))
            assert len(inventory["devices"]) == 3
            target = {"serial": "SYNTHETIC-CODEX-1", **CONSENT}
            assert success(client.call("inspect_adb_status", target))["state"] == "device"
            assert len(success(client.call("get_device_properties", target))["readings"]) == 12
            inspection = success(client.call("inspect_device", target))
            assert inspection["snapshot"]["identity"]["manufacturer"] == "SYNTHETIC; NO HARDWARE"
            failure(
                client.call("inspect_device", {**target, "serial": "SYNTHETIC-CODEX-2"}),
                "device_offline",
            )
            failure(
                client.call("inspect_device", {**target, "serial": "SYNTHETIC-CODEX-3"}),
                "device_unauthorized",
            )
            failure(
                client.call("inspect_device", {**target, "serial": "SYNTHETIC-MISSING"}),
                "device_not_found",
            )
            failure(client.call("detect_devices", {}), "authorization_required")
            cases += [
                "synthetic_inventory",
                "synthetic_selected_state",
                "synthetic_properties",
                "synthetic_inspection",
                "offline_error",
                "unauthorized_error",
                "missing_target_error",
                "consent_not_reused",
            ]
    after, stopped = lifecycle(log)
    new_runs = set(after) - set(before)
    deadline = time.monotonic() + 5
    while new_runs and not all(process_exited(after[run]) for run in new_runs):
        if time.monotonic() >= deadline:
            raise RpcFailure("Codex left an ARI process running")
        time.sleep(0.1)
    assert new_runs, "No new ARI process was observed"
    cases += ["codex_exit_zero", "ari_process_terminated"]
    return {
        "backend": label,
        "cases_passed": cases,
        "hardware_access": False,
        "python_finalizer_observed": new_runs <= stopped,
    }


def main():
    binary = shutil.which("codex")
    if binary is None:
        raise RpcFailure("Installed Codex client not found")
    (ROOT / ".ari").mkdir(exist_ok=True)
    version = subprocess.run(
        [binary, "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    ).stdout.strip()
    report = {
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "codex_version": version,
        "client": "installed Codex App Server acting as MCP client",
        "verification_scope": "app_server_protocol_only",
        "native_chat_tools_verified": False,
        "sdk_client_used": False,
        "model_turns_started": False,
        "runs": [verify(binary, synthetic=False), verify(binary, synthetic=True)],
    }
    (ROOT / ".ari" / "codex-verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
