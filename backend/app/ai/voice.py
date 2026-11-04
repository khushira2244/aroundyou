"""Private source audio and transcript runs; never an authoritative interpretation."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave
from fastapi import APIRouter,Depends,Header,Request,UploadFile,File
from sqlalchemy import select
from app.api.dependencies import identity
from app.api.errors import DomainError,missing
from app.access.authorization import require
from app.ai.models import AIRun
from app.shared.unit_of_work import unit_of_work
from app.shared.idempotency import execute_once
from app.shared.audit import audit
from app.shared.types import uid

router=APIRouter()
MAX_BYTES=10*1024*1024
MAX_SECONDS=60

def normalize_audio(raw):
    if not raw or len(raw)>MAX_BYTES:raise DomainError('invalid_audio','Audio must be nonempty and at most 10 MB.',422)
    magic=(raw.startswith((b'RIFF',b'ID3',b'OggS',b'fLaC',b'\x1aE\xdf\xa3')) or raw[4:8]==b'ftyp' or (len(raw)>1 and raw[0]==255 and raw[1]&224==224))
    if not magic:raise DomainError('invalid_audio','The uploaded content is not a supported audio container.',422)
    # Probe content, not an untrusted filename or MIME header; never invoke a shell.
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise DomainError('audio_conversion_unavailable','Install FFmpeg and ffprobe, or use manual text.',503)
    flags=subprocess.CREATE_NO_WINDOW if __import__('os').name=='nt' else 0
    with tempfile.TemporaryDirectory(prefix='aroundyou-voice-') as folder:
        source=Path(folder)/'input';dest=Path(folder)/'normalized.wav';source.write_bytes(raw)
        try:
            probe=subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_entries','format=duration,format_name','-of','json',str(source)],capture_output=True,timeout=10,creationflags=flags,check=True)
            info=json.loads(probe.stdout)['format'];duration=float(info.get('duration',0))
            formats=set(info.get('format_name','').split(','))
            if not formats.intersection({'wav','mp3','mov','mp4','m4a','matroska','webm','ogg','flac','aac'}):raise ValueError()
            # MediaRecorder WebM sometimes lacks duration; bounded decoding below still enforces it.
            if duration>MAX_SECONDS:raise DomainError('audio_too_long','Audio is limited to 60 seconds.',422)
            subprocess.run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file,pipe','-i',str(source),'-vn','-t',str(MAX_SECONDS+1),'-ac','1','-ar','24000','-c:a','pcm_s16le','-map_metadata','-1',str(dest)],capture_output=True,timeout=15,creationflags=flags,check=True)
            wav=dest.read_bytes()
            with wave.open(io.BytesIO(wav)) as audio:
                seconds=audio.getnframes()/audio.getframerate()
                if not 0<seconds<=MAX_SECONDS:raise DomainError('audio_too_long','Audio must contain at most 60 seconds of speech.',422)
            return wav,seconds
        except DomainError:raise
        except (subprocess.SubprocessError,ValueError,KeyError,OSError,wave.Error):
            raise DomainError('invalid_audio','Unreadable or unsupported audio. Upload WAV, WebM, MP3, M4A, OGG or FLAC, or enter text.',422) from None

def transcript_dto(run):
    return {'id':run.id,'status':run.status,'transcript':run.context_manifest.get('result',{}).get('transcript'), 'model':run.model_profile,'error':run.failure_code,'requires_organizer_review':True}

@router.post('/events/{event_id}/voice-transcriptions')
def transcribe(event_id:str,request:Request,audio:UploadFile=File(),user=Depends(identity),idempotency_key:str=Header()):
    adapter=request.app.state.planning_adapter
    if not getattr(adapter,'transcribe',None):raise DomainError('provider_unavailable','Real voice transcription is not configured. Manual text remains available.',503)
    raw=audio.file.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise DomainError('invalid_audio','Audio is limited to 10 MB.',422)
    sha=hashlib.sha256(raw).hexdigest();factory=request.app.state.session_factory
    with unit_of_work(factory) as db:
        event=require(db,user.id,event_id,'context:write');require(db,user.id,event_id,'source:private')
        def begin():
            run=AIRun(id=uid(),event_id=event_id,requester_id=user.id,kind='voice_transcription',status='running',source_versions={'context_revision':event.active_context_revision_id},context_manifest={'sha256':sha,'bytes':len(raw),'input_evidence_only':True},model_profile='muse-voice-transcribe-1.0')
            db.add(run);db.flush();audit(db,user.id,event_id,'voice.request',run.id);return {'id':run.id}
        result=execute_once(db,user.id,event_id,'voice.transcribe',idempotency_key,{'sha256':sha},begin)
        run=db.get(AIRun,result['id'])
        # A repeated key can only read its saved run; it never calls a paid provider again.
        if run.context_manifest.get('claimed'):return {'data':transcript_dto(run)}
        run.context_manifest={**run.context_manifest,'claimed':True}
    try:
        wav,seconds=normalize_audio(raw)
        directory=Path(request.app.state.settings.voice_directory);directory.mkdir(parents=True,exist_ok=True)
        path=directory/(result['id']+'.audio');path.write_bytes(raw)
        with unit_of_work(factory) as db:
            run=db.get(AIRun,result['id']);run.context_manifest={**run.context_manifest,'storage_key':path.name,'seconds':seconds}
        value=adapter.transcribe(wav)
        with unit_of_work(factory) as db:
            require(db,user.id,event_id,'context:write');require(db,user.id,event_id,'source:private')
            run=db.get(AIRun,result['id']);run.context_manifest={**run.context_manifest,'storage_key':path.name,'seconds':seconds,'result':value};run.status='succeeded'
            audit(db,user.id,event_id,'voice.transcribed',run.id)
            return {'data':transcript_dto(run)}
    except Exception as exc:
        code=exc.code if isinstance(exc,DomainError) else 'transcription_failed'
        with unit_of_work(factory) as db:
            run=db.get(AIRun,result['id']);run.status='failed';run.failure_code=code
        if isinstance(exc,DomainError):raise
        raise DomainError(code,'Transcription failed. No replacement text was generated. Retry explicitly or enter text.',503) from None

@router.get('/events/{event_id}/voice-transcriptions')
def transcripts(event_id:str,request:Request,user=Depends(identity)):
    with request.app.state.session_factory() as db:
        require(db,user.id,event_id,'context:write');require(db,user.id,event_id,'source:private')
        rows=db.scalars(select(AIRun).where(AIRun.event_id==event_id,AIRun.kind=='voice_transcription',AIRun.requester_id==user.id).order_by(AIRun.created_at.desc()).limit(10))
        return {'data':{'items':[transcript_dto(r) for r in rows]}}
