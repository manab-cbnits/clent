from clent.states import AgentState
from clent.prompts import RENAME_PROMPT, SUMMARY_PROMPT
from clent.lib.command_registry import commands
from clent.lib.llm import _get_llm
from clent.lib.session_handler import delete_conversation
from pathlib import Path
from clent.lib.conversation import get_messages, set_session_summary, save_metadata


def Command_Node(state: AgentState):
    raw_command = state["user_input"][1:].strip() if state["user_input"].lower().startswith("/") else state["user_input"].strip()

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
            # available_sessions is a list of metadata dicts; remove by id
            if any((s.get("id") == session_id) for s in available_sessions if isinstance(s, dict)):
                available_sessions = [s for s in available_sessions if not (isinstance(s, dict) and s.get("id") == session_id)]

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
            sessions = state.get("available_sessions") or []
            if not sessions:
                print("No available sessions.")
            else:
                lines = []
                for s in sessions:
                    if isinstance(s, dict):
                        lines.append(f"{s.get('id')} - {s.get('name') or s.get('preview') or ''}")
                    else:
                        lines.append(str(s))
                print("Available sessions:\n", "\n".join(lines))

        case "resume":
            sessions = state.get("available_sessions") or []
            if not sessions:
                print("No available sessions.")
                return

            lines = []
            for s in sessions:
                if isinstance(s, dict):
                    lines.append(f"{s.get('id')} - {s.get('name') or s.get('preview') or ''}")
                else:
                    lines.append(str(s))

            print("Select session to resume:\n" + "\n".join(lines) + "\n")

            sid = input("Enter session ID (or press Enter to cancel): ").strip()
            if not sid:
                print("Resume cancelled.")
                return

            if sid == state.get("active_session_id"):
                meta = state.get('available_sessions')["active_session_id"]
                print(f"Already in session: {meta['name'] or meta['preview'] or meta['id']}")
                return

            ids = [s.get("id") for s in sessions if isinstance(s, dict)]
            if sid not in ids:
                print(f"Session '{sid}' does not exist.")
                return

            try:
                hist = get_messages(sid)
            except Exception:
                hist = []

            print(f"Resumed session: {sid}\n")
            return {
                "active_session_id": sid,
                "messages": hist,
            }

        case "rename":
            if len(state.get("messages", [])) <= 1:
                print("No active conversation to rename.")
                return

            llm = _get_llm(temperature=0.0, max_tokens=20)
            response = llm.invoke(str([RENAME_PROMPT, *state.get("messages", [])]))
            new_name = (response.content or "").strip().capitalize()
            if not new_name:
                print("Session rename failed (empty name).")
                return
            else:
                print(f"Session renamed to: {new_name}")
                session_id = state.get("active_session_id")
                available_sessions = state.get("available_sessions") or []

                # Find the current session metadata in the available_sessions list
                current_meta = next(
                    (sess for sess in available_sessions if isinstance(sess, dict) and sess.get("id") == session_id),
                    None,
                )

                # Create an updated metadata dict (do not mutate the original in-place)
                if isinstance(current_meta, dict):
                    current_meta = {**current_meta, "name": new_name}
                else:
                    current_meta = {"name": new_name}

                # Persist metadata (only if we have a session id)
                if session_id:
                    save_metadata(session_id, metadata=current_meta)

                # Produce an updated list of available sessions with the new name
                updated_sessions = []
                for s in available_sessions:
                    if isinstance(s, dict) and s.get("id") == session_id:
                        updated_sessions.append({**s, "name": new_name})
                    else:
                        updated_sessions.append(s)

                return {
                    "active_session_id": session_id,
                    "available_sessions": updated_sessions,
                }

        case "compact":
            if len(state.get("messages", [])) <= 1:
                print("No conversation history selected to summarize.")
                return

            confirm = input("This will summarize the current conversation and remove detailed history. Continue? (y/n): ").strip().lower()
            print("")
            if confirm != "y":
                print("Session summarization cancelled.")
                return

            llm = _get_llm(temperature=0.2, max_tokens=400)
            summary_response = llm.invoke(str([SUMMARY_PROMPT, *state.get("messages", [])]))
            summary = (summary_response.content or "").strip()

            if not summary:
                print("Session summarization failed (empty summary).")
                return
            else:
                print(f"Session summary: {summary}")
                session_id = state.get("active_session_id")
                if session_id:
                    set_session_summary(session_id, summary)

                available_sessions = state.get("available_sessions") or []
                updated_sessions = []
                for session in available_sessions:
                    if isinstance(session, dict) and session.get("id") == session_id:
                        updated_sessions.append({**session, "summary": summary})
                    else:
                        updated_sessions.append(session)

                return {
                    "available_sessions": updated_sessions,
                }

        case "config":
            print("Launching configuration wizard on next cycle...")
            return {
                "run_setup": True,
                "user_input": "",
            }

