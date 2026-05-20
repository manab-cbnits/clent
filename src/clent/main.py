from clent.config import get_sessions_dir
from clent.lib.conversation import list_all_sessions
from clent.graph import initialize_graph


def main():
    sessions_dir = get_sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)
    available_sessions = list_all_sessions()

    state = {
        "session_dir": sessions_dir,

        "available_sessions": available_sessions,
        "active_session_id": None,
        "messages": [],

        "user_input": "",
        "assistant_reponse": "",

        "run_setup": False,
    }

    print("Welcome to clent...")


    graph = initialize_graph()
    graph.invoke(state)


if __name__ == "__main__":
    main()
