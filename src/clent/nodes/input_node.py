from clent.states import AgentState
from clent.lib.ui import console


def Input_Node(state: AgentState) -> dict:
    """Get user input and return it as a HumanMessage for the state."""

    confirmed = 2
    while True:
        try:
            user_input = console.input("[bold cyan]>>> [/bold cyan]").strip()
            confirmed = 2
            if user_input:
                console.print("[dim cyan]*[/dim cyan] ", end="")
                break
        except KeyboardInterrupt:
            confirmed -= 1
            if confirmed <= 0:
                console.print("[yellow]Ready to help whenever needed...[/yellow]")
                exit(0)
            console.print("[yellow]Press Ctrl+C again to exit.[/yellow]")

    return {"user_input": user_input}
