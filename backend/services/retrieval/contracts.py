from typing import Literal

from pydantic import BaseModel, Field


class RetrievalFilters(BaseModel):
    orientation: Literal["portrait", "landscape", "squarish"] | None = None
    has_human: bool | None = None


class RetrievalRequest(BaseModel):
    query: str
    mode: Literal["wallpaper", "reference", "auto"] = "auto"
    limit: int = 20
    filters: RetrievalFilters = Field(default_factory=RetrievalFilters)
    debug: bool = False
