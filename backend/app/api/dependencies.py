from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.access.authentication import authenticate
from app.api.errors import DomainError

bearer=HTTPBearer(auto_error=False)

def session(request: Request):
    with request.app.state.session_factory() as db:
        with db.begin():
            yield db

def identity(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(session, scope="function")):
    if not credentials or credentials.scheme.lower()!="bearer":
        raise DomainError("unauthenticated","Valid bearer token required",401)
    return authenticate(db,request.app.state.settings,credentials.credentials)
