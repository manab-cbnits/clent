import json
import shutil
import uuid
from pathlib import Path
from typing import List, Dict, TypedDict, Optional, Any


# ==========================================
# CONFIG
# ==========================================

BASE_DIR = Path(__file__).parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"


class Message(TypedDict):
    role: str
    content: str

class SessionMetadata(TypedDict, total=False):
    name: str
    preview: str


# ==========================================
# HELPERS
# ==========================================

def load_messages(session_id: str) -> List[Message]:
    """Load all messages from a session."""
    messages_file = SESSIONS_DIR / session_id / "messages.json"
    if not messages_file.exists():
        raise FileNotFoundError(f"Session '{session_id}' not found.")
    with open(messages_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_messages(session_id: str, messages: List[Message]) -> None:
    """Save messages to disk."""
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    messages_file = session_dir / "messages.json"
    with open(messages_file, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)


def load_metadata(session_id: str) -> SessionMetadata:
    """Load session metadata."""
    metadata_file = SESSIONS_DIR / session_id / "metadata.json"
    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata for session '{session_id}' not found.")
    with open(metadata_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Invalid metadata.json (expected object).")
    name = data.get("name")
    preview = data.get("preview")
    return {
        "name": name if isinstance(name, str) else "",
        "preview": preview if isinstance(preview, str) else "",
    }


def save_metadata(session_id: str, metadata: SessionMetadata) -> None:
    """Save session metadata to disk."""
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = session_dir / "metadata.json"
    normalized: SessionMetadata = {
        "name": (metadata.get("name") or "").strip(),
        "preview": (metadata.get("preview") or "").strip(),
    }
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)


def _one_line(text: str) -> str:
    """Collapse whitespace into a single line."""
    return " ".join(str(text).replace("\r", " ").replace("\n", " ").split())


def _truncate(line: str, width: int) -> str:
    """Truncate a string to `width`, adding '...' if needed."""
    if width <= 0 or len(line) <= width:
        return line
    if width <= 3:
        return "." * width
    return line[: width - 3] + "..."


def _compute_preview_from_messages(messages: List[Message]) -> str:
    pairs = []
    i = 0
    while i < len(messages) - 1 and len(pairs) < 2:
        if messages[i].get("role") == "user" and messages[i + 1].get("role") == "assistant":
            pairs.append((
                _truncate(_one_line(messages[i]["content"]), 30),
                _truncate(_one_line(messages[i + 1]["content"]), 30)
            ))
            i += 2
        else:
            i += 1
    if not pairs:
        return "no messages"
    return " ".join(f"➤ {q} ✤ {a}" for q, a in pairs)


def ensure_metadata(session_id: str, messages: Optional[List[Message]] = None) -> SessionMetadata:
    """Load or create metadata, computing preview if missing."""
    try:
        metadata = load_metadata(session_id)
    except Exception:
        metadata = {"name": "", "preview": ""}

    # Normalise name
    if not isinstance(metadata.get("name"), str):
        metadata["name"] = ""
    # Compute preview if empty
    if not metadata.get("preview"):
        if messages is None:
            try:
                messages = load_messages(session_id)
            except Exception:
                messages = []
        metadata["preview"] = _compute_preview_from_messages(messages)
        save_metadata(session_id, metadata)
    return metadata


def update_metadata_from_messages(session_id: str, messages: List[Message]) -> None:
    """Recalculate and persist preview after message changes."""
    metadata = ensure_metadata(session_id, messages=messages)
    metadata["preview"] = _compute_preview_from_messages(messages)
    save_metadata(session_id, metadata)

    """
    Save session metadata to disk.
    """

    session_dir = SESSIONS_DIR / session_id
    if not session_dir.exists():
        session_dir.mkdir(parents=True, exist_ok=True)

    metadata_file = session_dir / "metadata.json"

    normalized: SessionMetadata = {
        "name": (metadata.get("name") or ""),
        "preview": (metadata.get("preview") or ""),
    }

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)


# ==========================================
# CORE
# ==========================================

# SAVE MESSAGES
def save_message(
    messages: List[Message],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create or update a session, returning success and session_id."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    if session_id is None:
        session_id = uuid.uuid4().hex
    session_dir = SESSIONS_DIR / session_id
    if not session_dir.exists():
        session_dir.mkdir(parents=True, exist_ok=True)

    try:
        save_messages(session_id, messages)
        update_metadata_from_messages(session_id, messages)
        return {
            "success": True,
            "session_id": session_id
        }
    except Exception as e:
        print(f"Failed to save messages. Error: {e}")
        return {
            "success": False,
            "session_id": None
        }


# GET MESSAGES
def get_messages(session_id: str, limit: Optional[int] = 30) -> List[Message]:
    """Retrieve messages. If `limit` is given, return the last `limit` messages"""
    messages = load_messages(session_id)
    if limit and limit > 0:
        return messages[-limit:]
    return messages


# DELETE SESSION
def delete_conversation(session_id: str) -> None:
    """Delete a session completely."""
    session_dir = SESSIONS_DIR / session_id
    if not session_dir.exists():
        raise FileNotFoundError(f"Session '{session_id}' not found.")
    shutil.rmtree(session_dir)
    print(f"Session: {session_id} cleared successfully.")


# LIST CONVERSATIONS
def list_all_sessions() -> list:
    """Return a list of all session IDs."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return [session.name for session in SESSIONS_DIR.iterdir() if session.is_dir()]


# SET SESSION NAME
def set_session_name(session_id: str, name: str) -> None:
    """Set a user-friendly name for the session."""
    metadata = ensure_metadata(session_id)
    metadata["name"] = (name or "").strip()
    save_metadata(session_id, metadata)


# GET SESSION PREVIEW
def get_session_preview(session_id: str) -> str:
    """
    Return the session preview.
    If no metadata preview exists, it is computed from stored messages.
    """
    try:
        metadata = load_metadata(session_id)
        preview = (metadata.get("preview") or "").strip()
        if preview:
            return preview
    except Exception:
         # Metadata missing or malformed – we’ll rebuild it.
        pass

    # No valid preview in metadata – compute from messages
    msgs = get_messages(session_id)
    preview = _compute_preview_from_messages(msgs)
    # Persist for next time
    metadata = ensure_metadata(session_id, messages=msgs)
    metadata["preview"] = preview
    save_metadata(session_id, metadata)
    return preview


# LIST SESSIONS WITH PREVIEW
def list_session(width: Optional[int] = None) -> List[str]:
    """
    Return formatted lines: `- <session_id> :: <preview>`,
    truncated to terminal width.
    """
    sessions = list_all_sessions()
    if width is None:
        width = shutil.get_terminal_size((120, 20)).columns

    lines: List[str] = []
    for session_id in sessions:
        display = ""
        try:
            metadata = ensure_metadata(session_id)
            name = (metadata.get("name") or "").strip()
            preview = (metadata.get("preview") or "").strip()
            display = name or preview
        except Exception:
            pass

        line = f"- {session_id}"
        if display:
            line += f" :: {display}"
        lines.append(_truncate(line, width))

    return lines
