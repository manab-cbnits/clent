#Todoimport shutil
from pathlib import Path
from typing import List, Dict, TypedDict, Optional, Any
import shutil



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
    summary: str


# =============================================
# CORE
# =============================================

# DELETE SESSION
def delete_conversation(session_dir: str, session_id: str) -> None:
    """Delete a session completely."""

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