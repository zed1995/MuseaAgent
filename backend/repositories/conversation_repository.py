from sqlalchemy import select

from backend.models.conversation import ConversationOrmModel
from backend.repositories.records import ConversationRecord
from backend.repositories.write_models import ConversationWriteModel


class ConversationRepository:
    def __init__(self, session) -> None:
        self._session = session

    def create(self, entry: ConversationWriteModel) -> ConversationRecord:
        row = ConversationOrmModel(
            id=entry.id,
            user_id=entry.user_id,
            title=entry.title,
        )
        self._session.add(row)
        self._session.flush()
        return self._to_record(row)

    def get_by_id(self, id: int) -> ConversationRecord | None:
        row = self._session.get(ConversationOrmModel, id)
        if row is None:
            return None
        return self._to_record(row)

    @staticmethod
    def _to_record(row: ConversationOrmModel) -> ConversationRecord:
        return ConversationRecord(
            id=row.id,
            user_id=row.user_id,
            title=row.title,
            message_count=row.message_count,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
