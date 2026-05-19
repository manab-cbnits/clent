from pathlib import Path
from clent.lib.conversation import get_messages, list_all_sessions
from clent.graph import initialize_graph


SESSIONS_DIR = Path(__file__).parent / "sessions"


def main():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    available_sessions = list_all_sessions()

    state = {
        "session_dir": SESSIONS_DIR,

        "available_sessions": available_sessions,
        "active_session_id": None,
        "messages": [],
        
        "user_input": "",
        "assistant_reponse": "",
    }

    print("Welcome to clent...")


    graph = initialize_graph()
    graph.invoke(state)


if __name__ == "__main__":
    main()
