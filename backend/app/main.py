from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from app.settings import Settings
from app.shared.database import database
from app.api.errors import DomainError
from app.shared.types import uid
from app.access.router import router as access_router
from app.events.router import router as event_router
from app.memory.router import router as memory_router

# No auto-migration, fixture loading, provider calls or credential output on import.
def create_app(settings=None, session_factory=None, extractor=None, planning_adapter=None, evidence_storage=None):
    settings=settings or Settings()
    app=FastAPI(title="AroundYou Backend",version="0.1.0")
    if evidence_storage is None and settings.evidence_directory:
        from app.execution.storage import LocalPrivateStorage
        evidence_storage=LocalPrivateStorage(settings.evidence_directory)
    from app.execution.media import router as media_router
    app.include_router(media_router,prefix='/v1')
    app.state.evidence_storage=evidence_storage
    app.state.settings=settings
    if extractor is None and settings.modal_memory_enabled:
        if not all((settings.modal_memory_endpoint,settings.modal_memory_proxy_key,settings.modal_memory_proxy_secret)):raise ValueError('Explicit Modal memory endpoint and proxy credentials required')
        from app.memory.modal_adapter import ModalHTTPExtractor
        extractor=ModalHTTPExtractor(settings.modal_memory_endpoint,settings.modal_memory_proxy_key.get_secret_value(),settings.modal_memory_proxy_secret.get_secret_value())
    app.state.extractor=extractor
    if planning_adapter is None and settings.meta_ai_enabled and settings.meta_api_key:
        from app.ai.meta_provider import MetaProvider
        planning_adapter=MetaProvider(settings.meta_api_key.get_secret_value(),settings.meta_model_id)
    app.state.planning_adapter=planning_adapter
    if session_factory is None:
        engine,session_factory=database(settings.database_url.get_secret_value())
        app.state.engine=engine
    app.state.session_factory=session_factory

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        request.state.request_id=uid()
        result=await call_next(request)
        result.headers["X-Request-ID"]=request.state.request_id
        result.headers["Cache-Control"]="no-store"
        return result

    def error(request,code,message,status):
        return JSONResponse(status_code=status,content={"error":{"code":code,"message":message,"retryable":status==503,"request_id":getattr(request.state,"request_id",None)}})
    @app.exception_handler(DomainError)
    async def domain_error(request,exc): return error(request,exc.code,exc.message,exc.status)
    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc): return error(request,"validation_failed","Invalid request fields or required headers",422)
    @app.exception_handler(IntegrityError)
    async def integrity_error(request,exc): return error(request,"constraint_conflict","Request conflicts with stored constraints",409)

    from pydantic import ValidationError
    @app.exception_handler(ValidationError)
    async def schema_error(request,exc):return error(request,"validation_failed","Invalid domain document or incompatible references/timing",422)

    @app.get("/health")
    def health(): return {"status":"ok","group":4}
    if settings.app_env=='development':
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5173','http://localhost:5173'],allow_credentials=True,allow_methods=['GET','POST','PUT','PATCH','DELETE'],allow_headers=['Authorization','Content-Type','If-Match','Idempotency-Key'])
    from app.access.accounts import router as accounts_router
    app.include_router(accounts_router,prefix='/v1')
    app.include_router(access_router,prefix="/v1")
    app.include_router(event_router,prefix="/v1")
    app.include_router(memory_router,prefix="/v1")
    from app.api.group2 import router as group2_router
    app.include_router(group2_router,prefix="/v1")
    from app.ai.voice import router as voice_router
    app.include_router(voice_router,prefix='/v1')
    from app.api.group3 import router as group3_router
    app.include_router(group3_router,prefix="/v1")
    from app.api.group4 import router as group4_router
    app.include_router(group4_router,prefix="/v1")
    from app.api.group5 import router as group5_router
    app.include_router(group5_router,prefix="/v1")
    return app
