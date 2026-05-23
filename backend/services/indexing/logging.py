from dataclasses import dataclass


@dataclass(slots=True)
class IngestionRunResult:
    trigger_type: str
    total_candidates: int
    succeeded: int
    failed: int
