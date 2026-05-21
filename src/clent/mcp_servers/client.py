"""
MCP Client Configuration
========================
This is the **single place** to register MCP servers for the clent agent.

To add a new MCP server:
  1. Create a new server script under `src/clent/mcp_servers/`.
  2. Add an entry to the dict returned by `get_mcp_servers_config()` below.
  3. That's it — the Chat node picks it up automatically.

Transport options:
  - "stdio"  : agent spawns the server as a subprocess (best for local tools).
  - "sse"    : agent connects to a running HTTP server (best for remote tools).
"""

from pathlib import Path

# Absolute path to this package directory — used to locate server scripts.
_SERVERS_DIR = Path(__file__).parent


def get_mcp_servers_config() -> dict:
    """
    Return a MultiServerMCPClient-compatible config dict.

    Each key is a logical server name (used for namespacing in logs).
    Each value is a connection spec understood by langchain-mcp-adapters.

    Example of adding a future server:
        "filesystem": {
            "command": sys.executable,
            "args": [str(_SERVERS_DIR / "filesystem_server.py")],
            "transport": "stdio",
        },
    """
    import sys

    return {
        # ── Shell tool ────────────────────────────────────────────────────────
        "shell": {
            "command": sys.executable,          # uses the active venv Python
            "args": [str(_SERVERS_DIR / "shell_server.py")],
            "transport": "stdio",
        },

        # ── Add future MCP servers below ──────────────────────────────────────
        # "my_tool": {
        #     "command": sys.executable,
        #     "args": [str(_SERVERS_DIR / "my_tool_server.py")],
        #     "transport": "stdio",
        # },
    }
