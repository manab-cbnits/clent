from clent.states import AgentState


def Input_Node(state: AgentState) -> dict:
    """Get user input and return it as a HumanMessage for the state."""
    confirmed = 2
    while True:
        try:
            user_input = input("\n➤  ").strip()
            confirmed = 2
            if user_input:
                break
        except KeyboardInterrupt:
            confirmed -= 1
            if confirmed <= 0:
                print("Ready to help whenever needed...\n")
                exit(0)
            print("Press Ctrl+C again to exit.")

    return {
        "user_input": user_input
    }