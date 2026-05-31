from langchain_core.runnables import RunnableLambda

from backend.llm.chains.intent_chain import IntentClassificationChain


class FakeChatModel:
    def with_structured_output(self, schema):
        return RunnableLambda(
            lambda _: schema(
                mode="photographer",
                topic_action="new",
            )
        )


def test_intent_chain_returns_mode_and_topic_action() -> None:
    chain = IntentClassificationChain(FakeChatModel())

    result = chain.invoke({"query": "找个摄影师风格", "conversation_history": []})

    assert result.mode == "photographer"
    assert result.topic_action in {"new", "refine", "reset"}
