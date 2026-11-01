import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

def uid():
    return str(uuid4())

def now():
    return datetime.now(timezone.utc)

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
