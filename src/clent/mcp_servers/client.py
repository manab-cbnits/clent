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

import sys
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

    # Determine the project root directory
    project_root = Path(__file__).resolve().parent.parent
    
    # Path to the 'gmail' executable in the current virtualenv
    gmail_exe_name = "gmail.exe" if sys.platform == "win32" else "gmail"
    gmail_bin = Path(sys.executable).parent / gmail_exe_name

    servers = {
        # ── Shell tool ────────────────────────────────────────────────────────
        "shell": {
            "command": sys.executable,          # uses the active venv Python
            "args": [str(_SERVERS_DIR / "shell_server.py")],
            "transport": "stdio",
        },
    }

    # ── Gmail tool ────────────────────────────────────────────────────────
    creds_path = project_root  / "credentials.json"
    if creds_path.exists():
        servers["gmail"] = {
            "command": str(gmail_bin),
            "args": [
                "--creds-file-path", str(creds_path),
                "--token-path", str(project_root / "token.json")
            ],
            "transport": "stdio",
        }
    else:
        print(f"Warning: Skipping gmail MCP server because {creds_path} was not found.")

    return servers
