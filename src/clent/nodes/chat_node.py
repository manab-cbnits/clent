import asyncio
import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from clent.lib.conversation import ensure_metadata, save_message
from clent.lib.llm import _get_llm
from clent.mcp_servers.client import get_mcp_servers_config
from clent.prompts import SYSTEM_PROMPT
from clent.states import AgentState


# ── Helpers ───────────────────────────────────────────────────────────────────

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


async def _call_tool(tool, tool_call: dict) -> str:
    """Invoke a LangChain tool (async) and return its output as a string."""
    raw = await tool.ainvoke(tool_call["args"])
    if isinstance(raw, str):
        return raw
    # MCP tools return a list of content blocks, e.g. [{"type": "text", "text": "..."}]
    if isinstance(raw, list):
        texts = [
            block["text"] if isinstance(block, dict) and "text" in block
            else str(block)
            for block in raw
        ]
        return "\n".join(texts)
    try:
        return json.dumps(raw, indent=2, ensure_ascii=False)
    except Exception:
        return str(raw)


def _find_tool(tools: list, name: str):
    """Return the tool with the given name, or None."""
    return next((t for t in tools if t.name == name), None)


# ── Async core ────────────────────────────────────────────────────────────────

async def _chat_async(state: AgentState) -> dict:
    """
    The actual async implementation of the Chat node.

    Flow:
      1. Loads MCP tools and binds them to the LLM.
      2. Runs an agentic loop:
            LLM invoked → tool_calls present?
                YES → execute each tool, feed ToolMessages back, repeat
                NO  → stream the final text response to stdout
      3. Returns a state-update dict (human + assistant messages only).
    """
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
        # langchain-mcp-adapters ≥0.2: plain instantiation, not a context manager
        mcp_client = MultiServerMCPClient(get_mcp_servers_config())
        tools = await mcp_client.get_tools()
        llm = _get_llm(streaming=True).bind_tools(tools)

        # ── Agentic loop ──────────────────────────────────────────────────────
        while True:
            # Non-streaming invoke so we can inspect tool_calls cleanly
            response: AIMessage = await llm.ainvoke(messages)

            if not response.tool_calls:
                # ── Final text response — stream it ───────────────────────────
                streaming_llm = _get_llm(streaming=True).bind_tools(tools)
                async for chunk in streaming_llm.astream(messages):
                    text = _chunk_to_text(chunk)
                    if text:
                        print(text, end="", flush=True)
                        full_response += text
                print("")  # newline after streamed response
                assistant_message = AIMessage(content=full_response)
                messages.append(assistant_message)
                break

            # ── Tool call turn ────────────────────────────────────────────────
            messages.append(response)  # AIMessage with tool_calls

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool = _find_tool(tools, tool_name)

                print(f"\n[Tool call → {tool_name}]", flush=True)

                if tool is None:
                    tool_output = f"Error: tool '{tool_name}' not found."
                else:
                    try:
                        tool_output = await _call_tool(tool, tool_call)
                    except Exception as exc:  # noqa: BLE001
                        tool_output = f"Error executing tool '{tool_name}': {exc}"

                print(f"[Tool result ✓ {tool_name}]", flush=True)

                messages.append(
                    ToolMessage(
                        content=tool_output,
                        tool_call_id=tool_call["id"],
                    )
                )

    except Exception as e:
        print(f"\nError occurred while generating response: {e}")

    # ── Persist messages ───────────────────────────────────────────────────────
    # Store only the clean human + assistant pair (no intermediate tool msgs)
    if assistant_message is not None:
        updated_messages = [*state["messages"], human_message, assistant_message]
        save_result = save_message(
            messages=updated_messages,
            session_id=state["active_session_id"],
        )
    else:
        updated_messages = state["messages"]

    if not save_result["success"]:
        print(f"Error saving message: {save_result['error']}")

    # ── Build state update ─────────────────────────────────────────────────────
    state_update = {
        "user_input": "",
        "assistant_response": full_response,
        "active_session_id": save_result["session_id"],
        "messages": updated_messages if save_result["success"] and assistant_message is not None else [],
    }

    # If this turn created a brand-new session, add it to available_sessions
    new_session_id = save_result["session_id"]
    was_new_session = (
        state["active_session_id"] is None
        and new_session_id is not None
        and save_result["success"]
    )
    if was_new_session:
        meta = ensure_metadata(new_session_id)
        new_entry = {
            "id": new_session_id,
            "name": meta.get("name", ""),
            "preview": meta.get("preview", ""),
            "summary": meta.get("summary", ""),
        }
        available_sessions = list(state.get("available_sessions") or [])
        available_sessions.insert(0, new_entry)
        state_update["available_sessions"] = available_sessions

    return state_update


# ── Sync wrapper (LangGraph node) ─────────────────────────────────────────────

def Chat(state: AgentState) -> dict:
    """
    Synchronous LangGraph node. Bridges graph.invoke() (sync) with the
    async MCP client by running the async core in a fresh event loop.
    """
    return asyncio.run(_chat_async(state))