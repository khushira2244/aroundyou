from sqlalchemy import select,func
from tests.test_group2 import flow
from app.events.models import Event,ContextRevision
from app.shared.models import AuditEvent


def test_owner_delete_hides_event_and_preserves_history(flow,factory,headers):
    flow.new();eid=flow.id
    forbidden=flow.client.delete('/v1/events/'+eid,headers=headers('outsider-subject',key='outsider-delete'))
    assert forbidden.status_code==404
    stale=flow.client.delete('/v1/events/'+eid,headers=flow.headers(key='stale-delete',version='0'))
    assert stale.status_code==409
    version=flow.get('').json()['data']['version']
    h=flow.headers(key='delete-once',version=str(version))
    first=flow.client.delete('/v1/events/'+eid,headers=h)
    assert first.status_code==200 and first.json()['data']['deleted']
    assert flow.client.delete('/v1/events/'+eid,headers=h).status_code==200
    assert flow.get('').status_code==404
    assert flow.client.get('/v1/events/'+eid+'/profile').status_code==404
    items=flow.client.get('/v1/me/events',headers=flow.headers()).json()['data']['items']
    assert eid not in {i['event']['id'] for i in items}
    with factory() as db:
        assert db.get(Event,eid).lifecycle=='deleted'
        assert db.scalar(select(func.count()).select_from(ContextRevision).where(ContextRevision.event_id==eid))>0
        assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.event_id==eid,AuditEvent.operation=='event.delete'))==1
