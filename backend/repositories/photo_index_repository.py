from datetime import datetime

from sqlalchemy import func, literal_column, select, text, update
from sqlalchemy.engine import Row

from backend.models.photo_index import PhotoIndexOrmModel
from backend.repositories.records import PhotoIndexRecord, PhotoRetrievalCandidate
from backend.repositories.write_models import PhotoIndexWriteModel


def _build_weighted_tsvector(model) -> object:
    # PostgreSQL `setweight` expects the weight as a SQL "char" literal. If we
    # bind "A"/"B"/"C" as VARCHAR parameters, Postgres raises UndefinedFunction.
    return (
        func.setweight(
            func.to_tsvector("english", func.coalesce(model.search_text, "")),
            literal_column("'A'"),
        ).op("||")(
            func.setweight(
                func.to_tsvector(
                    "english",
                    func.coalesce(model.retrieval_caption_text, ""),
                ),
                literal_column("'A'"),
            )
        ).op("||")(
            func.setweight(
                func.to_tsvector(
                    "english",
                    func.coalesce(model.retrieval_tag_text, ""),
                ),
                literal_column("'B'"),
            )
        ).op("||")(
            func.setweight(
                func.to_tsvector(
                    "english",
                    func.coalesce(model.retrieval_document_text, ""),
                ),
                literal_column("'C'"),
            )
        )
    )


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
            existing.retrieval_caption_text = entry.retrieval_caption_text
            existing.retrieval_tag_text = entry.retrieval_tag_text
            existing.retrieval_document_text = entry.retrieval_document_text
            existing.embedding_text = entry.embedding_text
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
                retrieval_caption_text=entry.retrieval_caption_text,
                retrieval_tag_text=entry.retrieval_tag_text,
                retrieval_document_text=entry.retrieval_document_text,
                embedding_text=entry.embedding_text,
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

    def search_vector(
        self,
        query_embedding: list[float],
        orientation: str | None,
        has_human: bool | None,
        limit: int,
    ) -> list[PhotoRetrievalCandidate]:
        stmt = (
            select(
                PhotoIndexOrmModel,
                (1 - PhotoIndexOrmModel.embedding.cosine_distance(query_embedding)).label(
                    "vector_score"
                ),
            )
            .where(PhotoIndexOrmModel.index_status == "indexed")
            .where(PhotoIndexOrmModel.embedding.isnot(None))
        )

        if orientation is not None:
            stmt = stmt.where(PhotoIndexOrmModel.orientation == orientation)

        if has_human is not None:
            stmt = stmt.where(PhotoIndexOrmModel.has_human == has_human)

        stmt = stmt.order_by(
            PhotoIndexOrmModel.embedding.cosine_distance(query_embedding)
        ).limit(limit)

        rows = self._session.execute(stmt)
        return [self._to_retrieval_candidate(row) for row in rows]

    def search_full_text(
        self,
        query_text: str,
        orientation: str | None,
        has_human: bool | None,
        limit: int,
    ) -> list[PhotoRetrievalCandidate]:
        """Full-text search using OR-based term matching.

        Splits query into meaningful terms and builds
        ``websearch_to_tsquery('term1 OR term2 OR …')`` so that
        documents matching *any* term are candidates.  ``ts_rank``
        then gives higher scores to documents matching more terms,
        achieving both recall and meaningful ranking.
        """
        terms = [t for t in query_text.strip().split() if len(t) > 2]
        if not terms:
            return []

        tsvector = _build_weighted_tsvector(PhotoIndexOrmModel)
        tsquery = func.websearch_to_tsquery("english", " OR ".join(terms))

        rank_expr = func.ts_rank(tsvector, tsquery, 32)  # 32 = normalize by doc length

        stmt = (
            select(PhotoIndexOrmModel, rank_expr.label("fts_score"))
            .where(PhotoIndexOrmModel.index_status == "indexed")
            .where(tsquery.isnot(None))
            .where(tsvector.op("@@")(tsquery))
            .order_by(rank_expr.desc())
            .limit(limit)
        )

        if orientation is not None:
            stmt = stmt.where(PhotoIndexOrmModel.orientation == orientation)

        if has_human is not None:
            stmt = stmt.where(PhotoIndexOrmModel.has_human == has_human)

        rows = self._session.execute(stmt)
        return [self._to_retrieval_candidate(row) for row in rows]

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
            retrieval_caption_text=row.retrieval_caption_text,
            retrieval_tag_text=row.retrieval_tag_text,
            retrieval_document_text=row.retrieval_document_text,
            embedding_text=row.embedding_text,
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

    @staticmethod
    def _to_retrieval_candidate(row: Row[tuple[PhotoIndexOrmModel, float]]) -> PhotoRetrievalCandidate:
        orm = row[0]
        return PhotoRetrievalCandidate(
            id=orm.id,
            unsplash_photo_id=orm.unsplash_photo_id,
            unsplash_user_id=orm.unsplash_user_id,
            orientation=orm.orientation,
            search_text=orm.search_text,
            ai_caption=orm.ai_caption,
            retrieval_caption_text=orm.retrieval_caption_text,
            retrieval_tag_text=orm.retrieval_tag_text,
            has_human=orm.has_human,
            has_face=orm.has_face,
            is_dark=orm.is_dark,
            is_minimal=orm.is_minimal,
            wallpaper_score=orm.wallpaper_score,
            photography_reference_score=orm.photography_reference_score,
            dominant_colors=orm.dominant_colors,
            scene_tags=orm.scene_tags,
            style_tags=orm.style_tags,
            color_tags=orm.color_tags,
            subject_tags=orm.subject_tags,
            use_case_tags=orm.use_case_tags,
            vector_score=getattr(row, "vector_score", 0.0),
            fts_score=getattr(row, "fts_score", 0.0),
        )
