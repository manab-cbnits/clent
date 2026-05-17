from clent.states import AgentState
from clent.prompts import SYSTEM_PROMPT, RENAME_PROMPT, SUMMARY_PROMPT
from clent.lib.command_registry import commands
from clent.lib.llm import _get_llm
from clent.lib.session_handler import delete_conversation
from pathlib import Path


def Command_Node(state: AgentState):
    raw_command = state["user_input"][1:].strip()

    result = commands(raw_command)

    if result["message"] and result.get("action") != "clear":
        print(result["message"])

    match result["action"]:
        case "new_chat":
            print("Started a new chat session.")
            return {
                "active_session_id": None,
                "messages": [],
                "metadata": None,
                "user_input": None,
                "assistant_reponse": None,
            }

        case "clear":
            if not state["active_session_id"]:
                print("No active session to clear.")
                return state

            confirm = input("This will delete the current session and all its messages. Continue? (y/n): ").strip().lower()
            if confirm in ("n", ""):
                print("Session deletion cancelled.")
                return state

            if confirm not in ("y", "yes"):
                print("Bad input. Deletion cancelled...")
                return state

            session_id = state["active_session_id"]

            base_dir = Path(state.get("session_dir") or "")
            if str(base_dir) in ("", "."):
                from clent.lib.session_handler import SESSIONS_DIR
                base_dir = SESSIONS_DIR

            session_dir = base_dir if base_dir.name == session_id else (base_dir / session_id)

            res = delete_conversation(session_dir=session_dir, session_id=session_id)
            if not res.get("success"):
                print(res.get("error") or "Session deletion failed. Please try again later...")
                return state

            available_sessions = state.get("available_sessions") or []
            if session_id in available_sessions:
                available_sessions = [sid for sid in available_sessions if sid != session_id]

            if result.get("message"):
                print(result["message"])

            return {
                "available_sessions": available_sessions,
                "active_session_id": None,
                "messages": [],
                "metadata": None,
                "user_input": None,
                "assistant_reponse": None,
            }
             

        case "sessions":
            sessions = state["available_sessions"] | []
            if not sessions:
                print("No available sessions.")
            else:
                print("Available sessions:\n", "\n".join(sessions))

        case "resume":
            sessions = state["available_sessions"] | []
            if not sessions:
                print("No available sessions.")
                return

            print("Select session to resume:\n" + "\n".join(sessions) + "\n")

            sid = input("Enter session ID (or press Enter to cancel): ").strip()
            if not sid:
                print("Resume cancelled.")
                return

            if sid == state["active_session_id"]:
                print(f"Already in session: {state['active_session_id']}")
                

            sessions = state["available_sessions"] | []
            if sid not in sessions:
                print(f"Session '{sid}' does not exist.")
                return

            messages = [SYSTEM_PROMPT] 
            # + get_messages(sid)   # TODO: load messages for the session
            print(f"Resumed session: {sid}\n")
            return

        case "rename":
            if len(messages) <= 1:
                print("No conversation history to analyze for renaming.")
                return

            response = _get_llm(
                messages=[RENAME_PROMPT] + messages[1:],
                temperature=0.0,
                max_tokens=20
            )
            new_name = response.strip().capitalize()
            if not new_name:
                print("Session rename cancelled (empty name).")
                return
            else:
                if not state["active_session_id"]:
                    print("No active session to rename.")
                    return

                print(f"Session renamed to: {new_name}")
                return {
                    "active_session_id": state["active_session_id"]
                }

        case "compact":
            if len(messages) <= 1:
                print("No conversation history to analyze for summarization.")
                return

            confirm = input("This will summarize the current conversation and remove detailed history. Continue? (y/n): ").strip().lower()
            print("")
            if confirm != "y":
                print("Session summarization cancelled.")
                return

            summary = _get_llm(
                messages=[SUMMARY_PROMPT] + messages[1:],
                temperature=0.2,
                max_tokens=400
            ).strip()

            if not summary:
                print("Session summarization failed (empty summary).")
                return
            else:
                print(f"Session summarized: {summary}")
                state['metadata']['summary'] = summary
                return state
            
