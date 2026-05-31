from backend.agents.nodes.constraint_node import ConstraintNode
from backend.agents.nodes.critic_node import CriticNode
from backend.agents.nodes.intent_node import IntentNode
from backend.agents.nodes.planner_node import PlannerNode
from backend.agents.nodes.response_node import ResponseNode
from backend.agents.nodes.search_execution_node import SearchExecutionNode
from backend.agents.policies.critic_policy import CriticPolicy
from backend.agents.visual_search_graph import build_visual_search_graph


def build_agent_workflow(
    *,
    retrieval_preparation_service,
    retrieval_service,
    min_acceptable_results: int,
    hard_constraint_min_match_ratio: float,
    max_retry_count: int,
):
    return build_visual_search_graph(
        intent_node=IntentNode(),
        constraint_node=ConstraintNode(retrieval_preparation_service),
        planner_node=PlannerNode(),
        search_execution_node=SearchExecutionNode(retrieval_service),
        critic_node=CriticNode(
            CriticPolicy(
                min_acceptable_results=min_acceptable_results,
                hard_constraint_min_match_ratio=hard_constraint_min_match_ratio,
            )
        ),
        response_node=ResponseNode(),
        max_retry_count=max_retry_count,
    )
