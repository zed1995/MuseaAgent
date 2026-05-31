import logging

from backend.services.chat_debug.service import _format_timing_log


def test_format_timing_log_includes_operation_duration_and_fields() -> None:
    message = _format_timing_log(
        "respond",
        123.4,
        conversation_id=9001,
        message_count=2,
    )

    assert message == "[debug-chat] respond took 123.4ms conversation_id=9001 message_count=2"


def test_format_timing_log_supports_phase_breakdown_fields() -> None:
    message = _format_timing_log(
        "list_conversations",
        432.1,
        acquire_connection_ms="321.0",
        query_ms="111.1",
        count=4,
    )

    assert message == (
        "[debug-chat] list_conversations took 432.1ms "
        "acquire_connection_ms=321.0 query_ms=111.1 count=4"
    )
