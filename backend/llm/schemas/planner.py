from pydantic import BaseModel, Field

from backend.agents.contracts import SearchSpec


class SearchPlannerSchema(BaseModel):
    search_specs: list[SearchSpec] = Field(default_factory=list)
