from langchain_core.runnables import RunnableLambda

from backend.llm.chains.planner_chain import SearchPlannerChain


class FakeChatModel:
    def with_structured_output(self, schema):
        return RunnableLambda(
            lambda _: schema(
                search_specs=[
                    {
                        "spec_id": "strict-1",
                        "query_text": "dark calm oled wallpaper no people",
                        "query_mode": "strict",
                        "filters": {"has_human": False},
                        "limit": 20,
                    },
                    {
                        "spec_id": "balanced-1",
                        "query_text": "dark calm wallpaper no people",
                        "query_mode": "balanced",
                        "filters": {"has_human": False},
                        "limit": 20,
                    },
                    {
                        "spec_id": "exploratory-1",
                        "query_text": "dark moody wallpaper no people",
                        "query_mode": "exploratory",
                        "filters": {"has_human": False},
                        "limit": 20,
                    },
                ]
            )
        )


def test_planner_chain_returns_three_structured_search_specs() -> None:
    chain = SearchPlannerChain(FakeChatModel())

    result = chain.invoke(
        {
            "mode": "wallpaper",
            "hard_constraints": {"has_human": False},
            "soft_preferences": {"moods": ["calm"], "colors": ["dark"], "qualities": ["oled"]},
        }
    )

    assert [spec.query_mode for spec in result.search_specs] == ["strict", "balanced", "exploratory"]
