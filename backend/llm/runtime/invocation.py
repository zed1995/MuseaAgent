from dataclasses import dataclass, field


@dataclass(slots=True)
class InvocationMetadata:
    capability: str
    provider: str
    model: str
    tags: list[str] = field(default_factory=list)
