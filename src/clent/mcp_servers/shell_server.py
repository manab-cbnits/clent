"""
Shell Command MCP Server
========================
Exposes a single tool — `execute_shell_command` — that lets the agent run
arbitrary shell commands on the host system and get back stdout, stderr, and
the exit code.

Run as a subprocess (stdio transport); do NOT import this file directly.
"""

import logging
import subprocess

from mcp.server.fastmcp import FastMCP

# Suppress noisy MCP protocol debug messages (e.g. "Processing request of type ...")
logging.getLogger("mcp.server").setLevel(logging.WARNING)

mcp = FastMCP("shell")


@mcp.tool(
    description=(
        "Execute a shell command on the system and return its output. "
        "Use this tool whenever the user asks you to run a command, inspect "
        "the filesystem, check system info, manage processes, or do anything "
        "that requires interacting with the operating system. "
        "\n\n"
        "Parameters:\n"
        "  command  — the full shell command string to execute (e.g. 'ls -la', 'pwd', 'git status').\n"
        "  timeout  — maximum seconds to wait before killing the process (default: 30).\n"
        "\n"
        "Returns a JSON-like dict with:\n"
        "  stdout   — captured standard output (may be empty string).\n"
        "  stderr   — captured standard error (may be empty string).\n"
        "  exit_code — integer exit code (0 = success, non-zero = error).\n"
        "  timed_out — bool, True if the command was killed due to timeout.\n"
        "\n"
        "⚠️  This tool has unrestricted access to the system. Only run commands "
        "that the user has explicitly requested or that are clearly safe and "
        "reversible. Never delete, overwrite, or exfiltrate data without "
        "explicit user confirmation."
    )
)
def execute_shell_command(command: str, timeout: int = 30) -> dict:
    """Run *command* in a shell subprocess and return the result."""
    timed_out = False
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        stdout = ""
        stderr = f"Command timed out after {timeout} seconds."
        exit_code = -1
        timed_out = True
    except Exception as exc:  # noqa: BLE001
        stdout = ""
        stderr = f"Failed to execute command: {exc}"
        exit_code = -1

    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "timed_out": timed_out,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
