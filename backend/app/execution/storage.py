from pathlib import Path
from typing import Protocol
import hashlib,re
from app.api.errors import DomainError
class PrivateObjectStorage(Protocol):
    def put(self,key:str,data:bytes):...
    def get(self,key:str)->bytes:...
class LocalPrivateStorage:
    def __init__(self,root):
        self.root=Path(root).resolve()
        if any(x.lower() in ('public','static','dist') for x in self.root.parts):raise ValueError('Evidence storage must not be a public/static/build directory')
        self.root.mkdir(parents=True,exist_ok=True)
    def path(self,key):
        if not re.fullmatch(r'[a-f0-9]{32}',key):raise DomainError('invalid_object','Invalid object key',422)
        path=self.root/key
        if path.is_symlink() or path.resolve().parent!=self.root:raise DomainError('invalid_object','Unsafe object path',422)
        return path
    def put(self,key,data):
        # Server-generated basename; exclusive creation; never a user path or public directory.
        with self.path(key).open('xb') as f:f.write(data)
    def get(self,key):return self.path(key).read_bytes()

def inspect_bytes(kind,mime,data):
    allowed={'image':{'image/jpeg','image/png','image/webp'},'audio':{'audio/mpeg','audio/wav','audio/webm','audio/ogg'},'video':{'video/mp4','video/webm'},'document':{'application/pdf','text/plain'}}
    if mime not in allowed.get(kind,set()):raise DomainError('unsupported_media','Unsupported media type; transcription is not configured',422)
    ok={'image/jpeg':data.startswith(b'\xff\xd8\xff'),'image/png':data.startswith(b'\x89PNG\r\n\x1a\n'),'image/webp':data.startswith(b'RIFF') and data[8:12]==b'WEBP','audio/mpeg':data.startswith(b'ID3') or len(data)>1 and data[0]==255 and data[1]&224==224,'audio/wav':data.startswith(b'RIFF') and data[8:12]==b'WAVE','audio/ogg':data.startswith(b'OggS'),'audio/webm':data.startswith(b'\x1aE\xdf\xa3'),'video/webm':data.startswith(b'\x1aE\xdf\xa3'),'video/mp4':len(data)>12 and data[4:8]==b'ftyp','application/pdf':data.startswith(b'%PDF-'),'text/plain':b'\x00' not in data}
    if not data or not ok[mime]:raise DomainError('invalid_media','Media signature does not match declared type',422)
    return hashlib.sha256(data).hexdigest()
