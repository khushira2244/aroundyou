from datetime import timedelta
import jwt
from sqlalchemy import select
from app.access.models import User
from app.api.errors import DomainError
from app.shared.types import now, uid

def issue_token(settings, subject, minutes=30):
    """Trusted CLI/test helper, never a public identity-picker endpoint."""
    issued = now()
    return jwt.encode({"sub":subject,"iss":settings.auth_issuer,"aud":settings.auth_audience,"iat":issued,"nbf":issued,"exp":issued+timedelta(minutes=minutes),"jti":uid()},settings.session_secret.get_secret_value(),algorithm="HS256")

def authenticate(session, settings, token):
    try:
        claims=jwt.decode(token,settings.session_secret.get_secret_value(),algorithms=["HS256"],audience=settings.auth_audience,issuer=settings.auth_issuer,options={"require":["sub","exp","iat","nbf","jti","iss","aud"]})
        if not isinstance(claims["sub"],str) or not claims["sub"]:
            raise ValueError()
    except (jwt.PyJWTError,ValueError,TypeError):
        raise DomainError("unauthenticated","Valid bearer token required",401) from None
    user=session.scalar(select(User).where(User.external_auth_subject==claims["sub"],User.active.is_(True)))
    if not user:
        raise DomainError("unauthenticated","Valid bearer token required",401)
    return user
