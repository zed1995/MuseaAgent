from langchain_core.runnables import RunnableLambda

from backend.llm.chains.response_chain import ResponseReasonChain


class FakeChatModel:
    def with_structured_output(self, schema):
        return RunnableLambda(
            lambda _: schema(
                reason="These results best match the dark calm wallpaper request.",
            )
        )


def test_response_reason_chain_returns_reason_text() -> None:
    chain = ResponseReasonChain(FakeChatModel())

    result = chain.invoke(
        {
            "query": "深色安静壁纸",
            "mode": "wallpaper",
            "selected_spec_id": "balanced-1",
            "top_result_ids": ["photo-1", "photo-2"],
        }
    )

    assert "dark calm wallpaper" in result.reason
