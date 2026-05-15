from clent.states import AgentState
from clent.lib.llm import _get_llm
from clent.prompts import SYSTEM_PROMPT
from clent.lib.save_messages import save_message
from langchain_core.messages import HumanMessage, AIMessage


def _chunk_to_text(chunk) -> str:
    if chunk is None:
        return ""

    # LangChain message chunks (preferred)
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content

    # OpenAI ChatCompletionChunk passthrough (fallback)
    try:
        return chunk.choices[0].delta.content or ""
    except Exception:
        return ""


def Chat(state: AgentState):
    llm = _get_llm(streaming=True)

    human_message = HumanMessage(content=state["user_input"])

    messages = [SYSTEM_PROMPT] + state["messages"] + [human_message]
    
    full_response = ""
    try:
        for chunk in llm.stream(messages):
            text = _chunk_to_text(chunk)
            if text:
                print(text, end="", flush=True)
                full_response += text
        
        print("")
        save_result = save_message(user_input=state["user_input"], ai_message=full_response)

    except Exception as e:
        print(f"Error occurred while generating response: {e}")

    if not save_result["success"]:
        print(f"Error saving message: {save_result['error']}")


    return {
        "user_input": "",
        "assistant_reponse": "",
        "messages":  state["messages"] + [human_message, AIMessage(content=full_response)]
    }