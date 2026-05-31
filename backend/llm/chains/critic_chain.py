from backend.llm.prompts.critic_review import build_critic_review_prompt
from backend.llm.runtime.structured_output import invoke_structured_output
from backend.llm.schemas.critic import CriticAdviceSchema


class CriticAdviceChain:
    def __init__(self, chat_model) -> None:
        self._chat_model = chat_model
        self._prompt = build_critic_review_prompt()

    def invoke(self, payload: dict) -> CriticAdviceSchema:
        return invoke_structured_output(
            chat_model=self._chat_model,
            prompt=self._prompt,
            schema=CriticAdviceSchema,
            payload=payload,
        )
