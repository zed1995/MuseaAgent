from langchain_core.prompts import ChatPromptTemplate


def build_response_reason_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", "Write a short user-facing reason for why the selected search results match the request."),
            (
                "human",
                "Query: {query}\nMode: {mode}\nSelected spec: {selected_spec_id}\nTop result ids: {top_result_ids}",
            ),
        ]
    )
