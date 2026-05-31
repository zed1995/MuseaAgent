from backend.agents.states import VisualSearchState


class IntentNode:
    def __init__(self, chain=None) -> None:
        self._chain = chain

    def run(self, state: VisualSearchState) -> dict[str, object]:
        if self._chain is not None:
            # Intent classification is the first graph decision point: it sets
            # the retrieval use-case before any constraints or search specs are
            # derived downstream.
            result = self._chain.invoke(
                {
                    "query": state["original_query"],
                    "conversation_history": state["conversation_history"],
                }
            )
            return {
                "mode": result.mode,
                "topic_action": result.topic_action,
            }

        query = state["original_query"]

        # The rule-based fallback keeps the workflow bootable without a model
        # while still separating obvious query types into different modes.
        if "摄影师" in query:
            mode = "photographer"
        elif "参考" in query:
            mode = "reference"
        elif "壁纸" in query:
            mode = "wallpaper"
        else:
            mode = "auto"

        return {
            "mode": mode,
            "topic_action": "new",
        }
