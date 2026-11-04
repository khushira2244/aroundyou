"""Run from an ordinary Windows terminal when Codex cannot access Docker's engine pipe.
Never deletes containers/volumes. Refuses existing AroundYou containers or target volumes.
No migrations or provider calls. Credentials never appear in command arguments/output.
"""
from pathlib import Path
import json,os,secrets,socket,subprocess,time
from urllib.parse import quote
from dotenv import dotenv_values,set_key

ROOT=Path(__file__).resolve().parents[1]
NAME='aroundyou-postgres-dev'
VOLUME='aroundyou-postgres-dev-data'
ROLE='aroundyou_app'


def run(args,stdin=None,check=True):
    result=subprocess.run(args,input=stdin,capture_output=True,text=True)
    if check and result.returncode:
        # Do not print Docker/SQL stderr: it can contain credentials or SQL text.
        raise RuntimeError('Command failed: '+args[0]+' '+args[1]+'; inspect Docker Desktop privately. No data was removed.')
    return result


def restrict(path):
    if os.name=='nt':
        identity=run(['whoami']).stdout.strip()
        run(['icacls',str(path),'/inheritance:r','/grant:r',identity+':F','SYSTEM:F'])
    else:path.chmod(0o600)


def main():
    print('Inspecting Docker engine...')
    version=run(['docker','version','--format','{{.Server.Version}}']).stdout.strip()
    print('Docker server:',version)
    containers=[json.loads(line) for line in run(['docker','ps','-a','--format','{{json .}}']).stdout.splitlines() if line]
    volumes=run(['docker','volume','ls','--format','{{.Name}}']).stdout.splitlines()
    print('Existing containers (names/images/ports only):')
    for c in containers:print(c.get('Names'),c.get('Image'),c.get('Ports'))
    print('Existing volume names:',', '.join(volumes) or '(none)')
    if any('aroundyou' in c.get('Names','').lower() for c in containers) or any('aroundyou' in v.lower() for v in volumes):
        raise RuntimeError('An existing AroundYou container or volume was found. STOP: inspect its data before creating, transferring or migrating anything.')
    env=ROOT/'.env'
    config=dotenv_values(env)
    from sqlalchemy.engine import make_url
    current=config.get('DATABASE_URL')
    if current:
        u=make_url(current)
        placeholder=(u.username or '').upper() in ('USER','USERNAME') or (u.password or '').upper() in ('PASSWORD','PASS')
        if not placeholder:raise RuntimeError('DATABASE_URL already has non-placeholder credentials. STOP: inspect the intended database before changing configuration.')
    port=None
    for candidate in (5432,5433,5434):
        with socket.socket() as probe:
            try:probe.bind(('127.0.0.1',candidate));port=candidate;break
            except OSError:print('Port',candidate,'occupied; leaving its service unchanged.')
    if port is None:raise RuntimeError('No free candidate PostgreSQL port. No configuration changed.')
    credential_file=ROOT/'.env.docker'
    manifest=ROOT/'.tmp'/'docker-development.json'
    backup=ROOT/'.env.before-docker'
    if credential_file.exists() or backup.exists() or manifest.exists():
        raise RuntimeError('Prior setup credentials/manifest exist. STOP for inspection; no credentials overwritten.')
    admin_password=secrets.token_urlsafe(40)
    app_password=secrets.token_hex(32)
    credential_file.touch(exist_ok=False);restrict(credential_file)
    credential_file.write_text('POSTGRES_USER=postgres\nPOSTGRES_DB=postgres\nPOSTGRES_PASSWORD='+admin_password+'\nAROUNDYOU_APP_PASSWORD='+app_password+'\n',encoding='utf-8')
    if run(['docker','image','inspect','postgres:16'],check=False).returncode:
        print('Pulling official postgres:16 image...');run(['docker','pull','postgres:16'])
    run(['docker','volume','create','--label','com.aroundyou.purpose=development',VOLUME])
    run(['docker','run','--detach','--name',NAME,'--label','com.aroundyou.purpose=development','--restart','unless-stopped',
         '--publish',f'127.0.0.1:{port}:5432','--mount','type=volume,source='+VOLUME+',target=/var/lib/postgresql/data',
         '--env-file',str(credential_file),'--health-cmd','pg_isready -U postgres -d postgres','--health-interval','5s','--health-timeout','3s','--health-retries','20','postgres:16'])
    ready=False
    for _ in range(60):
        if run(['docker','exec',NAME,'pg_isready','-U','postgres','-d','postgres'],check=False).returncode==0:ready=True;break
        time.sleep(1)
    if not ready:raise RuntimeError('New container not ready. Container and volume retained; no reset or deletion performed.')
    # Query before creating anything. Unexpected existing DB implies persistent data; never assume it is empty.
    found=run(['docker','exec',NAME,'psql','-U','postgres','-d','postgres','-Atc',"SELECT datname FROM pg_database WHERE datname='aroundyou'"]).stdout.strip()
    if found:raise RuntimeError('Existing aroundyou database found. STOP for data inspection; no migration performed.')
    sql=f"CREATE ROLE {ROLE} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{app_password}';\nCREATE DATABASE aroundyou OWNER {ROLE};\n"
    run(['docker','exec','-i',NAME,'psql','-v','ON_ERROR_STOP=1','-U','postgres','-d','postgres'],stdin=sql)
    url=f'postgresql+psycopg://{ROLE}:{quote(app_password,safe="")}@127.0.0.1:{port}/aroundyou'
    import psycopg
    with psycopg.connect(host='127.0.0.1',port=port,user=ROLE,password=app_password,dbname='aroundyou',connect_timeout=5) as db:
        database,user,version=db.execute('SELECT current_database(),current_user,version()').fetchone()
        tables=db.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'").fetchone()[0]
    if tables:raise RuntimeError('Unexpected existing application tables. STOP; no migration performed.')
    backup.touch(exist_ok=False);restrict(backup);backup.write_bytes(env.read_bytes() if env.exists() else b'')
    if not env.exists():env.touch()
    restrict(env);set_key(str(env),'DATABASE_URL',url)
    # Preserve every other existing value. AI/Modal credentials are never read out or changed.
    manifest.parent.mkdir(exist_ok=True)
    manifest.write_text(json.dumps({'container':NAME,'volume':VOLUME,'host':'127.0.0.1','port':port,'database':database,'user':user,
        'postgres_version':version,'existing_tables_before_migration':tables,'new_database_verified':True,'migrations_applied':False},indent=2)+'\n',encoding='utf-8')
    print('Created dedicated container:',NAME)
    print('Persistent volume:',VOLUME)
    print('Verified database:',database,'user:',user,'host: 127.0.0.1 port:',port)
    print('Updated backend/.env DATABASE_URL only. Credentials saved locally; no passwords printed.')
    print('STOP: return to Codex for approved migrations and application startup. No AI calls made.')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        # Whitelist only our deliberately safe exception messages.
        if isinstance(exc,RuntimeError):print('Setup stopped:',str(exc))
        else:print('Setup stopped with',type(exc).__name__,'; no secret details printed. Existing data retained.')
        raise SystemExit(1)
