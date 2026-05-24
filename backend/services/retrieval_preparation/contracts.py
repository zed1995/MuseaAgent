from typing import Literal

from pydantic import BaseModel, Field, field_validator


class HardFilters(BaseModel):
    orientation: Literal["portrait", "landscape", "squarish"] | None = None
    has_human: bool | None = None


class NegativeConstraints(BaseModel):
    exclude_people: bool = False
    exclude_faces: bool = False


class SoftPreferences(BaseModel):
    moods: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    lighting: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    qualities: list[str] = Field(default_factory=list)


class QueryUnderstandingResult(BaseModel):
    raw_query: str
    detected_language: Literal["zh", "en", "mixed", "unknown"]
    inferred_mode: Literal["wallpaper", "reference", "generic"]

    hard_filters: HardFilters = Field(default_factory=HardFilters)
    negative_constraints: NegativeConstraints = Field(default_factory=NegativeConstraints)
    soft_preferences: SoftPreferences = Field(default_factory=SoftPreferences)

    subject_candidates: list[str] = Field(default_factory=list)
    scene_candidates: list[str] = Field(default_factory=list)
    style_candidates: list[str] = Field(default_factory=list)
    mood_candidates: list[str] = Field(default_factory=list)
    color_candidates: list[str] = Field(default_factory=list)

    understanding_notes: list[str] = Field(default_factory=list)

    @field_validator(
        "subject_candidates",
        "scene_candidates",
        "style_candidates",
        "mood_candidates",
        "color_candidates",
        "understanding_notes",
        mode="before",
    )
    @classmethod
    def _coerce_single_string_to_list(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        return value


class RetrievalRewriteResult(BaseModel):
    rewrite_for_embedding: str = Field(min_length=1)
    # Must stay lexical and explicit-only: user-explicit terms plus negatives/hard filters.
    rewrite_for_fts: str = Field(min_length=1)
    lexical_terms: list[str] = Field(default_factory=list)
    user_explicit_terms: list[str] = Field(default_factory=list)
    expansion_terms: list[str] = Field(default_factory=list)
    negative_terms: list[str] = Field(default_factory=list)
    rewrite_notes: list[str] = Field(default_factory=list)

    @field_validator(
        "lexical_terms",
        "user_explicit_terms",
        "expansion_terms",
        "negative_terms",
        "rewrite_notes",
        mode="before",
    )
    @classmethod
    def _coerce_single_string_to_list(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        return value

    @field_validator("rewrite_for_embedding", "rewrite_for_fts")
    @classmethod
    def _reject_blank_rewrites(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("rewrite must not be blank")
        return value


class PreparedRetrievalRequest(BaseModel):
    understanding: QueryUnderstandingResult
    rewrite: RetrievalRewriteResult
