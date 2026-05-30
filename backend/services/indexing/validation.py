from datetime import UTC, datetime

from backend.repositories.write_models import PhotoIndexWriteModel


def build_completed_index_entry(*, context, entry_id: int) -> PhotoIndexWriteModel:
    if not context.text_artifacts.search_text:
        raise ValueError("search_text is required")
    if not context.semantic_artifacts.ai_caption:
        raise ValueError("ai_caption is required")
    if not context.representation_artifacts.retrieval_caption_text:
        raise ValueError("retrieval_caption_text is required")
    if not context.representation_artifacts.retrieval_tag_text:
        raise ValueError("retrieval_tag_text is required")
    if not context.representation_artifacts.retrieval_document_text:
        raise ValueError("retrieval_document_text is required")
    if not context.representation_artifacts.embedding_text:
        raise ValueError("embedding_text is required")
    if context.retrieval_artifacts.embedding is None:
        raise ValueError("embedding is required")

    return PhotoIndexWriteModel(
        id=entry_id,
        unsplash_photo_id=context.source.unsplash_photo_id,
        unsplash_user_id=context.source.unsplash_user_id,
        orientation=context.source.orientation,
        source_text=context.text_artifacts.source_text,
        search_text=context.text_artifacts.search_text,
        ai_caption=context.semantic_artifacts.ai_caption,
        ai_short_caption=context.semantic_artifacts.ai_short_caption or context.semantic_artifacts.ai_caption,
        retrieval_caption_text=context.representation_artifacts.retrieval_caption_text,
        retrieval_tag_text=context.representation_artifacts.retrieval_tag_text,
        retrieval_document_text=context.representation_artifacts.retrieval_document_text,
        embedding_text=context.representation_artifacts.embedding_text,
        scene_tags=context.semantic_artifacts.scene_tags,
        mood_tags=context.semantic_artifacts.mood_tags,
        style_tags=context.semantic_artifacts.style_tags,
        composition_tags=context.semantic_artifacts.composition_tags,
        lighting_tags=context.semantic_artifacts.lighting_tags,
        color_tags=context.semantic_artifacts.color_tags,
        subject_tags=context.semantic_artifacts.subject_tags,
        use_case_tags=context.semantic_artifacts.use_case_tags,
        dominant_colors=context.semantic_artifacts.dominant_colors,
        has_human=bool(context.semantic_artifacts.has_human),
        has_face=bool(context.semantic_artifacts.has_face),
        is_abstract=bool(context.semantic_artifacts.is_abstract),
        is_minimal=bool(context.semantic_artifacts.is_minimal),
        is_dark=bool(context.semantic_artifacts.is_dark),
        wallpaper_score=float(context.semantic_artifacts.wallpaper_score or 0.0),
        photography_reference_score=float(context.semantic_artifacts.photography_reference_score or 0.0),
        embedding=context.retrieval_artifacts.embedding,
        indexed_at=datetime.now(UTC),
    )
