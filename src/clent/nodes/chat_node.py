# chat_node.py
import asyncio
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from clent.lib.conversation import ensure_metadata, save_message
from clent.lib.llm import _get_llm
from clent.lib.shell_env import get_shell_environment_hint
from clent.lib.ui import (
    console,
    print_info,
    print_success,
    print_error,
    status as rich_status,
)
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


# ── Module-level cache for tools ──────────────────────────────────────────
_tools_cache = None
_llm_cache = None


def _find_tool(tools: list, name: str):
    """Return the tool with the given name, or None."""
    return next((t for t in tools if t.name == name), None)


async def _get_cached_tools():
    """Get tools from cache, or load and cache them if not available."""
    global _tools_cache

    if _tools_cache is not None:
        return _tools_cache

    with rich_status("Initializing tools..."):
        mcp_client = MultiServerMCPClient(get_mcp_servers_config())
        tools = await mcp_client.get_tools()

        # Sanitize tool names for strict LLMs (e.g. Llama 3 via Groq)
        for t in tools:
            t.name = t.name.replace("-", "_")

    print_success(f"Loaded {len(tools)} tools")
    _tools_cache = tools
    return tools


async def _chat_async(state: AgentState) -> dict:
    """
    Async implementation of the Chat node.

    - Loads MCP tools and binds them to a **single streaming LLM**.
    - Runs an agentic loop: stream → check for tool_calls → execute tools → repeat.
    - Persists only the final human + assistant message pair.
    """
    human_message = HumanMessage(content=state["user_input"])

    env_hint = state.get("shell_environment_hint") or get_shell_environment_hint()
    system_message = SystemMessage(content=f"{SYSTEM_PROMPT.content}\n\n{env_hint}")
    messages = [system_message] + state["messages"] + [human_message]

    full_response = ""
    save_result = {
        "success": False,
        "session_id": state["active_session_id"],
        "error": "",
    }
    assistant_message = None

    try:
        # Get cached tools (loads only on first call)
        tools = await _get_cached_tools()

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
                    console.print()  # blank line before response
                    print_info("Thinking...")
                    accumulated = None
                    full_response = ""
                    # Stream the response, printing tokens as they arrive
                    async for chunk in streaming_llm.astream(messages):
                        text = _chunk_to_text(chunk)
                        if text:
                            print(text, end="", flush=True)
                            full_response += text
                        accumulated = (
                            chunk if accumulated is None else accumulated + chunk
                        )
                    print()  # newline after streaming
                    break  # success – exit retry loop
                except Exception as e:
                    err_msg = str(e)
                    print_error(f"LLM Error: {err_msg}")
                    if retries < max_retries:
                        retries += 1
                        print_info(f"Retrying ({retries}/{max_retries})...")
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
                        print_error("Max retries reached. Aborting this turn.")
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

                console.print(
                    f"[yellow]-->[/yellow] Calling [bold]{tool_name}[/bold]..."
                )

                if tool is None:
                    tool_output = f"Error: tool '{tool_name}' not found."
                    print_error(f"Tool '{tool_name}' not found")
                else:
                    try:
                        with rich_status(f"Executing {tool_name}..."):
                            tool_output = await _call_tool(tool, tool_call)
                        print_success(f"{tool_name} completed")
                    except Exception as exc:
                        tool_output = f"Error executing tool '{tool_name}': {exc}"
                        print_error(f"Failed to execute {tool_name}: {exc}")

                messages.append(
                    ToolMessage(
                        content=tool_output,
                        tool_call_id=tool_call["id"],
                    )
                )

    except Exception as e:
        print_error(f"Error occurred while generating response: {e}")

    # ── Persist messages ───────────────────────────────────────────────────────
    if assistant_message is not None:
        with rich_status("Saving conversation..."):
            updated_messages = [*state["messages"], human_message, assistant_message]
            save_result = save_message(
                messages=updated_messages,
                session_id=state["active_session_id"],
            )
    else:
        updated_messages = state["messages"]

    if not save_result["success"]:
        print_error(f"Error saving message: {save_result['error']}")

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
