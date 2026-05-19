from langchain_core.messages import SystemMessage


SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are a helpful assistant. Answer the user's questions to the best of your ability."
        "If you don't know the answer, say you don't know."
    )
)