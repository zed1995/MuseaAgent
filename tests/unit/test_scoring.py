from backend.services.indexing.contracts import SemanticArtifacts
from backend.services.indexing.scoring import StubScorer


def test_scorer_normalizes_model_scores_without_replacing_them() -> None:
    scorer = StubScorer()
    artifacts = SemanticArtifacts(
        wallpaper_score=1.4,
        photography_reference_score=-0.2,
    )

    result = scorer.score(semantic_artifacts=artifacts)

    assert result.wallpaper_score == 1.0
    assert result.photography_reference_score == 0.0


def test_scorer_applies_light_adjustments_to_model_scores() -> None:
    scorer = StubScorer()
    artifacts = SemanticArtifacts(
        wallpaper_score=0.6,
        photography_reference_score=0.5,
        has_human=True,
        is_minimal=True,
        composition_tags=["wide"],
        lighting_tags=["dramatic"],
    )

    result = scorer.score(semantic_artifacts=artifacts)

    assert result.wallpaper_score == 0.55
    assert result.photography_reference_score == 0.58
