"""Trusted local development session helper. No public identity-minting endpoint."""
from pathlib import Path
import sys,json,webbrowser
from sqlalchemy import select
from app.settings import Settings
from app.shared.database import database
from app.shared.unit_of_work import unit_of_work
from app.access.models import User
from app.access.authentication import issue_token
from app.shared.types import uid
import app.models

def main():
    settings=Settings()
    if settings.app_env!='development':raise SystemExit('Development environment required')
    engine,factory=database(settings.database_url.get_secret_value())
    with unit_of_work(factory) as db:
        user=db.scalar(select(User).where(User.external_auth_subject=='aroundyou-local-organizer'))
        if not user:
            user=User(id=uid(),external_auth_subject='aroundyou-local-organizer',display_name='AroundYou Local Organizer');db.add(user);db.flush()
        if not user.active:raise SystemExit('Development account disabled; no session issued')
    token=issue_token(settings,'aroundyou-local-organizer',minutes=120)
    target=Path(__file__).resolve().parents[1]/'.tmp'/'development-session.json';target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps({'token':token,'base_url':'http://127.0.0.1:8000'}),encoding='utf-8')
    if __import__('os').name=='nt':
        import subprocess
        identity=subprocess.check_output(['whoami'],text=True).strip()
        subprocess.run(['icacls',str(target),'/inheritance:r','/grant:r',identity+':F','SYSTEM:F'],capture_output=True,check=True)
    else:target.chmod(0o600)
    if '--no-browser' not in sys.argv:webbrowser.open('http://127.0.0.1:5173/create/1#local-session='+token)
    print('Local organizer session prepared (2 hours). No token printed. No provider calls.')
    engine.dispose()
if __name__=='__main__':main()
