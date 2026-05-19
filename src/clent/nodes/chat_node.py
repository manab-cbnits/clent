from clent.states import AgentState
from clent.lib.llm import _get_llm
from clent.prompts import SYSTEM_PROMPT
from clent.lib.conversation import save_message
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
    save_result = {
        "success": False,
        "session_id": state["active_session_id"],
        "error": "",
    }
    assistant_message = None
    try:
        for chunk in llm.stream(messages):
            text = _chunk_to_text(chunk)
            if text:
                print(text, end="", flush=True)
                full_response += text

        print("")

        assistant_message = AIMessage(content=full_response)
        updated_messages = [*state["messages"], human_message, assistant_message]
        save_result = save_message(
            messages=updated_messages,
            session_id=state["active_session_id"],
        )

    except Exception as e:
        print(f"Error occurred while generating response: {e}")

    if not save_result["success"]:
        print(f"Error saving message: {save_result['error']}")


    return {
        "user_input": "",
        "assistant_response": full_response,
        "active_session_id": save_result["session_id"],
        "messages": updated_messages if save_result["success"] and assistant_message is not None else [],
    }