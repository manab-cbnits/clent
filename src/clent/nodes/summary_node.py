from ..lib.llm import _get_llm
from ..states import AgentState
from ..prompts import SUMMARY_PROMPT


def Summarize(state: AgentState):
    """Get the full response from the LLM as a string."""
    messages = [SUMMARY_PROMPT] + state["messages"][1:]
    
    llm = _get_llm(
        streaming=False,
        temperature=0.0,
        max_tokens=400
    )
    response = llm.invoke(messages)

    return response.content