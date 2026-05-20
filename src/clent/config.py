import json
from pathlib import Path


# ==========================================
# PATHS
# ==========================================

SETTINGS_PATH = Path(__file__).parent / "settings.json"
_PKG_ROOT = Path(__file__).parent


# ==========================================
# DEFAULTS
# ==========================================

DEFAULT_SETTINGS: dict = {
    "env": {
        "CLENT_API_KEY": "",
        "CLENT_BASE_URL": "",
        "CLENT_MODELS": {
            "default": "",
            "thinking": "",
            "code": "",
        },
    },
    "theme": "dark",
    "sessions_dir": "sessions",
}


# ==========================================
# LOAD / SAVE
# ==========================================

def load_settings() -> dict:
    """Read settings.json; returns DEFAULT_SETTINGS if file is absent or malformed."""
    if not SETTINGS_PATH.exists():
        return DEFAULT_SETTINGS

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return DEFAULT_SETTINGS
        return data
    except (json.JSONDecodeError, OSError):
        return DEFAULT_SETTINGS


def save_settings(data: dict) -> None:
    """Atomically write *data* to settings.json."""
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ==========================================
# VALIDATION
# ==========================================

def is_configured(settings: dict | None = None) -> bool:
    """Return True only when all required keys are non-empty strings."""
    s = settings if settings is not None else load_settings()
    env = s.get("env", {})
    required = [
        env.get("CLENT_API_KEY", ""),
        env.get("CLENT_MODELS", {}).get("default", ""),
    ]
    return all(isinstance(v, str) and v.strip() for v in required)


# ==========================================
# ACCESSORS (lazy — read settings at call time)
# ==========================================

def get_sessions_dir() -> Path:
    """
    Resolve the sessions directory from settings.json.

    - Relative values (e.g. "sessions") are resolved relative to the package root.
    - Absolute values are used as-is.
    - Falls back to <pkg>/sessions when the key is absent or empty.
    """
    settings = load_settings()
    raw = settings.get("sessions_dir", "").strip()
    if not raw:
        return _PKG_ROOT / "sessions"
    p = Path(raw)
    return p if p.is_absolute() else _PKG_ROOT / p


def get_theme() -> str:
    return load_settings().get("theme", "dark")


def get_api_key() -> str:
    api_key = load_settings().get("env", {}).get("CLENT_API_KEY", "").strip()
    if api_key:
        return api_key
    raise ValueError("API key is not set. Run /config or set CLENT_API_KEY in settings.json.")


def get_model_name() -> str:
    model = load_settings().get("env", {}).get("CLENT_MODELS", {}).get("default", "").strip()
    if model:
        return model
    raise ValueError("Default model is not set. Run /config or set CLENT_MODELS.default in settings.json.")


def get_base_url() -> str | None:
    url = load_settings().get("env", {}).get("CLENT_BASE_URL", "").strip()
    return url or None