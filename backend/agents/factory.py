from backend.core.config import Settings
from backend.llm.chains.critic_chain import CriticAdviceChain
from backend.llm.chains.intent_chain import IntentClassificationChain
from backend.llm.chains.planner_chain import SearchPlannerChain
from backend.llm.chains.response_chain import ResponseReasonChain
from backend.llm.providers.factory import build_chat_model
from backend.agents.nodes.constraint_node import ConstraintNode
from backend.agents.nodes.critic_node import CriticNode
from backend.agents.nodes.intent_node import IntentNode
from backend.agents.nodes.planner_node import PlannerNode
from backend.agents.nodes.response_node import ResponseNode
from backend.agents.nodes.search_execution_node import SearchExecutionNode
from backend.agents.policies.critic_policy import HybridCriticPolicy, RuleCriticPolicy
from backend.agents.visual_search_graph import build_visual_search_graph


def build_agent_workflow(
    *,
    retrieval_preparation_service,
    retrieval_service,
    min_acceptable_results: int,
    hard_constraint_min_match_ratio: float,
    max_retry_count: int,
    intent_chain=None,
    planner_chain=None,
    critic_advice_chain=None,
    response_reason_chain=None,
    settings: Settings | None = None,
):
    if settings is not None:
        intent_chain = intent_chain or _build_optional_chain(
            capability="intent",
            config=settings.llm.intent,
            chain_cls=IntentClassificationChain,
        )
        planner_chain = planner_chain or _build_optional_chain(
            capability="planner",
            config=settings.llm.planner,
            chain_cls=SearchPlannerChain,
        )
        critic_advice_chain = critic_advice_chain or _build_optional_chain(
            capability="critic",
            config=settings.llm.critic,
            chain_cls=CriticAdviceChain,
        )
        response_reason_chain = response_reason_chain or _build_optional_chain(
            capability="response",
            config=settings.llm.response,
            chain_cls=ResponseReasonChain,
        )

    return build_visual_search_graph(
        intent_node=IntentNode(chain=intent_chain),
        constraint_node=ConstraintNode(retrieval_preparation_service),
        planner_node=PlannerNode(chain=planner_chain),
        search_execution_node=SearchExecutionNode(retrieval_service),
        critic_node=CriticNode(
            HybridCriticPolicy(
                base_policy=RuleCriticPolicy(
                    min_acceptable_results=min_acceptable_results,
                    hard_constraint_min_match_ratio=hard_constraint_min_match_ratio,
                ),
                advice_chain=critic_advice_chain,
            )
        ),
        response_node=ResponseNode(chain=response_reason_chain),
        max_retry_count=max_retry_count,
    )


def _build_optional_chain(*, capability: str, config, chain_cls):
    if not config.api_key:
        return None

    model = build_chat_model(
        capability=capability,
        provider_name=config.provider,
        model_name=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
    )
    return chain_cls(model)
