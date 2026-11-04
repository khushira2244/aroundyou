"""Private, pre-submission role advice. No assignments or submission authority."""
import json
from app.ai.models import AIRun, AIProposal
from app.ai.planning_port import MuseSparkRequest, WORKFLOW_INSTRUCTIONS
from app.participation.advisory import ParticipationAdvice, validate_output
from app.participation.service import app_for, published, require_state
from app.shared.types import uid, digest
from app.shared.audit import audit
from app.api.errors import DomainError


def suggest(session, actor, event, application_id, adapter):
    application = app_for(session, event, application_id, actor)
    require_state(application.status == 'application_draft', 'Role suggestions require your saved application draft')
    release = published(session, event, actor, True)
    require_state(release.plan_id == application.plan_id, 'Published roles changed; refresh your application')
    require_state(bool(application.content['intervals']), 'Save availability before requesting role suggestions')
    if not adapter or not getattr(adapter, 'live_provider', False):
        raise DomainError('provider_unavailable', 'AI role suggestions are unavailable. You can still choose published roles manually.', 503)
    # Only this applicant's relevant statements and published work enter the model context.
    answers = application.content['answers']
    reported = {k: answers[k] for k in ('skills', 'motivation', 'volunteer_experience', 'coordination_experience', 'community_experience', 'contribution', 'preferred_responsibility', 'leadership_interest', 'limitations', 'work_preferences') if k in answers}
    plan = release.snapshot['plan']
    context = {'scope': {'application_id': application.id}, 'published_plan_id': release.plan_id,
               'published_plan': {'roles': plan['roles'], 'work': plan['work']}, 'resources': [],
               'applicant': {'reported_answers': reported, 'availability': application.content['intervals'], 'requested_roles': application.content['role_ids']}}
    source = {'application_revision': application.sequence, 'publication_id': release.id, 'plan_id': release.plan_id}
    current = {'participation_and_resources': context}
    run = AIRun(id=uid(), event_id=event.id, requester_id=actor, kind='participant_role_fit', status='running', source_versions=source,
                context_manifest={'authoritative_current': current}, request_message='Suggest roles for my availability and stated experience.')
    session.add(run); session.flush()
    try:
        result = adapter.propose(MuseSparkRequest(kind='participation', authoritative_current=current, cited_historical_memory={}, source_versions=source,
            instruction=WORKFLOW_INSTRUCTIONS['participation'] + ' This is private pre-submission guidance. Suggest only existing published roles fitting supplied availability and self-reported experience. Do not use demographics. Return at most three recommendations; clarify unknown qualifications. No assignments, approvals or submission. resource_advice must be empty.',
            output_schema=ParticipationAdvice.model_json_schema()))
        result = dict(result)
        metadata = result.pop('_provider_metadata', None)
        if len(json.dumps(result)) > 24000:
            raise DomainError('invalid_model_output', 'Role suggestion output exceeded its limit', 422)
        data = validate_output(result, current)
        if data['resource_advice'] or len(data['recommendations']) > 3:
            raise DomainError('invalid_model_output', 'Role suggestion output exceeded its scope', 422)
        proposal = AIProposal(id=uid(), event_id=event.id, run_id=run.id, kind='participant_role_fit', status='pending', source_versions=source,
            payload=data, digest=digest(data), provenance={'source': 'meta', 'model_execution': True, 'model': adapter.model_profile, 'provider_metadata': metadata or {}, 'private_applicant_only': True})
        session.add(proposal); session.flush()
        run.status='succeeded'; run.proposal_id=proposal.id; run.model_profile=adapter.model_profile
        audit(session, actor, event.id, 'participation.role_suggestions', proposal.id)
        return {'status': 'available', 'recommendations': data['recommendations'], 'questions': data['clarification_questions'], 'unknowns': data['unknowns'], 'model_execution': True, 'source_versions': source}
    except (DomainError, ValueError, TypeError):
        run.status='failed'; run.failure_code='role_suggestion_failed'
        audit(session, actor, event.id, 'participation.role_suggestions_failed', run.id)
        return {'status': 'failed', 'recommendations': [], 'message': 'AI could not produce valid role suggestions. Your saved answers are preserved; choose a role manually or retry explicitly.', 'model_execution': True, 'validated': False}
