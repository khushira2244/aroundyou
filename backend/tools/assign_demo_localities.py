"""Assign sourced locality centers to demo publications only; original locations retained."""
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

# Fixed locality coordinates, independent of the user's map center. Reviewed 2026-11-02.
LOCALITIES={
 'event-discovery-002':('Hurhuru',23.97859,85.36893,'https://mapcarta.com/35718856'),
 'event-discovery-003':('Matwari',23.99606,85.38113,'https://mapcarta.com/35718866'),
 'event-discovery-004':('Korra',23.99290,85.38379,'https://mapcarta.com/35718868'),
 'event-discovery-005':('Jabra',23.99605,85.38725,'https://mapcarta.com/35718874'),
 'event-discovery-006':('Khirgaon',23.98393,85.35399,'https://mapcarta.com/35718852'),
 'event-discovery-007':('Haringanj',23.98022,85.37703,'https://mapcarta.com/35718870'),
 'event-discovery-008':('Katamdag',23.97760,85.29070,'https://mapcarta.com/37713100'),
 'event-discovery-009':('Masratu',23.98251,85.32383,'https://mapcarta.com/35718836'),
 'event-discovery-010':('Lakhe',23.98918,85.38888,'https://mapcarta.com/35718876'),
 'event-discovery-011':('Kadma',23.98736,85.34534,'https://mapcarta.com/35718844'),
}
LABEL='Demo · Approximate location — venue unverified.'

def main():
    settings=Settings();assert settings.app_env=='development'
    originals={e['id']:e for e in json.loads(SOURCE.read_text(encoding='utf-8'))}
    engine,factory=database(settings.database_url.get_secret_value())
    count=0
    with unit_of_work(factory) as db:
        assert db.execute(text('select current_database()')).scalar()=='aroundyou'
        for event in db.scalars(select(Event).where(Event.id.like('event-discovery-%')).with_for_update()):
            old=db.get(Publication,event.current_publication_id)
            if event.id not in LOCALITIES or not old or not old.snapshot['event'].get('demo') or not old.snapshot.get('demo_import',{}).get('catalog_only'):continue
            name,lat,lng,source=LOCALITIES[event.id]
            declared={**deepcopy(originals[event.id]['location']),'label':name+', Hazaribagh, Jharkhand, India — '+LABEL,'confidence':'demo_approximate_locality','coordinates':{'lat':lat,'lng':lng},'source_id':source,'precise_meeting_point':None}
            if old.snapshot['event']['location']==declared:continue
            snap=deepcopy(old.snapshot);snap['event']['location']=deepcopy(declared)
            snap['demo_import'].update(original_location=deepcopy(originals[event.id]['location']),map_position=LABEL,locality_source=source,locality_reviewed='2026-11-02',event_locality_assignment='Fictional demo scenario placement, not an actual event at this locality')
            release=Publication(id=uid(),event_id=event.id,sequence=old.sequence+1,finalization_id=old.finalization_id,plan_id=old.plan_id,setup_revision_id=old.setup_revision_id,snapshot=snap,digest=digest(snap),visibility=old.visibility,approved_by=event.creator_id)
            db.add(release);db.flush();event.current_publication_id=release.id;event.version+=1
            audit(db,event.creator_id,event.id,'demo.locality.assigned',release.id,supersedes_publication_id=old.id,source='demo/fixtures/events.json')
            count+=1
    print(f'Assigned {count} demo-only approximate localities; original locations and prior revisions retained; real events and Canary Hill untouched.')
    engine.dispose()
if __name__=='__main__':main()
