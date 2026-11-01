import pytest
from pydantic import ValidationError
from app.settings import Settings
from app.memory.schemas import Candidate, ExtractionRequest
from app.memory.projections import project
from app.shared.source_resolver import ResolvedSource
from app.memory.schemas import SourceRef
from app.memory.service import validate_candidates
from app.planning.schemas import PlanContent
from app.api.errors import DomainError

@pytest.mark.parametrize("payload",[{"work":[{"id":"w","stage_id":"missing","title":"Work"}]},{"stages":[{"id":"s","title":"Stage"}],"work":[{"id":"w","stage_id":"s","title":"Work"}],"dependencies":[{"predecessor":"w","successor":"w"}]}])
def test_invalid_graph(payload):
    with pytest.raises(ValidationError): PlanContent.model_validate(payload)

def test_settings_fail_closed():
    with pytest.raises(ValidationError):Settings(_env_file=None,database_url="sqlite://",session_secret="short")

def test_extra_authority_fields_rejected():
    with pytest.raises(ValidationError): ExtractionRequest.model_validate({"source_refs":[],"actor_id":"forged"})

def test_model_cannot_invent_outcomes_or_provenance():
    ref=SourceRef(source_kind="context",source_id="s",source_revision=1,source_digest="a"*64)
    source=ResolvedSource(ref,"proposal","event","proposed","unknown",None,{})
    candidate=project([source])[0]
    candidate.assertions[0].evidence_stage="verified";candidate.assertions[0].outcome="successful"
    with pytest.raises(DomainError,match="unsupported_outcome"): validate_candidates([candidate],[source])
    candidate=project([source])[0];candidate.assertions[0].source_refs[0]=ref.model_copy(update={"source_id":"foreign"})
    with pytest.raises(DomainError,match="invalid_provenance"):validate_candidates([candidate],[source])
