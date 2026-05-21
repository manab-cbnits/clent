from typing import List, Optional, TypedDict

from langchain_core.messages import BaseMessage


class SessionMetadata(TypedDict, total=False):
    id: str
    name: str
    preview: str
    summary: str


class AgentState(TypedDict, total=False):
    session_dir: str

    available_sessions: List[SessionMetadata]
    active_session_id: Optional[str]
    messages: List[BaseMessage]

    user_input: Optional[str]
    assistant_reponse: Optional[str]

    run_setup: Optional[bool]  # set to True to trigger the setup wizard on next cycle

    # LLM-facing hint to generate correct shell commands for this runtime.
    shell_environment_hint: Optional[str]
