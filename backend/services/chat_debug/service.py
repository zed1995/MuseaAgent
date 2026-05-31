from __future__ import annotations

import logging
from time import perf_counter

from datetime import UTC, datetime
from sqlalchemy import select

from backend.agents.factory import build_agent_workflow
from backend.core.id_generator import IdGenerator
from backend.models.conversation import ConversationOrmModel
from backend.repositories.records import MessageRecord
from backend.repositories.write_models import MessageWriteModel
from backend.services.retrieval.factory import build_retrieval_service
from backend.services.retrieval_preparation.factory import build_retrieval_preparation_service

logger = logging.getLogger(__name__)


def _format_timing_log(operation: str, elapsed_ms: float, **fields) -> str:
    field_text = " ".join(f"{key}={value}" for key, value in fields.items())
    suffix = f" {field_text}" if field_text else ""
    return f"[debug-chat] {operation} took {elapsed_ms:.1f}ms{suffix}"


class DebugChatService:
    def __init__(self, *, session_factory, settings) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._id_generator = IdGenerator(machine_id=1)

    def list_conversations(self) -> list[dict]:
        # The debug sidebar only needs a lightweight conversation summary, so
        # this query stays intentionally shallow and ordered by recent activity.
        total_started = perf_counter()
        acquire_started = perf_counter()
        with self._session_factory() as session:
            acquire_connection_ms = (perf_counter() - acquire_started) * 1000
            query_started = perf_counter()
            rows = session.scalars(
                select(ConversationOrmModel).order_by(ConversationOrmModel.updated_at.desc())
            ).all()
            result = [self._serialize_conversation_row(row) for row in rows]
            query_ms = (perf_counter() - query_started) * 1000
            total_ms = (perf_counter() - total_started) * 1000
            logger.info(
                _format_timing_log(
                    "list_conversations",
                    total_ms,
                    acquire_connection_ms=f"{acquire_connection_ms:.1f}",
                    query_ms=f"{query_ms:.1f}",
                    count=len(result),
                )
            )
            return result

    def create_conversation(self, *, title: str | None, user_id: str | None) -> dict:
        started = perf_counter()
        with self._session_factory() as session:
            entry_id = self._id_generator.next_id()
            row = ConversationOrmModel(id=entry_id, user_id=user_id, title=title)
            session.add(row)
            session.commit()
            session.refresh(row)
            result = self._serialize_conversation_row(row)
            logger.info(_format_timing_log("create_conversation", (perf_counter() - started) * 1000, conversation_id=result["id"]))
            return result

    def list_messages(self, conversation_id: int) -> list[dict]:
        total_started = perf_counter()
        acquire_started = perf_counter()
        with self._session_factory() as session:
            from backend.repositories.message_repository import MessageRepository

            acquire_connection_ms = (perf_counter() - acquire_started) * 1000
            query_started = perf_counter()
            records = MessageRepository(session).list_by_conv_id(conversation_id)
            result = [self._serialize_message(record) for record in records]
            query_ms = (perf_counter() - query_started) * 1000
            logger.info(
                _format_timing_log(
                    "list_messages",
                    (perf_counter() - total_started) * 1000,
                    conversation_id=conversation_id,
                    acquire_connection_ms=f"{acquire_connection_ms:.1f}",
                    query_ms=f"{query_ms:.1f}",
                    count=len(result),
                )
            )
            return result

    def respond(self, *, conversation_id: int, message: str, mode: str) -> dict:
        # One debug turn persists the new user message, runs the existing agent
        # workflow against prior history, then stores the assistant result plus
        # its debug payload for inspection in the page.
        total_started = perf_counter()
        with self._session_factory() as session:
            from backend.repositories.conversation_repository import ConversationRepository
            from backend.repositories.message_repository import MessageRepository

            conversations = ConversationRepository(session)
            messages = MessageRepository(session)

            load_started = perf_counter()
            conversation = conversations.get_by_id(conversation_id)
            if conversation is None:
                raise ValueError(f"conversation {conversation_id} not found")

            prior_messages = messages.list_by_conv_id(conversation_id)
            user_message = messages.create(
                MessageWriteModel(
                    id=self._id_generator.next_id(),
                    conv_id=conversation_id,
                    role="user",
                    content=message,
                )
            )
            load_history_ms = (perf_counter() - load_started) * 1000

            retrieval_service = build_retrieval_service(session=session, settings=self._settings)
            retrieval_preparation_service = build_retrieval_preparation_service(settings=self._settings)
            workflow = build_agent_workflow(
                retrieval_preparation_service=retrieval_preparation_service,
                retrieval_service=retrieval_service,
                min_acceptable_results=self._settings.agent_workflow.min_acceptable_results,
                hard_constraint_min_match_ratio=self._settings.agent_workflow.hard_constraint_min_match_ratio,
                max_retry_count=self._settings.agent_workflow.max_retry_count,
                settings=self._settings,
            )

            workflow_started = perf_counter()
            result = workflow.invoke(
                {
                    "request_id": f"chat-{conversation_id}-{user_message.id}",
                    "conversation_id": str(conversation_id),
                    "user_id": conversation.user_id,
                    "original_query": message,
                    "conversation_history": [
                        {"role": item.role, "content": item.content}
                        for item in prior_messages
                    ],
                    "mode": mode,
                    "topic_action": None,
                    "hard_constraints": {},
                    "soft_preferences": {},
                    "search_specs": [],
                    "search_results": [],
                    "critic_result": None,
                    "retry_count": 0,
                    "final_items": [],
                    "response_reason": None,
                    "errors": [],
                }
            )
            workflow_ms = (perf_counter() - workflow_started) * 1000

            critic_result = result.get("critic_result")
            search_specs = result.get("search_specs", [])
            final_items = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in result.get("final_items", [])
            ]
            assistant_content = self._build_assistant_content(
                response_reason=result.get("response_reason"),
                final_items=final_items,
            )
            persist_started = perf_counter()
            assistant_message = messages.create(
                MessageWriteModel(
                    id=self._id_generator.next_id(),
                    conv_id=conversation_id,
                    role="assistant",
                    content=assistant_content,
                    structured_data={
                        "parts": [{"type": "text", "text": assistant_content}],
                        "agent": {
                            "mode": result.get("mode"),
                            "topic_action": result.get("topic_action"),
                            "search_spec_ids": [spec.spec_id for spec in search_specs],
                            "critic_reason_code": None if critic_result is None else critic_result.reason_code,
                            "retry_count": result.get("retry_count", 0),
                            "response_reason": result.get("response_reason"),
                        },
                        "retrieval": {
                            "final_items": final_items,
                        },
                    },
                )
            )

            row = session.get(ConversationOrmModel, conversation_id)
            if row is not None:
                row.message_count = row.message_count + 2
                row.updated_at = datetime.now(UTC)
                if not row.title:
                    row.title = message[:48]

            session.commit()
            session.refresh(row)
            persist_ms = (perf_counter() - persist_started) * 1000
            total_ms = (perf_counter() - total_started) * 1000
            logger.info(
                _format_timing_log(
                    "respond",
                    total_ms,
                    conversation_id=conversation_id,
                    history_count=len(prior_messages),
                    load_history_ms=f"{load_history_ms:.1f}",
                    workflow_ms=f"{workflow_ms:.1f}",
                    persist_ms=f"{persist_ms:.1f}",
                )
            )

            return {
                "conversation": self._serialize_conversation_row(row),
                "assistant_message": self._serialize_message(assistant_message),
                "debug": None
                if critic_result is None
                else {
                    "mode": result.get("mode"),
                    "topic_action": result.get("topic_action"),
                    "search_spec_ids": [spec.spec_id for spec in search_specs],
                    "critic_reason_code": critic_result.reason_code,
                    "retry_count": result.get("retry_count", 0),
                },
            }

    def _build_assistant_content(self, *, response_reason: str | None, final_items: list[dict]) -> str:
        count = len(final_items)
        if response_reason and count:
            return f"{response_reason}. I kept {count} candidate results for inspection."
        if response_reason:
            return response_reason
        if count:
            return f"I found {count} candidate results for this turn."
        return "I could not find any candidate results for this turn."

    def _serialize_conversation_row(self, row: ConversationOrmModel) -> dict:
        return {
            "id": str(row.id),
            "title": row.title,
            "user_id": row.user_id,
            "message_count": row.message_count,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _serialize_message(self, record: MessageRecord) -> dict:
        return {
            "id": str(record.id),
            "conversation_id": str(record.conv_id),
            "role": record.role,
            "content": record.content,
            "created_at": record.created_at,
            "structured_data": record.structured_data,
            "metadata": record.metadata,
        }
