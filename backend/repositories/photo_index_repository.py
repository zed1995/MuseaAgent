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
            existing.embedding = entry.embedding
            existing.status = entry.status
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
                status=entry.status,
            )
            self._session.add(row)

    def bulk_upsert_index_entries(self, entries: list[PhotoIndexWriteModel]) -> None:
        for entry in entries:
            self.upsert_index_entry(entry)

    def mark_indexed(self, id: int, indexed_at: datetime) -> None:
        stmt = (
            update(PhotoIndexOrmModel)
            .where(PhotoIndexOrmModel.id == id)
            .values(status="indexed", indexed_at=indexed_at)
        )
        self._session.execute(stmt)

    def mark_failed(self, id: int, error_message: str) -> None:
        stmt = (
            update(PhotoIndexOrmModel)
            .where(PhotoIndexOrmModel.id == id)
            .values(status="failed", last_error=error_message)
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
            status=row.status,
            last_error=row.last_error,
            indexed_at=row.indexed_at,
        )
