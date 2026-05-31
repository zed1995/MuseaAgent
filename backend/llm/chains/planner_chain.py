from backend.llm.prompts.search_planning import build_search_planning_prompt
from backend.llm.runtime.structured_output import invoke_structured_output
from backend.llm.schemas.planner import SearchPlannerSchema


class SearchPlannerChain:
    def __init__(self, chat_model) -> None:
        self._chat_model = chat_model
        self._prompt = build_search_planning_prompt()

    def invoke(self, payload: dict) -> SearchPlannerSchema:
        return invoke_structured_output(
            chat_model=self._chat_model,
            prompt=self._prompt,
            schema=SearchPlannerSchema,
            payload=payload,
        )
