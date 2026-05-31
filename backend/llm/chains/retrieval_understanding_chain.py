from backend.llm.prompts.retrieval_understanding import build_retrieval_understanding_prompt
from backend.llm.runtime.structured_output import invoke_structured_output
from backend.llm.schemas.retrieval_understanding import QueryUnderstandingSchema


class RetrievalUnderstandingChain:
    def __init__(self, chat_model) -> None:
        self._chat_model = chat_model
        self._prompt = build_retrieval_understanding_prompt()

    def invoke(self, payload: dict) -> QueryUnderstandingSchema:
        return invoke_structured_output(
            chat_model=self._chat_model,
            prompt=self._prompt,
            schema=QueryUnderstandingSchema,
            payload=payload,
        )
