"""Restore declared fixture locations through new publication revisions, never rewrites."""
from copy import deepcopy
import json
from sqlalchemy import select,text
from app.settings import Settings
from app.shared.database import database
from app.shared.unit_of_work import unit_of_work
from app.shared.types import uid,digest
from app.shared.audit import audit
from app.events.models import Event
from app.publication.models import Publication
from tools.import_discovery_examples import SOURCE
import app.models

def main():
    settings=Settings();assert settings.app_env=='development'
    originals={e['id']:e for e in json.loads(SOURCE.read_text(encoding='utf-8'))}
    engine,factory=database(settings.database_url.get_secret_value())
    count=0
    with unit_of_work(factory) as db:
        assert db.execute(text('select current_database()')).scalar()=='aroundyou'
        for event in db.scalars(select(Event).where(Event.id.like('event-discovery-%')).with_for_update()):
            old=db.get(Publication,event.current_publication_id)
            if not old or not old.snapshot.get('demo_import',{}).get('catalog_only'):continue
            declared=originals[event.id]['location']
            if old.snapshot['event']['location']==declared:continue
            snap=deepcopy(old.snapshot);snap['event']['location']=deepcopy(declared)
            snap['demo_import']['map_position']='Restored original declared locality and confidence; no user-center coordinates or generated offsets'
            release=Publication(id=uid(),event_id=event.id,sequence=old.sequence+1,finalization_id=old.finalization_id,plan_id=old.plan_id,setup_revision_id=old.setup_revision_id,snapshot=snap,digest=digest(snap),visibility=old.visibility,approved_by=event.creator_id)
            db.add(release);db.flush();event.current_publication_id=release.id;event.version+=1
            audit(db,event.creator_id,event.id,'demo.location.corrected',release.id,supersedes_publication_id=old.id,source='demo/fixtures/events.json')
            count+=1
    print(f'Restored {count} declared locations; prior revisions retained. Canary Hill untouched.')
    engine.dispose()
if __name__=='__main__':main()
