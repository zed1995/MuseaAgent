from langchain_core.prompts import ChatPromptTemplate


def build_intent_classification_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Classify the user's image-search intent and topic action.",
            ),
            (
                "human",
                "Query: {query}\nConversation history: {conversation_history}",
            ),
        ]
    )
