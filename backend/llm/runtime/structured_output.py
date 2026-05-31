from collections.abc import Mapping
from typing import TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def invoke_structured_output(
    *,
    chat_model: BaseChatModel,
    prompt: ChatPromptTemplate,
    schema: type[SchemaT],
    payload: Mapping[str, object],
) -> SchemaT:
    chain = prompt | chat_model.with_structured_output(schema)
    return chain.invoke(dict(payload))
