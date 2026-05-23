import pytest

from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.message_repository import MessageRepository
from backend.repositories.write_models import ConversationWriteModel, MessageWriteModel


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_conversation_and_message_round_trip(session) -> None:
    conv_repo = ConversationRepository(session)
    msg_repo = MessageRepository(session)

    conv = conv_repo.create(
        ConversationWriteModel(id=5001, user_id="user_1", title="Test conversation")
    )
    session.commit()

    assert conv.id == 5001
    assert conv.title == "Test conversation"

    msg1 = msg_repo.create(
        MessageWriteModel(id=6001, conv_id=5001, role="user", content="Hello")
    )
    msg2 = msg_repo.create(
        MessageWriteModel(id=6002, conv_id=5001, role="assistant", content="Hi there")
    )
    session.commit()

    assert msg1.id == 6001
    assert msg2.id == 6002

    messages = msg_repo.list_by_conv_id(5001)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
