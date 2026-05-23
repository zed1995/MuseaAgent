from sqlalchemy import select

from backend.models.search_log import SearchLogOrmModel
from backend.repositories.records import SearchLogRecord
from backend.repositories.write_models import SearchLogWriteModel


class SearchLogRepository:
    def __init__(self, session) -> None:
        self._session = session

    def create(self, entry: SearchLogWriteModel) -> SearchLogRecord:
        row = SearchLogOrmModel(
            id=entry.id,
            request_id=entry.request_id,
            user_id=entry.user_id,
            query=entry.query,
        )
        self._session.add(row)
        self._session.flush()
        return self._to_record(row)

    def get_by_request_id(self, request_id: str) -> SearchLogRecord | None:
        stmt = select(SearchLogOrmModel).where(
            SearchLogOrmModel.request_id == request_id
        )
        row = self._session.scalar(stmt)
        if row is None:
            return None
        return self._to_record(row)

    @staticmethod
    def _to_record(row: SearchLogOrmModel) -> SearchLogRecord:
        return SearchLogRecord(
            id=row.id,
            request_id=row.request_id,
            user_id=row.user_id,
            query=row.query,
            intent=row.intent,
            rewritten_queries=row.rewritten_queries,
            filters=row.filters,
            retrieved_photo_ids=row.retrieved_photo_ids,
            reranked_photo_ids=row.reranked_photo_ids,
            latency_ms=row.latency_ms,
            result_count=row.result_count,
            created_at=row.created_at,
        )
