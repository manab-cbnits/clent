from ..lib.separator import separator
from .commands import commands
from .chat import Chat, ChatStream
from ..prompts import SYSTEM_PROMPT, SUMMARY_PROMPT, RENAME_PROMPT
from .conversation import get_messages, save_message, delete_conversation, list_session, list_all_sessions, set_session_name, set_session_summary


def app():
    global CURRENT_SESSION_ID
    CURRENT_SESSION_ID = None
    global messages
    messages = [SYSTEM_PROMPT]

    if CURRENT_SESSION_ID:
        messages.extend(get_messages(CURRENT_SESSION_ID))

    separator()
    try:
        while True:
            user_input = input("\n➤  ")

            if not user_input:
                continue

            # command mode
            if user_input.startswith("/") or user_input == "?":
                result = commands(user_input[1:]) if user_input.startswith("/") else commands("?")

                if result["message"]:
                    print(result["message"])

                match result["action"]:
                    case "exit":
                        break

                    case "new_chat":
                        CURRENT_SESSION_ID = None
                        messages = [SYSTEM_PROMPT]
                        print("Started a new chat session.")

                    case "sessions":
                        lines = list_session()
                        if not lines:
                            print("No available sessions.")
                        else:
                            print("Available sessions:\n", "\n".join(lines))

                    case "resume":
                        lines = list_session()
                        if not lines:
                            print("No available sessions.")
                            continue

                        print("Select session to resume:\n" + "\n".join(lines) + "\n")

                        sid = input("Enter session ID (or press Enter to cancel): ").strip()
                        if not sid:
                            print("Resume cancelled.")
                            continue

                        if sid == CURRENT_SESSION_ID:
                            print(f"Already in session: {CURRENT_SESSION_ID}")
                            continue

                        sessions = list_all_sessions()
                        if sid not in sessions:
                            print(f"Session '{sid}' does not exist.")
                            continue

                        # load the session
                        CURRENT_SESSION_ID = sid
                        messages = [SYSTEM_PROMPT] + get_messages(CURRENT_SESSION_ID)
                        print(f"Resumed session: {sid}\n")
                        separator()
                        continue

                    case "rename":
                        if len(messages) <= 1:
                            print("No conversation history to analyze for renaming.")
                            continue

                        response = Chat(
                            messages=[RENAME_PROMPT] + messages[1:],
                            temperature=0.0,
                            # max_tokens=20
                        )
                        new_name = response.strip().capitalize()
                        if not new_name:
                            print("Session rename cancelled (empty name).")
                            continue
                        else:
                            if not CURRENT_SESSION_ID:
                                print("No active session to rename.")
                                continue

                            set_session_name(CURRENT_SESSION_ID, new_name)
                            print(f"Session renamed to: {new_name}")

                    case "compact":
                        if len(messages) <= 1:
                            print("No conversation history to analyze for summarization.")
                            continue

                        confirm = input("This will summarize the current conversation and remove detailed history. Continue? (y/n): ").strip().lower()
                        print("")
                        if confirm != "y":
                            print("Session summarization cancelled.")
                            continue

                        summary = Chat(
                            messages=[SUMMARY_PROMPT] + messages[1:],
                            temperature=0.2,
                            max_tokens=400
                        ).strip()

                        if not summary:
                            print("Session summarization failed (empty summary).")
                            continue
                        else:
                            set_session_summary(CURRENT_SESSION_ID, summary)
                            print(f"Session summarized: {summary}")

                    case "clear":
                        if not CURRENT_SESSION_ID:
                            print("No active session to clear.")
                            continue

                        confirm = input("This will delete the current session and all its messages. Continue? (y/n): ").strip().lower()
                        if confirm != "y":
                            print("Session deletion cancelled.")
                            continue
                        print("")

                        delete_conversation(CURRENT_SESSION_ID)
                        CURRENT_SESSION_ID = None
                        messages = [SYSTEM_PROMPT]

                print("")
                separator()
                continue

            # llm mode
            print("✤  ", end="", flush=True)
            try:
                messages.append({"role": "user", "content": user_input})

                full_response = ""
                for text in ChatStream(messages):
                    print(text, end="", flush=True)
                    full_response += text

                messages.append({"role": "assistant", "content": full_response.strip()})
                msg_res = save_message(messages=messages[1:], session_id=CURRENT_SESSION_ID)

                if not CURRENT_SESSION_ID and msg_res["success"] and msg_res["session_id"]:
                    CURRENT_SESSION_ID = msg_res["session_id"]

            except Exception as exc:
                print(f"\n\nError: {exc}\n", end="")
                break
            finally:
                print("\n")
                separator()

    # 'ctrl + c' exception
    except KeyboardInterrupt:
        print("\n\nExiting...\n")


if __name__ == "__main__":
    app()
