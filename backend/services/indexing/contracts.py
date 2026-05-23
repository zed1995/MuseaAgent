from dataclasses import dataclass, field


@dataclass(slots=True)
class NormalizedSourcePhoto:
    unsplash_photo_id: str
    unsplash_user_id: str | None
    raw_title: str | None
    raw_description: str | None
    raw_alt_description: str | None
    orientation: str | None
    width: int | None
    height: int | None
    regular_url: str


@dataclass(slots=True)
class TextArtifacts:
    source_text: str | None = None
    analysis_text: str | None = None
    search_text: str | None = None


@dataclass(slots=True)
class SemanticArtifacts:
    ai_caption: str | None = None
    ai_short_caption: str | None = None
    scene_tags: list[str] = field(default_factory=list)
    mood_tags: list[str] = field(default_factory=list)
    style_tags: list[str] = field(default_factory=list)
    composition_tags: list[str] = field(default_factory=list)
    lighting_tags: list[str] = field(default_factory=list)
    color_tags: list[str] = field(default_factory=list)
    subject_tags: list[str] = field(default_factory=list)
    use_case_tags: list[str] = field(default_factory=list)
    dominant_colors: list[str] = field(default_factory=list)
    has_human: bool | None = None
    has_face: bool | None = None
    is_abstract: bool | None = None
    is_minimal: bool | None = None
    is_dark: bool | None = None
    wallpaper_score: float | None = None
    photography_reference_score: float | None = None


@dataclass(slots=True)
class RetrievalArtifacts:
    embedding: list[float] | None = None


@dataclass(slots=True)
class EnrichmentContext:
    source: NormalizedSourcePhoto
    text_artifacts: TextArtifacts = field(default_factory=TextArtifacts)
    semantic_artifacts: SemanticArtifacts = field(default_factory=SemanticArtifacts)
    retrieval_artifacts: RetrievalArtifacts = field(default_factory=RetrievalArtifacts)
