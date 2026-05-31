from langchain_core.runnables import RunnableLambda

from backend.llm.chains.retrieval_rewrite_chain import RetrievalRewriteChain
from backend.services.retrieval_preparation.contracts import (
    HardFilters,
    NegativeConstraints,
    QueryUnderstandingResult,
    SoftPreferences,
)


class FakeChatModel:
    def with_structured_output(self, schema):
        return RunnableLambda(
            lambda _: schema(
                rewrite_for_embedding="dark calm oled wallpaper no people",
                rewrite_for_fts="dark calm oled wallpaper",
                lexical_terms=["dark", "calm", "oled", "wallpaper"],
                user_explicit_terms=["dark", "calm", "oled", "wallpaper"],
                expansion_terms=[],
                negative_terms=["people"],
                rewrite_notes=["stub structured output"],
            )
        )


def _understanding() -> QueryUnderstandingResult:
    return QueryUnderstandingResult(
        raw_query="我想找深色安静的 OLED 壁纸，不要人物",
        detected_language="zh",
        inferred_mode="wallpaper",
        hard_filters=HardFilters(orientation=None, has_human=False),
        negative_constraints=NegativeConstraints(exclude_people=True),
        soft_preferences=SoftPreferences(
            moods=["calm"],
            colors=["dark"],
            qualities=["oled"],
        ),
    )


def test_rewrite_chain_returns_structured_rewrite_result() -> None:
    chain = RetrievalRewriteChain(FakeChatModel())

    result = chain.invoke({"understanding": _understanding()})

    assert result.rewrite_for_embedding
    assert result.rewrite_for_fts
    assert result.negative_terms == ["people"]
