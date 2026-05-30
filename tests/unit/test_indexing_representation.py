from backend.services.indexing.representation import compose_retrieval_representation


def test_compose_retrieval_representation_builds_all_text_surfaces() -> None:
    result = compose_retrieval_representation(
        search_text="dark mountain wallpaper quiet minimal",
        ai_short_caption="Dark mountain wallpaper",
        ai_caption="A quiet dark mountain wallpaper with minimal composition.",
        scene_tags=["mountain"],
        mood_tags=["quiet"],
        style_tags=["minimal"],
        composition_tags=["negative space"],
        lighting_tags=["low light"],
        color_tags=["dark blue"],
        subject_tags=["mountain"],
        use_case_tags=["wallpaper"],
    )

    assert result.retrieval_caption_text.startswith("Dark mountain wallpaper")
    assert "quiet" in result.retrieval_tag_text
    assert "negative space" in result.retrieval_document_text
    assert result.embedding_text == result.retrieval_document_text
