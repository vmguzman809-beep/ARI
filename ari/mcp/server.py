"""STDIO entry point for a future Codex connection; not an independent user CLI."""

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from ari.core.capabilities import CapabilityCatalog, ProjectStatus
from ari.core.capabilities import list_capabilities as capability_catalog
from ari.core.runtime import AriRuntime
from ari.core.settings import Settings


def create_server() -> MCPServer:
    server = MCPServer(
        "ARI",
        instructions=(
            "Phase 1 foundation only. No Android device access or modification tools. "
            "Pending capabilities must never be represented as operational."
        ),
    )
    annotations = ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )

    @server.tool(annotations=annotations)
    def get_project_status() -> ProjectStatus:
        """Return static phase/safety metadata; performs no device inspection."""
        return ProjectStatus()

    @server.tool(annotations=annotations)
    def list_capabilities() -> CapabilityCatalog:
        """Distinguish implemented metadata tools from unimplemented roadmap items."""
        return capability_catalog()

    return server


def main() -> None:
    with AriRuntime(Settings.from_environment()):
        create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
