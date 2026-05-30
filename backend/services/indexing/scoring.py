from abc import ABC, abstractmethod

from backend.services.indexing.contracts import SemanticArtifacts


class Scorer(ABC):
    @abstractmethod
    def score(self, *, semantic_artifacts: SemanticArtifacts) -> SemanticArtifacts: ...


class StubScorer(Scorer):
    def score(self, *, semantic_artifacts: SemanticArtifacts) -> SemanticArtifacts:
        wall_score = _clamp_score(semantic_artifacts.wallpaper_score)
        photo_score = _clamp_score(semantic_artifacts.photography_reference_score)

        if semantic_artifacts.has_human:
            wall_score -= 0.1
        if semantic_artifacts.is_minimal:
            wall_score += 0.05

        composition_tags = semantic_artifacts.composition_tags or []
        lighting_tags = semantic_artifacts.lighting_tags or []
        if composition_tags:
            photo_score += 0.05
        if lighting_tags:
            photo_score += 0.03

        semantic_artifacts.wallpaper_score = _clamp_score(wall_score)
        semantic_artifacts.photography_reference_score = _clamp_score(photo_score)

        return semantic_artifacts


def _clamp_score(value: float | None) -> float:
    if value is None:
        return 0.0
    return round(min(max(float(value), 0.0), 1.0), 2)


def build_scorer() -> Scorer:
    return StubScorer()
