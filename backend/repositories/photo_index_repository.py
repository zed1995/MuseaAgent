from datetime import datetime

from sqlalchemy import select, text, update

from backend.models.photo_index import PhotoIndexOrmModel, VECTOR_DIMENSION
from backend.repositories.records import PhotoIndexRecord
from backend.repositories.write_models import PhotoIndexWriteModel


class PhotoIndexRepository:
    def __init__(self, session) -> None:
        self._session = session

    def get_by_id(self, id: int) -> PhotoIndexRecord | None:
        row = self._session.get(PhotoIndexOrmModel, id)
        if row is None:
            return None
        return self._to_record(row)

    def get_by_unsplash_photo_id(self, unsplash_photo_id: str) -> PhotoIndexRecord | None:
        stmt = select(PhotoIndexOrmModel).where(
            PhotoIndexOrmModel.unsplash_photo_id == unsplash_photo_id
        )
        row = self._session.scalar(stmt)
        if row is None:
            return None
        return self._to_record(row)

    def upsert_index_entry(self, entry: PhotoIndexWriteModel) -> None:
        stmt = select(PhotoIndexOrmModel).where(
            PhotoIndexOrmModel.unsplash_photo_id == entry.unsplash_photo_id
        )
        existing = self._session.scalar(stmt)

        if existing is not None:
            existing.unsplash_user_id = entry.unsplash_user_id
            existing.orientation = entry.orientation
            existing.source_text = entry.source_text
            existing.search_text = entry.search_text
            existing.ai_caption = entry.ai_caption
            existing.ai_short_caption = entry.ai_short_caption
            existing.scene_tags = entry.scene_tags or []
            existing.mood_tags = entry.mood_tags or []
            existing.style_tags = entry.style_tags or []
            existing.composition_tags = entry.composition_tags or []
            existing.lighting_tags = entry.lighting_tags or []
            existing.color_tags = entry.color_tags or []
            existing.subject_tags = entry.subject_tags or []
            existing.use_case_tags = entry.use_case_tags or []
            existing.dominant_colors = entry.dominant_colors or []
            existing.has_human = entry.has_human
            existing.has_face = entry.has_face
            existing.is_abstract = entry.is_abstract
            existing.is_minimal = entry.is_minimal
            existing.is_dark = entry.is_dark
            existing.wallpaper_score = entry.wallpaper_score
            existing.photography_reference_score = entry.photography_reference_score
            existing.embedding = entry.embedding
            existing.index_status = "indexed"
            existing.indexed_at = entry.indexed_at
        else:
            row = PhotoIndexOrmModel(
                id=entry.id,
                source="unsplash",
                unsplash_photo_id=entry.unsplash_photo_id,
                unsplash_user_id=entry.unsplash_user_id,
                orientation=entry.orientation,
                source_text=entry.source_text,
                search_text=entry.search_text,
                embedding=entry.embedding,
                index_status="indexed",
                ai_caption=entry.ai_caption,
                ai_short_caption=entry.ai_short_caption,
                scene_tags=entry.scene_tags or [],
                mood_tags=entry.mood_tags or [],
                style_tags=entry.style_tags or [],
                composition_tags=entry.composition_tags or [],
                lighting_tags=entry.lighting_tags or [],
                color_tags=entry.color_tags or [],
                subject_tags=entry.subject_tags or [],
                use_case_tags=entry.use_case_tags or [],
                dominant_colors=entry.dominant_colors or [],
                has_human=entry.has_human,
                has_face=entry.has_face,
                is_abstract=entry.is_abstract,
                is_minimal=entry.is_minimal,
                is_dark=entry.is_dark,
                wallpaper_score=entry.wallpaper_score,
                photography_reference_score=entry.photography_reference_score,
                indexed_at=entry.indexed_at,
            )
            self._session.add(row)

    def bulk_upsert_index_entries(self, entries: list[PhotoIndexWriteModel]) -> None:
        for entry in entries:
            self.upsert_index_entry(entry)

    def commit(self) -> None:
        self._session.commit()

    def mark_indexed(self, id: int, indexed_at: datetime) -> None:
        stmt = (
            update(PhotoIndexOrmModel)
            .where(PhotoIndexOrmModel.id == id)
            .values(index_status="indexed", indexed_at=indexed_at)
        )
        self._session.execute(stmt)

    @staticmethod
    def _to_record(row: PhotoIndexOrmModel) -> PhotoIndexRecord:
        return PhotoIndexRecord(
            id=row.id,
            source=row.source,
            unsplash_photo_id=row.unsplash_photo_id,
            unsplash_user_id=row.unsplash_user_id,
            orientation=row.orientation,
            source_text=row.source_text,
            search_text=row.search_text,
            index_status=row.index_status,
            ai_caption=row.ai_caption,
            ai_short_caption=row.ai_short_caption,
            scene_tags=row.scene_tags,
            mood_tags=row.mood_tags,
            style_tags=row.style_tags,
            composition_tags=row.composition_tags,
            lighting_tags=row.lighting_tags,
            color_tags=row.color_tags,
            subject_tags=row.subject_tags,
            use_case_tags=row.use_case_tags,
            dominant_colors=row.dominant_colors,
            has_human=row.has_human,
            has_face=row.has_face,
            is_abstract=row.is_abstract,
            is_minimal=row.is_minimal,
            is_dark=row.is_dark,
            wallpaper_score=row.wallpaper_score,
            photography_reference_score=row.photography_reference_score,
            embedding=row.embedding,
            indexed_at=row.indexed_at,
        )
