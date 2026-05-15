"""LangChain tool wrapper for the chat functionality.
This tool mirrors the ``Chat`` function used in ``chat_node`` but is
exposed as a ``BaseTool`` to allow future graph nodes to invoke it via
LangChain's tool‑execution API.
"""

from langchain.tools import BaseTool
from ..core_1.chat import Chat


class ChatTool(BaseTool):
    name = "chat"
    description = "Generate a response from the LLM given the conversation messages."

    def _run(self, messages, temperature=0.0, max_tokens=None):
        # ``messages`` expected to be a list of dicts as used by Chat
        response = Chat(messages=messages, temperature=temperature, max_tokens=max_tokens)
        return response
