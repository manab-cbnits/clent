import operator
from langchain_core.messages import BaseMessage
from typing import List, TypedDict, Optional, Annotated


class SessionMetadata(TypedDict):
    name: str
    preview: str
    summary: str


class AgentState(TypedDict):
    available_sessions: List[str]
    active_session_id: Optional[str] = None
    messages: Annotated[List[BaseMessage], operator.add]
    metadata: Optional[SessionMetadata] = None

    user_input: str | None
    assistant_reponse: str | None