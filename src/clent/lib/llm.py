from clent.config import get_api_key, get_base_url, get_model_name
from langchain_openai import ChatOpenAI


def _get_llm(streaming=False, temperature=0.0, max_tokens=None):
    """Lazy-initialise the LLM so env vars are read at call time, not import time."""
    return ChatOpenAI(
        api_key=get_api_key(),
        model=get_model_name(),
        base_url=get_base_url(),
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
    )
