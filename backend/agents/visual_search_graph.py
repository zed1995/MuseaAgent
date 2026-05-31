from typing import Literal

from langgraph.graph import END, START, StateGraph

from backend.agents.policies.retry_policy import apply_retry_strategy
from backend.agents.states import VisualSearchState


def build_visual_search_graph(
    intent_node,
    constraint_node,
    planner_node,
    search_execution_node,
    critic_node,
    response_node,
    *,
    max_retry_count: int,
):
    graph = StateGraph(VisualSearchState)

    graph.add_node("intent", intent_node.run)
    graph.add_node("constraint", constraint_node.run)
    graph.add_node("planner", planner_node.run)
    graph.add_node("search_execution", search_execution_node.run)
    graph.add_node("critic", critic_node.run)
    graph.add_node("prepare_retry", _build_prepare_retry_node())
    graph.add_node("response", response_node.run)

    graph.add_edge(START, "intent")
    graph.add_edge("intent", "constraint")
    graph.add_edge("constraint", "planner")
    graph.add_edge("planner", "search_execution")
    graph.add_edge("search_execution", "critic")
    graph.add_conditional_edges(
        "critic",
        _build_critic_router(max_retry_count),
        {
            "prepare_retry": "prepare_retry",
            "response": "response",
        },
    )
    graph.add_edge("prepare_retry", "search_execution")
    graph.add_edge("response", END)

    return graph.compile()


def _build_critic_router(max_retry_count: int):
    def _route(state: VisualSearchState) -> Literal["prepare_retry", "response"]:
        critic_result = state["critic_result"]
        if (
            critic_result is not None
            and not critic_result.passed
            and critic_result.retry_strategy != "none"
            and state["retry_count"] < max_retry_count
        ):
            return "prepare_retry"
        return "response"

    return _route


def _build_prepare_retry_node():
    def _prepare_retry(state: VisualSearchState) -> dict[str, object]:
        critic_result = state["critic_result"]
        if critic_result is None:
            return {}

        return {
            "search_specs": apply_retry_strategy(state["search_specs"], critic_result),
            "retry_count": state["retry_count"] + 1,
        }

    return _prepare_retry
