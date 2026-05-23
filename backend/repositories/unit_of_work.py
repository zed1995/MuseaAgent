from contextlib import AbstractContextManager

from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.message_repository import MessageRepository
from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.repositories.search_log_repository import SearchLogRepository


class SqlAlchemyUnitOfWork(AbstractContextManager):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def __enter__(self):
        self.session = self._session_factory()
        self.photo_indexes = PhotoIndexRepository(self.session)
        self.conversations = ConversationRepository(self.session)
        self.messages = MessageRepository(self.session)
        self.search_logs = SearchLogRepository(self.session)
        return self

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            self.session.rollback()
        self.session.close()
