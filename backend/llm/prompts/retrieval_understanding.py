from langchain_core.prompts import ChatPromptTemplate


def build_retrieval_understanding_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a retrieval-understanding model. Return a structured understanding for image search.",
            ),
            (
                "human",
                "Query: {query}\nMode hint: {mode}\nReturn structured understanding fields in English.",
            ),
        ]
    )
