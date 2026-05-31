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


class NullStringChatModel:
    def with_structured_output(self, schema):
        return RunnableLambda(
            lambda _: schema(
                raw_query="A cozy cafe interior with warm lighting and people reading.",
                detected_language="en",
                inferred_mode="generic",
                hard_filters={"orientation": "null", "has_human": "null"},
                negative_constraints={"exclude_people": False, "exclude_faces": False},
                soft_preferences={"lighting": ["warm"]},
                understanding_notes=["stub structured output"],
            )
        )


def test_understanding_chain_returns_structured_understanding_result() -> None:
    chain = RetrievalUnderstandingChain(FakeChatModel())

    result = chain.invoke({"query": "我想找深色安静的壁纸，不要人物", "mode": "wallpaper"})

    assert result.inferred_mode == "wallpaper"
    assert result.hard_filters.has_human is False


def test_understanding_chain_coerces_null_strings_in_hard_filters() -> None:
    chain = RetrievalUnderstandingChain(NullStringChatModel())

    result = chain.invoke(
        {
            "query": "A cozy cafe interior with warm lighting and people reading.",
            "mode": "auto",
        }
    )

    assert result.hard_filters.orientation is None
    assert result.hard_filters.has_human is None
