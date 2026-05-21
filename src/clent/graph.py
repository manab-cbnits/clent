from clent.states import AgentState
from clent.nodes import Chat, Input_Node, Command_Node, Setup_Node
from langgraph.graph import StateGraph, START, END



builder = StateGraph(AgentState)


# Conditional nodes
def route_after_input(state: AgentState) -> str:
    if state["user_input"].lower().startswith("/") or state["user_input"].strip() == "?":
        if state.get("user_input").lower() == "/bye":
            print("See you again whenever needed..")
            return END
        else:
            return "command"
        
    return "chat"


# create nodes
builder.add_node("setup", Setup_Node)
builder.add_node("input", Input_Node)
builder.add_node("chat", Chat)
builder.add_node("command", Command_Node)

# create edges
builder.add_edge(START, "setup")          # ← setup is first
builder.add_edge("setup", "input")        # ← then input as normal
builder.add_conditional_edges(
    "input",
    route_after_input,
    {
        "chat": "chat",
        "command": "command",
        END: END,
    }
)
builder.add_edge("chat", "setup")         # ← loop back through setup (pass-through when configured)
builder.add_edge("command", "setup")      # ← ensures /config re-triggers the wizard

# compile the graph
clent_graph = builder.compile()


def initialize_graph():
    return clent_graph