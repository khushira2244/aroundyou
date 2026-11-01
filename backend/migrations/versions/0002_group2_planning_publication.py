"""Group 2 additive event/planning/governance/publication schema. No data reset."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('events',sa.Column('lifecycle',sa.String(30),nullable=False,server_default='created_unpublished'))
    op.add_column('events',sa.Column('draft_step',sa.Integer(),nullable=False,server_default='1'))
    op.add_column('events',sa.Column('draft_form',postgresql.JSONB(),nullable=False,server_default=sa.text("'{}'::jsonb")))
    op.add_column('events',sa.Column('interpretation',postgresql.JSONB(),nullable=True))
    for col in ['current_setup_id','current_finalization_id','current_publication_id']:op.add_column('events',sa.Column(col,sa.String(36),nullable=True))
    op.execute('\nCREATE TABLE ai_runs (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\trequester_id VARCHAR(36) NOT NULL, \n\tkind VARCHAR(30) NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\tsource_versions JSONB NOT NULL, \n\tcontext_manifest JSONB NOT NULL, \n\trequest_message VARCHAR(2000) NOT NULL, \n\tfailure_code VARCHAR(80), \n\tproposal_id VARCHAR(36), \n\tmodel_profile VARCHAR(120), \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(requester_id) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_ai_runs_event_id ON ai_runs (event_id)')
    op.execute('\nCREATE TABLE governance_tickets (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (event_id), \n\tFOREIGN KEY(event_id) REFERENCES events (id)\n)\n\n')
    op.execute('\nCREATE TABLE ai_proposals (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\trun_id VARCHAR(36), \n\tkind VARCHAR(30) NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\tsource_versions JSONB NOT NULL, \n\tpayload JSONB NOT NULL, \n\tdigest VARCHAR(64) NOT NULL, \n\tprovenance JSONB NOT NULL, \n\treview_decision_id VARCHAR(36), \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(run_id) REFERENCES ai_runs (id), \n\tFOREIGN KEY(review_decision_id) REFERENCES review_decisions (id)\n)\n\n')
    op.execute('CREATE INDEX ix_ai_proposals_event_id ON ai_proposals (event_id)')
    op.execute('\nCREATE TABLE planning_drafts (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tcontext_revision_id VARCHAR(36) NOT NULL, \n\tcontent JSONB NOT NULL, \n\tversion INTEGER NOT NULL, \n\tstage_revision INTEGER NOT NULL, \n\twork_revision INTEGER NOT NULL, \n\tstage_confirmed BOOLEAN NOT NULL, \n\twork_confirmed BOOLEAN NOT NULL, \n\tactors_confirmed BOOLEAN NOT NULL, \n\tderived_from JSONB, \n\tPRIMARY KEY (id), \n\tUNIQUE (event_id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(context_revision_id) REFERENCES event_context_revisions (id)\n)\n\n')
    op.execute('\nCREATE TABLE event_setup_revisions (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tsource_plan_id VARCHAR(36) NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tdigest VARCHAR(64) NOT NULL, \n\tcreated_by VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_setup_sequence UNIQUE (event_id, sequence), \n\tCONSTRAINT uq_setup_event UNIQUE (event_id, id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(source_plan_id) REFERENCES plan_versions (id), \n\tFOREIGN KEY(created_by) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_event_setup_revisions_event_id ON event_setup_revisions (event_id)')
    op.execute('\nCREATE TABLE event_finalizations (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tsetup_revision_id VARCHAR(36) NOT NULL, \n\tplan_id VARCHAR(36) NOT NULL, \n\treviewed_digest VARCHAR(64) NOT NULL, \n\tapproved_by VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_finalization_event UNIQUE (event_id, id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(setup_revision_id) REFERENCES event_setup_revisions (id), \n\tFOREIGN KEY(plan_id) REFERENCES plan_versions (id), \n\tFOREIGN KEY(approved_by) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_event_finalizations_event_id ON event_finalizations (event_id)')
    op.execute('\nCREATE TABLE publications (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tfinalization_id VARCHAR(36) NOT NULL, \n\tplan_id VARCHAR(36) NOT NULL, \n\tsetup_revision_id VARCHAR(36) NOT NULL, \n\tsnapshot JSONB NOT NULL, \n\tdigest VARCHAR(64) NOT NULL, \n\tvisibility VARCHAR(30) NOT NULL, \n\tpublished_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tapproved_by VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_publication_sequence UNIQUE (event_id, sequence), \n\tCONSTRAINT uq_publication_event UNIQUE (event_id, id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(finalization_id) REFERENCES event_finalizations (id), \n\tFOREIGN KEY(plan_id) REFERENCES plan_versions (id), \n\tFOREIGN KEY(setup_revision_id) REFERENCES event_setup_revisions (id), \n\tFOREIGN KEY(approved_by) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_publications_event_id ON publications (event_id)')
    op.execute('\nCREATE TABLE published_roles (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tpublication_id VARCHAR(36) NOT NULL, \n\tplan_id VARCHAR(36) NOT NULL, \n\trequirement_id VARCHAR(60) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_published_requirement UNIQUE (publication_id, requirement_id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(publication_id) REFERENCES publications (id), \n\tFOREIGN KEY(plan_id) REFERENCES plan_versions (id)\n)\n\n')
    op.add_column('job_tasks',sa.Column('ai_run_id',sa.String(36),nullable=True))
    op.create_foreign_key('fk_job_ai_run','job_tasks','ai_runs',['ai_run_id'],['id'])
    op.create_unique_constraint('uq_job_ai_run','job_tasks',['ai_run_id'])
    op.create_foreign_key('fk_event_setup','events','event_setup_revisions',['id','current_setup_id'],['event_id','id'])
    op.create_foreign_key('fk_event_finalization','events','event_finalizations',['id','current_finalization_id'],['event_id','id'])
    op.create_foreign_key('fk_event_publication','events','publications',['id','current_publication_id'],['event_id','id'])
    op.execute("CREATE TRIGGER immutable_event_setup_revisions BEFORE UPDATE OR DELETE ON event_setup_revisions FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()")
    op.execute("CREATE TRIGGER immutable_event_finalizations BEFORE UPDATE OR DELETE ON event_finalizations FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()")
    op.execute("CREATE TRIGGER immutable_publications BEFORE UPDATE OR DELETE ON publications FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()")
    op.execute("CREATE TRIGGER immutable_published_roles BEFORE UPDATE OR DELETE ON published_roles FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()")
    op.execute("""CREATE FUNCTION protect_proposal_content() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
        IF TG_OP='DELETE' OR (to_jsonb(NEW) - ARRAY['status','review_decision_id']) IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['status','review_decision_id']) THEN RAISE EXCEPTION 'immutable proposal content'; END IF;
        RETURN NEW; END $$""")
    op.execute("CREATE TRIGGER immutable_proposal BEFORE UPDATE OR DELETE ON ai_proposals FOR EACH ROW EXECUTE FUNCTION protect_proposal_content()")
    op.alter_column('events','lifecycle',server_default=None)
    op.alter_column('events','draft_step',server_default=None)
    op.alter_column('events','draft_form',server_default=None)

def downgrade():
    for name in ['fk_event_publication','fk_event_finalization','fk_event_setup']:op.drop_constraint(name,'events',type_='foreignkey')
    op.drop_column('job_tasks','ai_run_id')
    op.drop_table('published_roles')
    op.drop_table('publications')
    op.drop_table('event_finalizations')
    op.drop_table('event_setup_revisions')
    op.drop_table('planning_drafts')
    op.drop_table('ai_proposals')
    op.drop_table('governance_tickets')
    op.drop_table('ai_runs')
    op.execute('DROP FUNCTION protect_proposal_content()')
    for col in ['current_setup_id','current_finalization_id','current_publication_id','interpretation','draft_form','draft_step','lifecycle']:op.drop_column('events',col)
