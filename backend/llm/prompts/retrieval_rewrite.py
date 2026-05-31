from langchain_core.prompts import ChatPromptTemplate


def build_retrieval_rewrite_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a retrieval-rewrite model. Return structured rewrite output for embedding and FTS.",
            ),
            (
                "human",
                "Understanding payload:\n{understanding_json}",
            ),
        ]
    )
