"""Configuration scope tests, without Codex processes or Android hardware."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify-codex-mcp.py"
SPEC = importlib.util.spec_from_file_location("codex_configuration_verifier", SCRIPT)
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def response(project: Path) -> dict:
    return {
        "config": {
            "mcp_servers": {
                "ari": {
                    "enabled": True,
                    "enabled_tools": sorted(VERIFIER.TOOLS),
                }
            }
        },
        "layers": [{"name": {"type": "project", "dotCodexFolder": str(project / ".codex")}}],
    }


def test_effective_configuration_requires_matching_project_layer(tmp_path):
    project = tmp_path.resolve()
    result = VERIFIER.configuration_summary(response(project), project)
    assert all(result.values())
    assert "native_chat_tools_verified" not in result
    assert not VERIFIER.configuration_summary(response(project), project / "other")[
        "project_layer_loaded"
    ]


def test_user_configuration_is_not_mistaken_for_project_scope(tmp_path):
    data = response(tmp_path)
    data["layers"] = [{"name": {"type": "user", "file": "synthetic/config.toml"}}]
    result = VERIFIER.configuration_summary(data, tmp_path)
    assert result["ari_enabled"] is True
    assert result["project_layer_loaded"] is False


def test_missing_disabled_or_expanded_allowlist_is_not_ready(tmp_path):
    assert not any(VERIFIER.configuration_summary({}, tmp_path).values())
    data = response(tmp_path)
    data["config"]["mcp_servers"]["ari"]["enabled"] = False
    assert not VERIFIER.configuration_summary(data, tmp_path)["ari_enabled"]
    data["config"]["mcp_servers"]["ari"]["enabled_tools"].append("reboot")
    assert not VERIFIER.configuration_summary(data, tmp_path)["exact_read_only_allowlist"]
