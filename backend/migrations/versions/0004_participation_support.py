"""Group 3 participation, consent, support and verified stock; additive only."""
from alembic import op
revision='0004'
down_revision='0003'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('\nCREATE TABLE organizations (\n\tid VARCHAR(36) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\tprofile JSONB NOT NULL, \n\tPRIMARY KEY (id)\n)\n\n')
    op.execute('\nCREATE TABLE organization_memberships (\n\tid VARCHAR(36) NOT NULL, \n\torganization_id VARCHAR(36) NOT NULL, \n\taccount_id VARCHAR(36) NOT NULL, \n\tpermission VARCHAR(30) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_org_member UNIQUE (organization_id, account_id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(account_id) REFERENCES users (id)\n)\n\n')
    op.execute('\nCREATE TABLE applications (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\taccount_id VARCHAR(36) NOT NULL, \n\tplan_id VARCHAR(36) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\tcontent JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_application_account_event UNIQUE (event_id, account_id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(account_id) REFERENCES users (id), \n\tFOREIGN KEY(plan_id) REFERENCES plan_versions (id)\n)\n\n')
    op.execute('CREATE INDEX ix_applications_account_id ON applications (account_id)')
    op.execute('CREATE INDEX ix_applications_event_id ON applications (event_id)')
    op.execute('\nCREATE TABLE application_revisions (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tapplication_id VARCHAR(36) NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tcontent JSONB NOT NULL, \n\tdigest VARCHAR(64) NOT NULL, \n\tcreated_by VARCHAR(36) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_application_sequence UNIQUE (application_id, sequence), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(application_id) REFERENCES applications (id), \n\tFOREIGN KEY(created_by) REFERENCES users (id)\n)\n\n')
    op.execute('\nCREATE TABLE assignments (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tapplication_id VARCHAR(36) NOT NULL, \n\taccount_id VARCHAR(36) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tcurrent_terms_id VARCHAR(36), \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(application_id) REFERENCES applications (id), \n\tFOREIGN KEY(account_id) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_assignments_event_id ON assignments (event_id)')
    op.execute('CREATE INDEX ix_assignments_account_id ON assignments (account_id)')
    op.execute('\nCREATE TABLE assignment_terms (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tassignment_id VARCHAR(36) NOT NULL, \n\tplan_id VARCHAR(36) NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tcontent JSONB NOT NULL, \n\tdigest VARCHAR(64) NOT NULL, \n\tcreated_by VARCHAR(36) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_assignment_term_sequence UNIQUE (assignment_id, sequence), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(assignment_id) REFERENCES assignments (id), \n\tFOREIGN KEY(plan_id) REFERENCES plan_versions (id), \n\tFOREIGN KEY(created_by) REFERENCES users (id)\n)\n\n')
    op.execute('\nCREATE TABLE assignment_consents (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tterms_id VARCHAR(36) NOT NULL, \n\taccount_id VARCHAR(36) NOT NULL, \n\tdecision VARCHAR(20) NOT NULL, \n\tdigest VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_terms_account_consent UNIQUE (terms_id, account_id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(terms_id) REFERENCES assignment_terms (id), \n\tFOREIGN KEY(account_id) REFERENCES users (id)\n)\n\n')
    op.execute('\nCREATE TABLE operational_sources (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\taggregate_id VARCHAR(36) NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tkind VARCHAR(40) NOT NULL, \n\tcontent JSONB NOT NULL, \n\tdigest VARCHAR(64) NOT NULL, \n\tcreated_by VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_operational_source_sequence UNIQUE (event_id, aggregate_id, sequence), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(created_by) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_operational_sources_event_id ON operational_sources (event_id)')
    op.execute('\nCREATE TABLE support_offers (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\taccount_id VARCHAR(36) NOT NULL, \n\torganization_id VARCHAR(36), \n\tplan_id VARCHAR(36) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\tcontent JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(account_id) REFERENCES users (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(plan_id) REFERENCES plan_versions (id)\n)\n\n')
    op.execute('CREATE INDEX ix_support_offers_event_id ON support_offers (event_id)')
    op.execute('\nCREATE TABLE support_fulfillments (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\toffer_id VARCHAR(36) NOT NULL, \n\tquantity NUMERIC(16, 4) NOT NULL, \n\treference VARCHAR(200) NOT NULL, \n\tevidence_reference VARCHAR(1000) NOT NULL, \n\tcreated_by VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_fulfillment_reference UNIQUE (event_id, reference), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(offer_id) REFERENCES support_offers (id), \n\tFOREIGN KEY(created_by) REFERENCES users (id)\n)\n\n')
    op.execute('\nCREATE TABLE resource_transactions (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tresource_id VARCHAR(60) NOT NULL, \n\toffer_id VARCHAR(36), \n\tfulfillment_id VARCHAR(36), \n\tquantity NUMERIC(16, 4) NOT NULL, \n\tunit VARCHAR(80) NOT NULL, \n\treference VARCHAR(200) NOT NULL, \n\tevidence_reference VARCHAR(1000) NOT NULL, \n\tkind VARCHAR(30) NOT NULL, \n\treverses_id VARCHAR(36), \n\tcreated_by VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_resource_receipt_reference UNIQUE (event_id, reference), \n\tCONSTRAINT ck_resource_positive CHECK (quantity > 0), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(offer_id) REFERENCES support_offers (id), \n\tUNIQUE (fulfillment_id), \n\tFOREIGN KEY(fulfillment_id) REFERENCES support_fulfillments (id), \n\tUNIQUE (reverses_id), \n\tFOREIGN KEY(reverses_id) REFERENCES resource_transactions (id), \n\tFOREIGN KEY(created_by) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_resource_transactions_event_id ON resource_transactions (event_id)')
    op.execute('\nCREATE TABLE resource_reservations (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\tresource_id VARCHAR(60) NOT NULL, \n\twork_id VARCHAR(60) NOT NULL, \n\tplan_id VARCHAR(36) NOT NULL, \n\tquantity NUMERIC(16, 4) NOT NULL, \n\tunit VARCHAR(80) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(plan_id) REFERENCES plan_versions (id)\n)\n\n')
    op.execute('CREATE INDEX ix_resource_reservations_event_id ON resource_reservations (event_id)')
    op.execute('ALTER TABLE assignments ADD CONSTRAINT fk_assignment_terms FOREIGN KEY(current_terms_id) REFERENCES assignment_terms (id)')
    op.execute('\nCREATE TABLE support_offer_revisions (\n\tid VARCHAR(36) NOT NULL, \n\tevent_id VARCHAR(36) NOT NULL, \n\toffer_id VARCHAR(36) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tcontent JSONB NOT NULL, \n\tcreated_by VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_support_offer_version UNIQUE (offer_id, version), \n\tFOREIGN KEY(event_id) REFERENCES events (id), \n\tFOREIGN KEY(offer_id) REFERENCES support_offers (id), \n\tFOREIGN KEY(created_by) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE TRIGGER immutable_support_offer_revisions BEFORE UPDATE OR DELETE ON support_offer_revisions FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()')
    op.execute('CREATE TRIGGER immutable_application_revisions BEFORE UPDATE OR DELETE ON application_revisions FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()')
    op.execute('CREATE TRIGGER immutable_assignment_terms BEFORE UPDATE OR DELETE ON assignment_terms FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()')
    op.execute('CREATE TRIGGER immutable_assignment_consents BEFORE UPDATE OR DELETE ON assignment_consents FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()')
    op.execute('CREATE TRIGGER immutable_operational_sources BEFORE UPDATE OR DELETE ON operational_sources FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()')
    op.execute('CREATE TRIGGER immutable_support_fulfillments BEFORE UPDATE OR DELETE ON support_fulfillments FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()')
    op.execute('CREATE TRIGGER immutable_resource_transactions BEFORE UPDATE OR DELETE ON resource_transactions FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()')

def downgrade():
    op.drop_constraint('fk_assignment_terms','assignments',type_='foreignkey')
    op.drop_table('resource_reservations')
    op.drop_table('resource_transactions')
    op.drop_table('support_fulfillments')
    op.execute('DROP TABLE IF EXISTS support_offer_revisions')
    op.drop_table('support_offers')
    op.drop_table('operational_sources')
    op.drop_table('assignment_consents')
    op.drop_table('assignment_terms')
    op.drop_table('assignments')
    op.drop_table('application_revisions')
    op.drop_table('applications')
    op.drop_table('organization_memberships')
    op.drop_table('organizations')
