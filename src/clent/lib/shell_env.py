import os
import platform


def _detect_shell_name(system: str) -> str:
    if system == "windows":
        # Best-effort detection: COMSPEC is the default command processor,
        # and PowerShell-hosted sessions almost always expose PSModulePath.
        if os.environ.get("PSModulePath") or os.environ.get("PSExecutionPolicyPreference"):
            return "powershell"
        return "cmd"

    return os.environ.get("SHELL", "unknown")


def get_shell_environment_hint() -> str:
    """
    Detect the current OS/shell environment and return a short, LLM-friendly
    execution hint.

    Intended use:
    - prepend/append into a system prompt
    - help an LLM generate valid shell commands
    - avoid wrong platform assumptions (paths, utilities, quoting)
    """

    system = platform.system().lower()
    shell_name = _detect_shell_name(system)

    if system == "windows":
        comspec = os.environ.get("COMSPEC", "unknown")
        return (
            "Shell environment:\n"
            "- OS=windows\n"
            f"- SHELL={shell_name}\n"
            f"- COMSPEC={comspec}\n\n"
            "Command guidance (Windows):\n"
            "- Prefer PowerShell syntax unless explicitly asked for CMD.\n"
            "- Avoid Unix-only utilities (sed/awk/grep) unless confirmed installed.\n"
            "- Use Windows paths (e.g. `C:\\path\\to\\file`) and quote paths with spaces.\n"
        )

    if system == "darwin":
        return (
            "Shell environment:\n"
            "- OS=darwin\n"
            f"- SHELL={shell_name}\n\n"
            "Command guidance (macOS):\n"
            "- Use bash/zsh-compatible commands.\n"
            "- Note: macOS uses BSD variants for some utilities.\n"
        )

    if system == "linux":
        return (
            "Shell environment:\n"
            "- OS=linux\n"
            f"- SHELL={shell_name}\n\n"
            "Command guidance (Linux):\n"
            "- Use standard POSIX/bash shell commands.\n"
        )

    return (
        "Shell environment:\n"
        f"- OS={system}\n"
        f"- SHELL={shell_name}\n\n"
        "Command guidance:\n"
        "- Use portable shell commands when possible.\n"
    )

