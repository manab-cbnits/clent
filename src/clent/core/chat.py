from langchain_openai import ChatOpenAI
from ..config import get_api_key, get_base_url, get_model_name, get_temperature, get_max_token


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


def ChatStream(messages):
    llm = ChatOpenAI(
        api_key=get_api_key(),
        model=get_model_name(),
        base_url=get_base_url(),
        temperature=get_temperature(),
        max_tokens=get_max_token(),
        streaming=True,
    )

    for chunk in llm.stream(messages):
        text = _chunk_to_text(chunk)
        if text:
            yield text
    

def Chat(messages, temperature=0.0, max_tokens=None):
    llm = ChatOpenAI(
        api_key=get_api_key(),
        model=get_model_name(),
        base_url=get_base_url(),
        temperature=temperature,
        max_tokens=max_tokens,
    )


    response = llm.invoke(str(messages))
    
    
    return response.content