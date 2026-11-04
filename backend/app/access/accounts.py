"""Password-backed browser accounts; no email-only identity bypass."""
from datetime import timedelta,datetime
import hashlib,hmac,secrets,re
from sqlalchemy import ForeignKey,String,Integer,Boolean,DateTime,select
from sqlalchemy.orm import Mapped,mapped_column
from fastapi import APIRouter,Depends,Request,Response
from fastapi.responses import JSONResponse
from pydantic import Field,ConfigDict,field_validator
from app.shared.database import Base
from app.shared.types import uid,now
from app.memory.schemas import StrictModel
from app.access.models import User
from app.api.dependencies import session
from app.api.errors import DomainError
COOKIE='aroundyou_session'
class Credential(Base):
    __tablename__='account_credentials'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    email:Mapped[str]=mapped_column(String(254),unique=True)
    password_hash:Mapped[str]=mapped_column(String(200))
    account_kind:Mapped[str]=mapped_column(String(20))
    failures:Mapped[int]=mapped_column(Integer,default=0)
    locked_until:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
class BrowserSession(Base):
    __tablename__='browser_sessions'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    token_hash:Mapped[str]=mapped_column(String(64),unique=True)
    expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    revoked:Mapped[bool]=mapped_column(Boolean,default=False)
class Signup(StrictModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    name:str=Field(min_length=1,max_length=120)
    email:str=Field(min_length=3,max_length=254)
    password:str=Field(default='',max_length=256)
    kind:str=Field(default='personal',pattern='^(personal|sponsor)$')
    @field_validator('name')
    @classmethod
    def name_not_blank(cls,value):
        if not value.strip():raise ValueError('Name is required')
        return value.strip()
class Signin(StrictModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    email:str=Field(min_length=3,max_length=254)
    password:str=Field(default='',max_length=256)

def normalize(email):
    email=email.strip().casefold()
    if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[a-z0-9](?:[a-z0-9.-]{0,187}[a-z0-9])?\.[a-z]{2,63}",email) or '..' in email:raise DomainError('invalid_email','Enter a valid email address',422)
    return email

def hash_password(password,salt=None):
    salt=salt or secrets.token_hex(16)
    value=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1,dklen=32).hex()
    return salt+':'+value

def identity_for(db,user):
    c=db.get(Credential,user.id)
    return {'accountId':user.id,'label':user.display_name,'kind':c.account_kind if c else 'personal'}

def cookie_user(db,token):
    row=db.scalar(select(BrowserSession).where(BrowserSession.token_hash==hashlib.sha256(token.encode()).hexdigest()))
    user=db.get(User,row.user_id) if row else None
    if not row or row.revoked or row.expires_at<=now() or not user or not user.active:raise DomainError('unauthenticated','Sign in to continue',401)
    return user

def issue(db,user,response,settings):
    token=secrets.token_urlsafe(32)
    db.add(BrowserSession(user_id=user.id,token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at=now()+timedelta(hours=8)))
    response.set_cookie(COOKIE,token,max_age=28800,httponly=True,secure=settings.app_env!='development',samesite='lax',path='/')
    return {'data':{'identity':identity_for(db,user)},'meta':{}}
router=APIRouter()

def origin(request):
    if request.headers.get('origin') not in ('http://127.0.0.1:5173','http://localhost:5173'):
        raise DomainError('invalid_origin','Use the approved frontend origin',403)
@router.post('/auth/signup',status_code=201)
def signup(body:Signup,request:Request,response:Response,db=Depends(session)):
    origin(request);email=normalize(body.email)
    if not body.password:raise DomainError('passwordless_unavailable','Email verification is not configured. Set a password to activate your account; email alone cannot sign in.',422)
    if len(body.password)<12:raise DomainError('weak_password','Use at least 12 characters',422)
    if db.scalar(select(Credential).where(Credential.email==email)):raise DomainError('account_exists','An account already exists. Sign in instead.',409)
    user=User(id=uid(),external_auth_subject='account:'+uid(),display_name=body.name);db.add(user);db.flush()
    db.add(Credential(user_id=user.id,email=email,password_hash=hash_password(body.password),account_kind=body.kind));db.flush()
    from app.shared.audit import audit
    audit(db,user.id,None,'account.signup',user.id)
    return issue(db,user,response,request.app.state.settings)
@router.post('/auth/signin')
def signin(body:Signin,request:Request,response:Response,db=Depends(session)):
    origin(request);email=normalize(body.email);c=db.scalar(select(Credential).where(Credential.email==email).with_for_update())
    candidate=hash_password(body.password,c.password_hash.split(':')[0] if c else '00'*16)
    valid=bool(c and hmac.compare_digest(candidate,c.password_hash) and (not c.locked_until or c.locked_until<=now()))
    user=db.get(User,c.user_id) if c else None
    if not valid or not user or not user.active:
        if c:
            c.failures+=1
            if c.failures>=5:c.locked_until=now()+timedelta(minutes=15)
        return JSONResponse(status_code=401,content={'error':{'code':'invalid_login','message':'Email/password invalid or account temporarily locked'}})
    c.failures=0;c.locked_until=None
    return issue(db,user,response,request.app.state.settings)
@router.post('/auth/logout')
def logout(request:Request,response:Response,db=Depends(session)):
    origin(request);token=request.cookies.get(COOKIE)
    if token:
        row=db.scalar(select(BrowserSession).where(BrowserSession.token_hash==hashlib.sha256(token.encode()).hexdigest()))
        if row:row.revoked=True
    response.delete_cookie(COOKIE,path='/');return {'data':{'logged_out':True},'meta':{}}
