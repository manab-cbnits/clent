from clent.graph import initialize_graph


def main():
    print("Welcome to clent...")

    state = {
        "available_sessions": [],
        "active_session_id": None,
        "messages": [],
        "metadata": None,
        "user_input": "",
    }

    graph = initialize_graph()
    graph.invoke(state)


if __name__ == "__main__":
    main()
