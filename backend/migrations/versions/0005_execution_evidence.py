"""Group 4 execution/evidence, human review and coordination; additive."""
from alembic import op
revision='0005'
down_revision='0004'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('\nCREATE TABLE coordination_records (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\taccount_id VARCHAR(36) NOT NULL, \n\tkind VARCHAR(30) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tcontent JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(account_id) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_coordination_records_event_id ON coordination_records (event_id)')
    op.execute('\nCREATE TABLE execution_revisions (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\taggregate_id VARCHAR(36) NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tkind VARCHAR(40) NOT NULL, \n\tcontent JSONB NOT NULL, \n\tdigest VARCHAR(64) NOT NULL, \n\tactor_id VARCHAR(36) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_execution_revision_sequence UNIQUE (aggregate_id, sequence), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_execution_revisions_event_id ON execution_revisions (event_id)')
    op.execute('\nCREATE TABLE execution_review_grants (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\taccount_id VARCHAR(36) NOT NULL, \n\tstage_id VARCHAR(60) NOT NULL, \n\tplan_id VARCHAR(36) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_execution_reviewer_stage UNIQUE (event_id, account_id, stage_id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(account_id) REFERENCES users (id), \n\tFOREIGN KEY(plan_id) REFERENCES plan_versions (id)\n)\n\n')
    op.execute('\nCREATE TABLE work_executions (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tplan_id VARCHAR(36) NOT NULL, \n\twork_id VARCHAR(60) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tcontent JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_execution_work_plan UNIQUE (event_id, plan_id, work_id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(plan_id) REFERENCES plan_versions (id)\n)\n\n')
    op.execute('CREATE INDEX ix_work_executions_event_id ON work_executions (event_id)')
    op.execute('\nCREATE TABLE work_issues (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tplan_id VARCHAR(36) NOT NULL, \n\taccount_id VARCHAR(36) NOT NULL, \n\twork_id VARCHAR(60) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tcontent JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(plan_id) REFERENCES plan_versions (id), \n\tFOREIGN KEY(account_id) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_work_issues_event_id ON work_issues (event_id)')
    op.execute('\nCREATE TABLE attendance_records (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tassignment_id VARCHAR(36) NOT NULL, \n\taccount_id VARCHAR(36) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tcontent JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_attendance_assignment UNIQUE (event_id, assignment_id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(assignment_id) REFERENCES assignments (id), \n\tFOREIGN KEY(account_id) REFERENCES users (id)\n)\n\n')
    op.execute('\nCREATE TABLE work_reports (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tplan_id VARCHAR(36) NOT NULL, \n\tassignment_id VARCHAR(36) NOT NULL, \n\tterms_id VARCHAR(36) NOT NULL, \n\taccount_id VARCHAR(36) NOT NULL, \n\twork_id VARCHAR(60) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tcontent JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(plan_id) REFERENCES plan_versions (id), \n\tFOREIGN KEY(assignment_id) REFERENCES assignments (id), \n\tFOREIGN KEY(terms_id) REFERENCES assignment_terms (id), \n\tFOREIGN KEY(account_id) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_work_reports_event_id ON work_reports (event_id)')
    op.execute('\nCREATE TABLE evidence_assets (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\treport_id VARCHAR(36) NOT NULL, \n\taccount_id VARCHAR(36) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tcontent JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(report_id) REFERENCES work_reports (id), \n\tFOREIGN KEY(account_id) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_evidence_assets_event_id ON evidence_assets (event_id)')
    op.execute('\nCREATE TABLE resource_operations (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\treservation_id VARCHAR(36) NOT NULL, \n\treport_id VARCHAR(36) NOT NULL, \n\tresource_id VARCHAR(60) NOT NULL, \n\treport_revision INTEGER NOT NULL, \n\tusage_id VARCHAR(60) NOT NULL, \n\tkind VARCHAR(30) NOT NULL, \n\tquantity NUMERIC(16, 4) NOT NULL, \n\treference VARCHAR(200) NOT NULL, \n\treverses_id VARCHAR(36), \n\tcreated_by VARCHAR(36) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_resource_operation_reference UNIQUE (event_id, reference), \n\tCONSTRAINT uq_resource_operation_reversal UNIQUE (reverses_id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(reservation_id) REFERENCES resource_reservations (id), \n\tFOREIGN KEY(report_id) REFERENCES work_reports (id), \n\tFOREIGN KEY(reverses_id) REFERENCES resource_operations (id), \n\tFOREIGN KEY(created_by) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_resource_operations_event_id ON resource_operations (event_id)')
    op.execute("CREATE TRIGGER immutable_execution_revisions BEFORE UPDATE OR DELETE ON execution_revisions FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()")
    op.execute("CREATE TRIGGER immutable_resource_operations BEFORE UPDATE OR DELETE ON resource_operations FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()")

def downgrade():
    op.execute("DROP TABLE resource_operations")
    op.execute("DROP TABLE evidence_assets")
    op.execute("DROP TABLE work_reports")
    op.execute("DROP TABLE attendance_records")
    op.execute("DROP TABLE work_issues")
    op.execute("DROP TABLE work_executions")
    op.execute("DROP TABLE execution_review_grants")
    op.execute("DROP TABLE execution_revisions")
    op.execute("DROP TABLE coordination_records")
