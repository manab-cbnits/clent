from clent.states import AgentState
from clent.nodes import Chat, Input_Node, Command_Node
from langgraph.graph import StateGraph, START, END



builder = StateGraph(AgentState)


# Conditional nodes
def route_after_input(state: AgentState) -> str:
    if state["user_input"].lower().startswith("/") or state["user_input"] == "?":
        return END if state["user_input"].lower() == "/bye" else "command"
    return "chat"

def route_after_command(state: AgentState) -> str:
    if state["action"] == "exit":
        return END
    return 
    # return "input"

# create nodes
builder.add_node("input", Input_Node)
builder.add_node("chat", Chat)
builder.add_node("command", Command_Node)

# create edges
builder.add_edge(START, "input")
builder.add_conditional_edges(
    "input",
    route_after_input,
    {
        "chat": "chat",
        "command": "command",
    }
)
builder.add_edge("chat", "input")
builder.add_edge("command", "input")

# compile the graph
clent_graph = builder.compile()


def initialize_graph():
    return clent_graph
