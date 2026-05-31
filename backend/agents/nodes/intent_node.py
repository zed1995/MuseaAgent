from backend.agents.states import VisualSearchState


class IntentNode:
    def __init__(self, chain=None) -> None:
        self._chain = chain

    def run(self, state: VisualSearchState) -> dict[str, object]:
        if self._chain is not None:
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
