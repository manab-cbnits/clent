from clent.states import AgentState
from clent.nodes import Chat, Input_Node
from langgraph.graph import StateGraph, START, END



builder = StateGraph(AgentState)


# Conditional nodes
def route_after_input(state: AgentState) -> str:
    if state["user_input"].strip().lower() == "/bye":
        return "end"
    return "chat"


# create nodes
builder.add_node("input", Input_Node)
builder.add_node("chat", Chat)

# create edges
builder.add_edge(START, "input")
builder.add_conditional_edges(
    "input",
    route_after_input,
    {
        "chat": "chat",
        "end": END
    }
)
builder.add_edge("chat", "input")

# compile the graph
clent_graph = builder.compile()


def initialize_graph():
    return clent_graph
