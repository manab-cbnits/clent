import json
import os
from pathlib import Path


# ==========================================
# PATHS
# ==========================================

_PKG_ROOT = Path(__file__).parent
_PACKAGED_SETTINGS_PATH = _PKG_ROOT / "settings.json"


def get_clent_home() -> Path:
    """
    Return the per-user clent directory.

    Override with `CLENT_HOME`.

    Windows: %LOCALAPPDATA%\\clent
    Others : $XDG_CONFIG_HOME/clent or ~/.config/clent
    """
    override = (os.getenv("CLENT_HOME") or "").strip()
    if override:
        return Path(override).expanduser()

    candidates: list[Path] = []

    if os.name == "nt":
        local = (os.getenv("LOCALAPPDATA") or "").strip()
        roaming = (os.getenv("APPDATA") or "").strip()
        home = str(Path.home())
        candidates.extend(
            [
                Path(local) / "clent" if local else None,
                Path(roaming) / "clent" if roaming else None,
                Path(home) / ".clent",
                Path.cwd() / ".clent",
            ]
        )
    else:
        xdg = (os.getenv("XDG_CONFIG_HOME") or "").strip()
        candidates.extend(
            [
                (Path(xdg).expanduser() / "clent") if xdg else None,
                Path.home() / ".config" / "clent",
                Path.cwd() / ".clent",
            ]
        )

    for p in [c for c in candidates if isinstance(c, Path)]:
        try:
            p.mkdir(parents=True, exist_ok=True)
            test_path = p / ".write_test"
            with open(test_path, "w", encoding="utf-8") as f:
                f.write("ok")
            try:
                test_path.unlink(missing_ok=True)
            except TypeError:
                if test_path.exists():
                    test_path.unlink()
            return p
        except OSError:
            continue

    # Last resort: a directory under the current working directory.
    fallback = Path.cwd() / ".clent"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_settings_path() -> Path:
    return get_clent_home() / "settings.json"


def get_credentials_path() -> Path:
    return get_clent_home() / "credentials.json"


def get_token_path() -> Path:
    return get_clent_home() / "token.json"


SETTINGS_PATH = get_settings_path()


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
    # Prefer per-user settings (supports site-packages being read-only).
    if not SETTINGS_PATH.exists():
        # One-time migration from older installs/dev runs where settings lived in the package dir.
        if _PACKAGED_SETTINGS_PATH.exists():
            try:
                with open(_PACKAGED_SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    try:
                        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
                        with open(SETTINGS_PATH, "w", encoding="utf-8") as out:
                            json.dump(data, out, indent=4, ensure_ascii=False)
                        return data
                    except OSError:
                        # If the per-user dir isn't writable, just use the packaged settings for this run.
                        return data
            except (json.JSONDecodeError, OSError):
                pass

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
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except OSError as exc:
        raise OSError(
            f"Unable to write settings to {SETTINGS_PATH}. "
            f"Set CLENT_HOME to a writable directory. ({exc})"
        ) from exc


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

    - Relative values (e.g. "sessions") are resolved relative to the per-user clent directory.
    - Absolute values are used as-is.
    - Falls back to <clent_home>/sessions when the key is absent or empty.
    """
    settings = load_settings()
    raw = settings.get("sessions_dir", "").strip()
    if not raw:
        return get_clent_home() / "sessions"
    p = Path(raw)
    return p if p.is_absolute() else get_clent_home() / p


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
