from langchain_core.prompts import ChatPromptTemplate


def build_search_planning_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Generate strict, balanced, and exploratory search specs for image retrieval.",
            ),
            (
                "human",
                "Mode: {mode}\nHard constraints: {hard_constraints}\nSoft preferences: {soft_preferences}",
            ),
        ]
    )
