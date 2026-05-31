from backend.llm.runtime.invocation import InvocationMetadata


def build_trace_context(metadata: InvocationMetadata) -> dict[str, object]:
    return {
        "capability": metadata.capability,
        "provider": metadata.provider,
        "model": metadata.model,
        "tags": list(metadata.tags),
    }
