from backend.agents.states import VisualSearchState


class IntentNode:
    def run(self, state: VisualSearchState) -> dict[str, object]:
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
