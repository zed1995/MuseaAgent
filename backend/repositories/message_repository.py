from sqlalchemy import select

from backend.models.message import MessageOrmModel
from backend.repositories.records import MessageRecord
from backend.repositories.write_models import MessageWriteModel


class MessageRepository:
    def __init__(self, session) -> None:
        self._session = session

    def create(self, entry: MessageWriteModel) -> MessageRecord:
        row = MessageOrmModel(
            id=entry.id,
            conv_id=entry.conv_id,
            role=entry.role,
            content=entry.content,
            structured_data=entry.structured_data,
            metadata_=entry.metadata,
        )
        self._session.add(row)
        self._session.flush()
        return self._to_record(row)

    def list_by_conv_id(self, conv_id: int) -> list[MessageRecord]:
        stmt = (
            select(MessageOrmModel)
            .where(MessageOrmModel.conv_id == conv_id)
            .order_by(MessageOrmModel.created_at)
        )
        rows = self._session.scalars(stmt).all()
        return [self._to_record(row) for row in rows]

    @staticmethod
    def _to_record(row: MessageOrmModel) -> MessageRecord:
        return MessageRecord(
            id=row.id,
            conv_id=row.conv_id,
            role=row.role,
            content=row.content,
            structured_data=row.structured_data,
            metadata=row.metadata_,
            created_at=row.created_at,
        )
