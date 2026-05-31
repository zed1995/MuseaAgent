from langchain_core.prompts import ChatPromptTemplate


def build_critic_review_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", "Summarize the critic decision for the current search results."),
            ("human", "Rule result: {rule_result}\nRetry count: {retry_count}"),
        ]
    )
