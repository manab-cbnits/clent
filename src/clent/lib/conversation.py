import json
import shutil
import uuid
from typing import Any, Dict, List, Optional, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from clent.config import get_sessions_dir


class Message(TypedDict):
    role: str
    content: str

class SessionMetadata(TypedDict, total=False):
    name: str
    preview: str
    summary: str


# ==========================================
# HELPERS
# ==========================================


def _message_to_record(message: Any) -> Message:
    if isinstance(message, dict):
        role = str(message.get("role") or "user").strip() or "user"
        content = str(message.get("content") or "")
        return {"role": role, "content": content}

    if isinstance(message, HumanMessage):
        return {"role": "user", "content": message.content or ""}

    if isinstance(message, AIMessage):
        return {"role": "assistant", "content": message.content or ""}

    if isinstance(message, SystemMessage):
        return {"role": "system", "content": message.content or ""}

    content = getattr(message, "content", "")
    role = getattr(message, "type", "user")
    if role == "human":
        role = "user"
    elif role == "ai":
        role = "assistant"
    return {"role": str(role), "content": str(content or "")}


def _record_to_message(record: Any) -> BaseMessage:
    if isinstance(record, BaseMessage):
        return record

    if not isinstance(record, dict):
        return HumanMessage(content=str(record or ""))

    role = str(record.get("role") or "user").strip().lower()
    content = str(record.get("content") or "")

    if role in {"assistant", "ai"}:
        return AIMessage(content=content)
    if role == "system":
        return SystemMessage(content=content)
    return HumanMessage(content=content)


def messages_to_records(messages: Sequence[Any]) -> List[Message]:
    return [_message_to_record(message) for message in messages]


def messages_to_langchain(messages: Sequence[Any]) -> List[BaseMessage]:
    return [_record_to_message(message) for message in messages]

def load_messages(session_id: str) -> List[Message]:
    """Load all messages from a session."""
    messages_file = get_sessions_dir() / session_id / "messages.json"
    if not messages_file.exists():
        raise FileNotFoundError(f"Session '{session_id}' not found.")
    with open(messages_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Invalid messages.json (expected list).")

    records: List[Message] = []
    for item in data:
        record = _message_to_record(item)
        records.append(record)
    return records


def save_messages(session_id: str, messages: Sequence[Any]) -> None:
    """Save messages to disk."""
    session_dir = get_sessions_dir() / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    messages_file = session_dir / "messages.json"
    records = messages_to_records(messages)
    with open(messages_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=4, ensure_ascii=False)


def load_metadata(session_id: str) -> SessionMetadata:
    """Load session metadata."""
    metadata_file = get_sessions_dir() / session_id / "metadata.json"
    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata for session '{session_id}' not found.")
    with open(metadata_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Invalid metadata.json (expected object).")
    name = data.get("name")
    preview = data.get("preview")
    summary = data.get("summary")
    return {
        "name": name if isinstance(name, str) else "",
        "preview": preview if isinstance(preview, str) else "",
        "summary": summary if isinstance(summary, str) else "",
    }


def save_metadata(session_id: str, metadata: SessionMetadata) -> None:
    """Save session metadata to disk."""
    session_dir = get_sessions_dir() / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = session_dir / "metadata.json"
    normalized: SessionMetadata = {
        "name": (metadata.get("name") or "").strip(),
        "preview": (metadata.get("preview") or "").strip(),
        "summary": (metadata.get("summary") or "").strip(),
    }
    try:
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("Failed to save metadata. Try again later")
        raise e


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
        left = _message_to_record(messages[i])
        right = _message_to_record(messages[i + 1])
        if left.get("role") == "user" and right.get("role") == "assistant":
            pairs.append((
                _truncate(_one_line(left["content"]), 30),
                _truncate(_one_line(right["content"]), 30)
            ))
            i += 2
        else:
            i += 1
    if not pairs:
        # Fall back to system messages (e.g. compacted session summaries)
        for msg in messages:
            rec = _message_to_record(msg)
            if rec.get("role") == "system" and rec.get("content"):
                return _truncate(_one_line(rec["content"]), 60)
        return "no messages"
    return " ".join(f"➤ {q} ✤ {a}" for q, a in pairs)


def ensure_metadata(session_id: str, messages: Optional[List[Message]] = None) -> SessionMetadata:
    try:
        metadata = load_metadata(session_id)
    except Exception:
        metadata = {"name": "", "preview": "", "summary": ""}

    # Normalise name (keep existing logic)
    if not isinstance(metadata.get("name"), str):
        metadata["name"] = ""
    # Keep existing summary (do not overwrite)
    if not isinstance(metadata.get("summary"), str):
        metadata["summary"] = ""

    # Compute preview if empty
    if not metadata.get("preview"):
        # Prefer summary-based preview for compacted sessions
        if metadata.get("summary"):
            metadata["preview"] = _truncate(_one_line(metadata["summary"]), 60)
        else:
            if messages is None:
                try:
                    messages = load_messages(session_id)
                except Exception:
                    messages = []
            metadata["preview"] = _compute_preview_from_messages(messages)
        save_metadata(session_id, metadata)
    return metadata


def update_metadata_from_messages(session_id: str, messages: List[Message]) -> None:
    """Save session metadata in metadata.json, ensuring preview is updated based on messages."""
    try:
        metadata = ensure_metadata(session_id, messages=messages)
        metadata["preview"] = _compute_preview_from_messages(messages)
        save_metadata(session_id, metadata)
    except Exception as e:
        print(f"Failed to save metadata. Error: {e}")

# ==========================================
# CORE
# ==========================================

# SAVE MESSAGES
def save_message(
    messages: Sequence[Any],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create or update a session, returning success and session_id."""
    sessions_dir = get_sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)

    if session_id is None:
        session_id = uuid.uuid4().hex
    session_dir = sessions_dir / session_id
    if not session_dir.exists():
        session_dir.mkdir(parents=True, exist_ok=True)

    try:
        save_messages(session_id, messages)
        update_metadata_from_messages(session_id, messages)
        return {"success": True, "session_id": session_id, "error": ""}
    except Exception as e:
        print(f"Failed to save messages. Error: {e}")
        return {"success": False, "session_id": session_id, "error": str(e)}


# GET MESSAGES
def get_messages(session_id: str, limit: Optional[int] = 30) -> List[BaseMessage]:
    """Retrieve messages as LangChain message objects."""
    messages = messages_to_langchain(load_messages(session_id))
    if limit and limit > 0:
        return messages[-limit:]
    return messages


# DELETE SESSION
def delete_conversation(session_id: str) -> None:
    """Delete a session completely."""
    session_dir = get_sessions_dir() / session_id

    try:
        if not session_dir.exists():
            raise FileNotFoundError(f"Session '{session_id}' not found.")
        shutil.rmtree(session_dir)
        print(f"Session: {session_id} cleared successfully.")

        return {
            "success": True
        }
    except OSError as e:
        print("Session deletion failed. Please try again later...")

        return {
            "success": False,
            "error": f"Error: ${e}"
        }


# LIST CONVERSATIONS
def list_all_sessions() -> List[SessionMetadata]:
    """Return a list of session metadata objects for all sessions."""
    sessions_dir = get_sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)
    sessions = [session for session in sessions_dir.iterdir() if session.is_dir()]
    sessions.sort(key=lambda session: session.stat().st_mtime, reverse=True)

    results: List[SessionMetadata] = []
    for session in sessions:
        sid = session.name
        try:
            meta = ensure_metadata(sid)
        except Exception:
            meta = {"name": "", "preview": "", "summary": ""}
        results.append({
            "id": sid,
            "name": (meta.get("name") or "").strip(),
            "preview": (meta.get("preview") or "").strip(),
            "summary": (meta.get("summary") or "").strip(),
        })
    return results


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
    sessions = list_all_sessions()
    if width is None:
        width = shutil.get_terminal_size((120, 20)).columns

    lines: List[str] = []
    for session in sessions:
        sid = session.get("id") if isinstance(session, dict) else None
        heading = preview = ""
        try:
            name = (session.get("name") or "").strip() if isinstance(session, dict) else ""
            summary = (session.get("summary") or "").strip() if isinstance(session, dict) else ""
            preview = (session.get("preview") or "").strip() if isinstance(session, dict) else ""
            heading = name or summary
        except Exception:
            sid = sid or ""

        # Build block only if there is something to show
        block = f"\n   [[[{sid or ''}]]]"
        if heading:
            block += f"\n{_truncate('   ' + heading, width)}"
        if preview:
            block += f"\n{_truncate('   ' + preview, width)}"
        lines.append(block)

    return lines


# SET SESSION SUMMARY
def set_session_summary(session_id: str, summary: str) -> None:
    """Store a user-defined summary (e.g. generated by /compact)."""
    metadata = ensure_metadata(session_id)
    metadata["summary"] = summary.strip()
    save_metadata(session_id, metadata)
    new_message = [{
        "role": "system",
        "content": f"The following is a summary of the conversation so far:\n\n{summary}"
    }]
    save_messages(session_id, new_message)


# GET SESSION SUMMARY
def get_session_summary(session_id: str) -> str:
    """Retrieve the stored summary, or an empty string if none exists."""
    try:
        metadata = load_metadata(session_id)
        return (metadata.get("summary") or "").strip()
    except Exception:
        return ""