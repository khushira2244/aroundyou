"""Idempotent, explicit development-only import of the ten existing catalog examples.

No Canary Hill, fictional coordinates, accepted participants or execution outcomes.
Empty plan snapshots support profile rendering; they assert no confirmed field work.
"""
from copy import deepcopy
import json
from pathlib import Path
from sqlalchemy import select,text
from app.settings import Settings
from app.shared.database import database
from app.shared.unit_of_work import unit_of_work
from app.shared.types import uid,digest
from app.shared.audit import audit
from app.access.models import User,EventGrant
from app.access.permissions import PERMISSIONS
from app.events.models import Event
from app.events.source_revisions import append_context,append_plan
from app.events.creation_schemas import CreationForm
from app.planning.schemas import PlanContent
from app.publication.models import SetupRevision,Finalization,Publication
from app.publication.service import default_configuration
import app.models

SOURCE=Path(__file__).resolve().parents[2]/'demo/fixtures/events.json'

def import_examples(db,rows):
    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('discovery-example-import',0))"))
    owner=db.scalar(select(User).where(User.external_auth_subject=='hackathon-catalog-import'))
    if not owner:
        owner=User(id=uid(),external_auth_subject='hackathon-catalog-import',display_name='Hackathon example organizer');db.add(owner);db.flush()
    added=0
    for original in rows:
        if original['id']=='event-canary-hill-001':continue
        if db.get(Event,original['id']):continue
        sample=deepcopy(original)
        assert sample['demo'] and 'Hazaribagh' in sample['location']['label']
        assert sample['location']['coordinates'] is None
        sample['title']=sample['title'].replace('\ufffd','’')
        form=CreationForm(title=sample['title'],category=sample['category'],purpose=sample['purpose'],goal=sample['goal'],city='Hazaribagh',state='Jharkhand',country='India').model_dump()
        event=Event(id=sample['id'],creator_id=owner.id,title=sample['title'],category=sample['category'],draft_form=form)
        db.add(event);db.flush()
        for permission in PERMISSIONS:db.add(EventGrant(event_id=event.id,user_id=owner.id,permission=permission,scope={}))
        db.flush()
        context=append_context(db,owner.id,event.id,json.dumps(original,ensure_ascii=False),event.version,snapshot={'demo':True,'source_file':'demo/fixtures/events.json','catalog_only':True})
        plan=append_plan(db,owner.id,event.id,PlanContent().model_dump(),event.version)
        config=default_configuration(event,plan)
        config['participation'].update(visibility='public',registration_open=False,show_open_roles=False)
        setup=SetupRevision(id=uid(),event_id=event.id,sequence=1,source_plan_id=plan.id,configuration=config,digest=digest(config),created_by=owner.id)
        db.add(setup);db.flush()
        final=Finalization(id=uid(),event_id=event.id,setup_revision_id=setup.id,plan_id=plan.id,reviewed_digest=digest({'source':original,'catalog_only':True}),approved_by=owner.id)
        db.add(final);db.flush()
        sample.update(context_id=context.id,lifecycle='published',demo=True,label='Fictional hackathon example — not an actual scheduled event')
        snapshot={'event':sample,'plan':plan.content,'configuration':config,'demo_import':{'catalog_only':True,'source':'demo/fixtures/events.json','user_requested':True}}
        release=Publication(id=uid(),event_id=event.id,sequence=1,finalization_id=final.id,plan_id=plan.id,setup_revision_id=setup.id,snapshot=snapshot,digest=digest(snapshot),visibility='public',approved_by=owner.id)
        db.add(release);db.flush()
        event.current_setup_id=setup.id;event.current_finalization_id=final.id;event.current_publication_id=release.id;event.lifecycle='published';event.version+=1
        audit(db,owner.id,event.id,'demo.catalog.import',release.id,source='demo/fixtures/events.json',catalog_only=True,verified_outcomes=False)
        added+=1
    return added

def main():
    settings=Settings()
    if settings.app_env!='development':raise SystemExit('Development only')
    engine,factory=database(settings.database_url.get_secret_value())
    with unit_of_work(factory) as db:
        assert db.execute(text('select current_database()')).scalar()=='aroundyou'
        count=import_examples(db,json.loads(SOURCE.read_text(encoding='utf-8')))
    print(f'Imported {count} Hazaribagh catalog examples; Canary Hill excluded. Existing records preserved.')
    engine.dispose()
if __name__=='__main__':main()
