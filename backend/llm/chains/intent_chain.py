from backend.llm.prompts.intent_classification import build_intent_classification_prompt
from backend.llm.runtime.structured_output import invoke_structured_output
from backend.llm.schemas.intent import IntentClassificationSchema


class IntentClassificationChain:
    def __init__(self, chat_model) -> None:
        self._chat_model = chat_model
        self._prompt = build_intent_classification_prompt()

    def invoke(self, payload: dict) -> IntentClassificationSchema:
        return invoke_structured_output(
            chat_model=self._chat_model,
            prompt=self._prompt,
            schema=IntentClassificationSchema,
            payload=payload,
        )
