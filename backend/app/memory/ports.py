from dataclasses import dataclass
from typing import Protocol
from app.memory.schemas import Candidate
from app.shared.source_resolver import ResolvedSource

@dataclass(frozen=True)
class ExtractionInput:
    event_id: str
    sources: tuple[ResolvedSource, ...]
    schema_version: str = "memory-v1"
    max_output_candidates: int = 20
    max_input_characters: int = 12000

class ModalExtractionPort(Protocol):
    """Deployment-neutral open-weight interface. No database/session or mutation tools."""
    model_profile: str
    def extract(self, request: ExtractionInput) -> list[Candidate]: ...

class MemoryRetrievalPort(Protocol):
    def retrieve(self, session, actor_id: str, event_id: str, **filters) -> dict: ...
