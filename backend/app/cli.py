"""Trusted local administration only. No network identity-picker or operational CRUD API."""
import argparse
import time
from sqlalchemy import select
from app.settings import Settings
from app.shared.database import database
from app.shared.unit_of_work import unit_of_work
from app.shared.types import uid
from app.access.models import User,EventGrant
from app.access.authentication import issue_token
from app.events.models import Event
from app.events.source_revisions import append_context
from app.shared.audit import audit
from app.shared.outbox import dispatch_one
from app.memory.worker import work_once
from app.api.errors import DomainError
import app.models

from app.access.permissions import PERMISSIONS

def provision(factory,subject,name,title,category,original_context):
    if not all(x.strip() for x in [subject,name,title,category,original_context]) or len(subject)>200 or len(name)>120 or len(title)>200 or len(category)>80:
        raise ValueError("Invalid provisioning fields")
    with unit_of_work(factory) as db:
        user=db.scalar(select(User).where(User.external_auth_subject==subject))
        if not user:
            user=User(id=uid(),external_auth_subject=subject,display_name=name);db.add(user);db.flush()
        if not user.active: raise ValueError("Inactive user")
        event=Event(id=uid(),creator_id=user.id,title=title,category=category);db.add(event);db.flush()
        for permission in PERMISSIONS:db.add(EventGrant(event_id=event.id,user_id=user.id,permission=permission,scope={}))
        db.flush();source=append_context(db,user.id,event.id,original_context,event.version)
        audit(db,user.id,event.id,"admin.provision",event.id)
        return {"event_id":event.id,"user_id":user.id,"context_revision_id":source.id}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("provision");p.add_argument("--subject",required=True);p.add_argument("--name",required=True);p.add_argument("--title",required=True);p.add_argument("--category",required=True);p.add_argument("--context",required=True)
    t=sub.add_parser("token");t.add_argument("--subject",required=True)
    w=sub.add_parser("worker");w.add_argument("--once",action="store_true")
    args=parser.parse_args();settings=Settings();engine,factory=database(settings.database_url.get_secret_value())
    try:
        if args.command=="provision":
            print(provision(factory,args.subject,args.name,args.title,args.category,args.context))
        elif args.command=="token":
            with factory() as db:
                user=db.scalar(select(User).where(User.external_auth_subject==args.subject,User.active.is_(True)))
                if not user: parser.error("Subject is not an active provisioned user")
            print(issue_token(settings,args.subject))
        else:
            while True:
                for _ in range(100):
                    if not dispatch_one(factory):break
                result=work_once(factory)
                if args.once:
                    print({"worker_result":result});break
                if result is None:time.sleep(1)
    finally:engine.dispose()

if __name__=="__main__":main()
