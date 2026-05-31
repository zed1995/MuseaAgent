from backend.agents.contracts import SearchResult, SearchSpec
from backend.agents.nodes.search_execution_node import SearchExecutionNode


class AgentRuntimeService:
    def __init__(self, retrieval_service, graph) -> None:
        self._retrieval_service = retrieval_service
        self._graph = graph

    def execute_search_specs(
        self,
        mode: str,
        search_specs: list[SearchSpec],
    ) -> list[SearchResult]:
        node = SearchExecutionNode(self._retrieval_service)
        state = {
            "mode": mode,
            "search_specs": search_specs,
        }
        return node.run(state)["search_results"]
