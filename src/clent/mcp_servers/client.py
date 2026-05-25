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

import shutil
import sys
from pathlib import Path

from clent.config import get_credentials_path, get_token_path

# Absolute path to this package directory — used to locate server scripts.
_SERVERS_DIR = Path(__file__).parent


def _maybe_migrate_packaged_file(packaged_path: Path, dest_path: Path) -> Path:
    """
    Best-effort one-time migration from older installs/dev runs where files
    lived inside the package directory (site-packages).
    """
    if dest_path.exists() or not packaged_path.exists():
        return dest_path
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(packaged_path, dest_path)
        return dest_path
    except OSError:
        # If we can't copy (permissions), fall back to packaged path.
        return packaged_path


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

    # Determine the project root directory (package dir)
    project_root = Path(__file__).resolve().parent.parent

    servers = {
        # ── Shell tool ────────────────────────────────────────────────────────
        "shell": {
            "command": sys.executable,          # uses the active venv Python
            "args": [str(_SERVERS_DIR / "shell_server.py")],
            "transport": "stdio",
        },
    }

    # ── Gmail tool ────────────────────────────────────────────────────────
    # Gmail tool (optional). Skip cleanly if creds or executable aren't present.
    creds_path = _maybe_migrate_packaged_file(
        project_root / "credentials.json",
        get_credentials_path(),
    )
    token_path = _maybe_migrate_packaged_file(
        project_root / "token.json",
        get_token_path(),
    )

    servers["gmail"] = {
        "command": sys.executable,
        "args": [
            str(_SERVERS_DIR / "gmail_server.py"),
            "--creds-file-path",
            str(creds_path),
            "--token-path",
            str(token_path),
        ],
        "transport": "stdio",
    }

    return servers
