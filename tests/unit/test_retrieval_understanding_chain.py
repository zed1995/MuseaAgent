from langchain_core.runnables import RunnableLambda

from backend.llm.chains.retrieval_understanding_chain import RetrievalUnderstandingChain


class FakeChatModel:
    def with_structured_output(self, schema):
        return RunnableLambda(
            lambda _: schema(
                raw_query="我想找深色安静的壁纸，不要人物",
                detected_language="zh",
                inferred_mode="wallpaper",
                hard_filters={"orientation": None, "has_human": False},
                negative_constraints={"exclude_people": True, "exclude_faces": False},
                soft_preferences={"moods": ["calm"], "colors": ["dark"], "qualities": ["oled"]},
                understanding_notes=["stub structured output"],
            )
        )


def test_understanding_chain_returns_structured_understanding_result() -> None:
    chain = RetrievalUnderstandingChain(FakeChatModel())

    result = chain.invoke({"query": "我想找深色安静的壁纸，不要人物", "mode": "wallpaper"})

    assert result.inferred_mode == "wallpaper"
    assert result.hard_filters.has_human is False
