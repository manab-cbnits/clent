import sys
from clent.states import AgentState
from clent.config import (
    load_settings,
    save_settings,
    is_configured,
    DEFAULT_SETTINGS,
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _prompt(label: str, current: str, placeholder: str = "") -> str:
    """
    Show a single setup prompt. Returns the user's input, or *current*
    if the user just pressed Enter, or *placeholder* if both are empty.
    """
    display = current or placeholder
    hint = f" [{display}]" if display else ""
    try:
        value = input(f"  {label}{hint}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return current or placeholder
    return value if value else (current or placeholder)


def _run_wizard(settings: dict) -> dict:
    """Interactively fill in settings and return the updated dict."""
    print("\n⚙  Setup  (press Enter to keep the current value / skip)\n")

    env = settings.get("env", {})
    models = env.get("CLENT_MODELS", {})

    api_key   = _prompt("API key",               env.get("CLENT_API_KEY", ""))
    base_url  = _prompt("Base URL for the model", env.get("CLENT_BASE_URL", ""))
    default_m = _prompt("Default model name",     models.get("default", ""))
    thinking_m = _prompt("Thinking model name",   models.get("thinking", ""))
    code_m    = _prompt("Code model name",         models.get("code", ""))
    sess_dir  = _prompt("Sessions directory",      settings.get("sessions_dir", ""), "sessions")
    theme     = _prompt("UI theme (dark/light)",   settings.get("theme", ""),        "dark")

    updated = {
        "env": {
            "CLENT_API_KEY":  api_key,
            "CLENT_BASE_URL": base_url,
            "CLENT_MODELS": {
                "default":  default_m,
                "thinking": thinking_m,
                "code":     code_m,
            },
        },
        "sessions_dir": sess_dir,
        "theme":        theme,
    }

    save_settings(updated)
    print("\n✔  Settings saved to settings.json")
    print("   Please restart clent for the changes to take effect.\n")
    sys.exit(0)


# ─────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────

def Setup_Node(state: AgentState) -> dict:
    """
    First node in the graph.

    • On first run (settings.json missing or required keys empty): runs the
      interactive setup wizard, saves settings.json, then exits so the user
      can restart with a fully configured environment.

    • When the user typed /config (state["run_setup"] is True): same wizard.

    • Otherwise (already configured): pure pass-through, returns {} immediately.
    """
    settings = load_settings()

    if state.get("run_setup") or not is_configured(settings):
        # Merge loaded settings on top of defaults so we don't lose any existing keys
        merged = {**DEFAULT_SETTINGS, **settings}
        merged["env"] = {**DEFAULT_SETTINGS.get("env", {}), **settings.get("env", {})}
        merged["env"]["CLENT_MODELS"] = {
            **DEFAULT_SETTINGS.get("env", {}).get("CLENT_MODELS", {}),
            **settings.get("env", {}).get("CLENT_MODELS", {}),
        }
        _run_wizard(merged)

    # Pass-through — no state mutation needed
    return {}
