# chat_node.py
import asyncio
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from clent.lib.conversation import ensure_metadata, save_message
from clent.lib.llm import _get_llm
from clent.lib.shell_env import get_shell_environment_hint
from clent.mcp_servers.client import get_mcp_servers_config
from clent.prompts import SYSTEM_PROMPT
from clent.states import AgentState


# ── Helpers ───────────────────────────────────────────────────────────────────

def _chunk_to_text(chunk) -> str:
    """Extract text content from a streaming chunk."""
    if chunk is None:
        return ""
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    # Fallback for OpenAI ChatCompletionChunk passthrough
    try:
        return chunk.choices[0].delta.content or ""
    except Exception:
        return ""


async def _call_tool(tool, tool_call: dict) -> str:
    """Invoke a LangChain tool asynchronously and return its output as a string."""
    raw = await tool.ainvoke(tool_call["args"])
    if isinstance(raw, str):
        return raw
    # MCP tools often return a list of content blocks, e.g. [{"type": "text", "text": "..."}]
    if isinstance(raw, list):
        texts = [
            block["text"] if isinstance(block, dict) and "text" in block else str(block)
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
    Async implementation of the Chat node.

    - Loads MCP tools and binds them to a **single streaming LLM**.
    - Runs an agentic loop: stream → check for tool_calls → execute tools → repeat.
    - Persists only the final human + assistant message pair.
    """
    human_message = HumanMessage(content=state["user_input"])

    env_hint = state.get("shell_environment_hint") or get_shell_environment_hint()
    system_message = SystemMessage(
        content=f"{SYSTEM_PROMPT.content}\n\n{env_hint}"
    )
    messages = [system_message] + state["messages"] + [human_message]

    full_response = ""
    save_result = {
        "success": False,
        "session_id": state["active_session_id"],
        "error": "",
    }
    assistant_message = None

    try:
        # Obtain MCP tools
        mcp_client = MultiServerMCPClient(get_mcp_servers_config())
        tools = await mcp_client.get_tools()

        # Sanitize tool names for strict LLMs (e.g. Llama 3 via Groq)
        for t in tools:
            t.name = t.name.replace("-", "_")

        # Single streaming LLM, used for every invocation
        streaming_llm = _get_llm(streaming=True).bind_tools(tools)

        # ── Agentic loop ──────────────────────────────────────────────────────
        while True:
            retries = 0
            max_retries = 3
            abort_turn = False
            original_messages = messages.copy()  # snapshot for retries

            # Inner retry loop for LLM errors
            while True:
                try:
                    accumulated = None
                    full_response = ""
                    # Stream the response, printing tokens as they arrive
                    async for chunk in streaming_llm.astream(messages):
                        text = _chunk_to_text(chunk)
                        if text:
                            print(text, end="", flush=True)
                            full_response += text
                        accumulated = chunk if accumulated is None else accumulated + chunk
                    break  # success – exit retry loop
                except Exception as e:
                    err_msg = str(e)
                    print(f"\n[LLM Error] {err_msg}", flush=True)
                    if retries < max_retries:
                        retries += 1
                        print(f"Retrying ({retries}/{max_retries})...", flush=True)
                        # Reset messages to state before the failed call, then add error hint
                        messages = original_messages.copy()
                        messages.append(
                            HumanMessage(
                                content=f"API Error: {err_msg}. Please correct your tool call and try again."
                            )
                        )
                        await asyncio.sleep(2)
                        continue
                    else:
                        print("Max retries reached. Aborting this turn.", flush=True)
                        abort_turn = True
                        break

            if abort_turn:
                break  # exit outer agentic loop

            # Convert accumulated chunks to a full AIMessage
            response = AIMessage(
                content=accumulated.content,
                tool_calls=accumulated.tool_calls,
                additional_kwargs=accumulated.additional_kwargs,
                response_metadata=accumulated.response_metadata,
                id=accumulated.id,
            )

            # No tool calls → this is the final answer
            if not response.tool_calls:
                print("")  # newline after streaming
                assistant_message = response
                messages.append(assistant_message)
                break

            # ── Tool call turn ────────────────────────────────────────────────
            messages.append(response)  # AIMessage with tool_calls

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool = _find_tool(tools, tool_name)

                print(
                    f"\n[Tool call → {tool_name}] args: {tool_call.get('args', {})}",
                    flush=True,
                )

                if tool is None:
                    tool_output = f"Error: tool '{tool_name}' not found."
                else:
                    try:
                        tool_output = await _call_tool(tool, tool_call)
                    except Exception as exc:
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
        "shell_environment_hint": env_hint,
        "messages": (
            updated_messages
            if save_result["success"] and assistant_message is not None
            else []
        ),
    }

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
    """Synchronous LangGraph node. Bridges sync graph with async MCP operations."""
    return asyncio.run(_chat_async(state))
