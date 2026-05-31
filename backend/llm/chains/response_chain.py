from backend.llm.prompts.response_reason import build_response_reason_prompt
from backend.llm.runtime.structured_output import invoke_structured_output
from backend.llm.schemas.response import ResponseReasonSchema


class ResponseReasonChain:
    def __init__(self, chat_model) -> None:
        self._chat_model = chat_model
        self._prompt = build_response_reason_prompt()

    def invoke(self, payload: dict) -> ResponseReasonSchema:
        return invoke_structured_output(
            chat_model=self._chat_model,
            prompt=self._prompt,
            schema=ResponseReasonSchema,
            payload=payload,
        )
