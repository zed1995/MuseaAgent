from backend.services.retrieval_preparation.contracts import QueryUnderstandingResult
from backend.services.retrieval_preparation.understanding import QueryUnderstandingService


def test_query_understanding_result_supports_hard_filters_soft_preferences_and_notes() -> None:
    result = QueryUnderstandingResult(
        raw_query="我想找深色安静的 OLED 壁纸，不要人物",
        detected_language="zh",
        inferred_mode="wallpaper",
        hard_filters={"orientation": None, "has_human": False},
        negative_constraints={"exclude_people": True, "exclude_faces": False},
        soft_preferences={"moods": ["calm"], "styles": ["minimal"], "colors": ["dark"], "qualities": ["oled"]},
        understanding_notes=["wallpaper use case inferred"],
    )

    assert result.hard_filters.has_human is False
    assert result.soft_preferences.colors == ["dark"]


def test_understanding_extracts_no_people_without_forcing_portrait_wallpaper() -> None:
    service = QueryUnderstandingService(
        model_client=lambda query, mode: {
            "raw_query": query,
            "detected_language": "zh",
            "inferred_mode": "wallpaper",
            "hard_filters": {"orientation": None, "has_human": False},
            "negative_constraints": {"exclude_people": True, "exclude_faces": False},
            "soft_preferences": {"moods": ["calm"], "styles": ["minimal"], "colors": ["dark"], "qualities": ["oled"]},
            "understanding_notes": ["exclude-people constraint extracted"],
        }
    )
    result = service.understand("我想找深色安静的 OLED 壁纸，不要人物", "wallpaper")

    assert result.hard_filters.orientation is None
    assert result.hard_filters.has_human is False
    assert result.negative_constraints.exclude_people is True


def test_understanding_infers_portrait_only_for_mobile_wallpaper_terms() -> None:
    service = QueryUnderstandingService(
        model_client=lambda query, mode: {
            "raw_query": query,
            "detected_language": "zh",
            "inferred_mode": "wallpaper",
            "hard_filters": {"orientation": "portrait", "has_human": None},
            "negative_constraints": {"exclude_people": False, "exclude_faces": False},
            "soft_preferences": {"styles": ["minimal"], "scenes": ["mountain"]},
            "understanding_notes": ["orientation inferred: portrait"],
        }
    )
    result = service.understand("手机壁纸 极简山景", "wallpaper")

    assert result.hard_filters.orientation == "portrait"


def test_understanding_preserves_soft_preferences_in_structured_fields() -> None:
    service = QueryUnderstandingService(
        model_client=lambda query, mode: {
            "raw_query": query,
            "detected_language": "zh",
            "inferred_mode": "reference",
            "hard_filters": {"orientation": None, "has_human": None},
            "negative_constraints": {"exclude_people": False, "exclude_faces": False},
            "soft_preferences": {"styles": ["cinematic"], "scenes": ["city", "night"]},
            "scene_candidates": ["city", "night"],
            "style_candidates": ["cinematic"],
            "understanding_notes": ["reference use case inferred"],
        }
    )
    result = service.understand("找一点电影感的城市夜景参考图", "reference")

    assert "cinematic" in result.soft_preferences.styles
    assert "city" in result.soft_preferences.scenes
    assert "night" in result.soft_preferences.scenes


def test_understanding_falls_back_to_deterministic_parsing_when_model_client_is_missing() -> None:
    service = QueryUnderstandingService()
    result = service.understand("我想找深色安静的壁纸，不要人物", "auto")

    assert result.inferred_mode == "wallpaper"
    assert result.hard_filters.has_human is False
    assert "understanding fallback used" in result.understanding_notes


def test_understanding_logs_invalid_json_payload(caplog) -> None:
    service = QueryUnderstandingService(model_client=lambda query, mode: "not json")

    try:
        service.understand("test", "auto")
    except Exception:
        pass
    else:
        raise AssertionError("invalid model json should fail")

    assert "invalid json" in caplog.text.lower()


def test_understanding_accepts_json_wrapped_in_markdown_fence() -> None:
    service = QueryUnderstandingService(
        model_client=lambda query, mode: """```json
{
  "raw_query": "test",
  "detected_language": "en",
  "inferred_mode": "generic",
  "hard_filters": {"orientation": null, "has_human": null},
  "negative_constraints": {"exclude_people": false, "exclude_faces": false},
  "soft_preferences": {
    "moods": [],
    "styles": [],
    "scenes": [],
    "subjects": [],
    "lighting": [],
    "colors": ["monochrome"],
    "qualities": []
  },
  "subject_candidates": ["trees"],
  "scene_candidates": ["forest"],
  "style_candidates": [],
  "mood_candidates": [],
  "color_candidates": ["monochrome"],
  "understanding_notes": ["parsed from fenced json"]
}
```"""
    )

    result = service.understand("test", "auto")

    assert result.detected_language == "en"
    assert result.color_candidates == ["monochrome"]


def test_understanding_result_coerces_string_notes_to_list() -> None:
    result = QueryUnderstandingResult(
        raw_query="test",
        detected_language="en",
        inferred_mode="generic",
        understanding_notes="single note string",
    )

    assert result.understanding_notes == ["single note string"]
