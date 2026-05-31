from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import create_engine

from backend.agents.factory import build_agent_workflow
from backend.core.config import Settings
from backend.schemas.search import AgentSearchDebugSummary, AgentSearchResponse
from backend.services.retrieval.factory import build_retrieval_service
from backend.services.retrieval_preparation.factory import (
    build_retrieval_preparation_service,
)
from backend.services.retrieval_preparation.service import RetrievalPreparationError

router = APIRouter(tags=["search-agent"])


@router.get("/search/agent", response_model=AgentSearchResponse)
def search_agent(
    request: Request,
    query: str = Query(..., description="Chinese or English search query"),
    mode: str = Query("auto", description="wallpaper | reference | photographer | auto"),
):
    settings: Settings = request.app.state.settings
    engine = create_engine(settings.database.url)
    session = engine.connect()

    try:
        from sqlalchemy.orm import Session as ORMSession

        orm_session = ORMSession(bind=session)
        retrieval_service = build_retrieval_service(session=orm_session, settings=settings)
        retrieval_preparation_service = build_retrieval_preparation_service(settings=settings)
        workflow = build_agent_workflow(
            retrieval_preparation_service=retrieval_preparation_service,
            retrieval_service=retrieval_service,
            min_acceptable_results=settings.agent_workflow.min_acceptable_results,
            hard_constraint_min_match_ratio=settings.agent_workflow.hard_constraint_min_match_ratio,
            max_retry_count=settings.agent_workflow.max_retry_count,
            settings=settings,
        )
        try:
            result = workflow.invoke(
                {
                    "request_id": f"agent-{query}",
                    "conversation_id": None,
                    "user_id": None,
                    "original_query": query,
                    "conversation_history": [],
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
        except RetrievalPreparationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        critic_result = result.get("critic_result")
        search_specs = result.get("search_specs", [])
        return AgentSearchResponse(
            request_id=result["request_id"],
            final_items=[item.model_dump() for item in result["final_items"]],
            response_reason=result.get("response_reason"),
            debug=AgentSearchDebugSummary(
                mode=result["mode"],
                topic_action=result.get("topic_action"),
                search_spec_ids=[spec.spec_id for spec in search_specs],
                critic_reason_code=None if critic_result is None else critic_result.reason_code,
                retry_count=result["retry_count"],
            ),
        )
    finally:
        session.close()
        engine.dispose()
