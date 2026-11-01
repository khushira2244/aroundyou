# Import the complete Group 1 metadata graph for Alembic and the application.
from app.access.models import User, EventGrant
from app.events.models import Event, ContextRevision
from app.planning.models import PlanVersion
from app.shared.models import ReviewDecision, AuditEvent, IdempotencyRecord, OutboxEvent, JobTask
from app.memory.models import MemoryEntry, MemorySource, MemoryRun

from app.planning.draft_models import PlanningDraft
from app.ai.models import AIRun, AIProposal
from app.publication.models import SetupRevision, Finalization, Publication, PublishedRole
from app.governance.models import GovernanceTicket

from app.participation.models import Application,ApplicationRevision,Assignment,AssignmentTerms,AssignmentConsent,OperationalSource
from app.sponsorship.models import Organization,OrganizationMembership,SupportOffer,SupportFulfillment,SupportOfferRevision
from app.resources.models import ResourceTransaction,ResourceReservation

from app.execution.models import WorkExecution,WorkReport,EvidenceAsset,ExecutionRevision,ExecutionReviewGrant,AttendanceRecord,ResourceOperation,WorkIssue,CoordinationRecord
