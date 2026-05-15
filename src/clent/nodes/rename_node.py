from clent.lib.llm import _get_llm
from clent.states import AgentState
from langchain import messages


def Rename(state: AgentState, temperature=0.0, max_tokens=None):
    """Get the full response from the LLM as a string."""
    llm = _get_llm(
        streaming=False,
        temperature=temperature,
        max_tokens=max_tokens
    )
    response = llm.invoke(str(messages))

    return response.content