from backend.llm.prompts.retrieval_rewrite import build_retrieval_rewrite_prompt
from backend.llm.runtime.structured_output import invoke_structured_output
from backend.llm.schemas.retrieval_rewrite import RetrievalRewriteSchema


class RetrievalRewriteChain:
    def __init__(self, chat_model) -> None:
        self._chat_model = chat_model
        self._prompt = build_retrieval_rewrite_prompt()

    def invoke(self, payload: dict) -> RetrievalRewriteSchema:
        understanding = payload["understanding"]
        return invoke_structured_output(
            chat_model=self._chat_model,
            prompt=self._prompt,
            schema=RetrievalRewriteSchema,
            payload={"understanding_json": understanding.model_dump_json()},
        )
