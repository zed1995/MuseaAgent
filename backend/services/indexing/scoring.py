from abc import ABC, abstractmethod

from backend.services.indexing.contracts import SemanticArtifacts


class Scorer(ABC):
    @abstractmethod
    def score(self, *, semantic_artifacts: SemanticArtifacts) -> SemanticArtifacts: ...


class StubScorer(Scorer):
    def score(self, *, semantic_artifacts: SemanticArtifacts) -> SemanticArtifacts:
        wall_score = 0.0
        photo_score = 0.0

        scene_tags = semantic_artifacts.scene_tags or []
        mood_tags = semantic_artifacts.mood_tags or []
        style_tags = semantic_artifacts.style_tags or []

        if "wallpaper" in scene_tags:
            wall_score += 0.3
        if "minimal" in style_tags:
            wall_score += 0.2
        if "calm" in mood_tags:
            wall_score += 0.1

        if "scenic" in scene_tags:
            photo_score += 0.3
        if "cinematic" in style_tags:
            photo_score += 0.2

        semantic_artifacts.wallpaper_score = min(round(wall_score + 0.5, 2), 1.0)
        semantic_artifacts.photography_reference_score = min(round(photo_score + 0.3, 2), 1.0)

        return semantic_artifacts


def build_scorer() -> Scorer:
    return StubScorer()
