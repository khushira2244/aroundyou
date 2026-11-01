"""Run integration tests against a disposable local PostgreSQL cluster, never .env."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import psycopg

root=Path(__file__).resolve().parents[1]
bin_dir=Path(os.environ.get("PG_BIN", "C:/Program Files/PostgreSQL/16/bin"))
cluster=root/".tmp"/"integration-postgres"
cluster.parent.mkdir(parents=True,exist_ok=True)
flags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0
if not (cluster/"PG_VERSION").exists():
    subprocess.run([str(bin_dir/"initdb"),"-D",str(cluster),"-U","aroundyou_test","--auth=trust","--encoding=UTF8","--locale=C"],check=True,creationflags=flags)
with socket.socket() as s:
    s.bind(("127.0.0.1",0));port=s.getsockname()[1]
log=(root/".tmp"/"integration-postgres.log").open("a")
server=subprocess.Popen([str(bin_dir/"postgres"),"-D",str(cluster),"-h","127.0.0.1","-p",str(port)],stdout=log,stderr=log,creationflags=flags)
try:
    connection=None
    for _ in range(90):
        if server.poll() is not None: raise RuntimeError("PostgreSQL exited; inspect .tmp/integration-postgres.log")
        try:
            connection=psycopg.connect(host="127.0.0.1",port=port,user="aroundyou_test",dbname="postgres",connect_timeout=2,autocommit=True)
            break
        except psycopg.OperationalError: time.sleep(.5)
    if not connection: raise RuntimeError("Isolated PostgreSQL connection unavailable")
    for name in ["aroundyou_group1_test","aroundyou_group1_migration_test"]:
        if not connection.execute("SELECT 1 FROM pg_database WHERE datname=%s",(name,)).fetchone(): connection.execute(f'CREATE DATABASE "{name}"')
    connection.close()
    env={**os.environ,"TEST_DATABASE_URL":f"postgresql+psycopg://aroundyou_test@127.0.0.1:{port}/aroundyou_group1_test?connect_timeout=3","TEST_MIGRATION_DATABASE_URL":f"postgresql+psycopg://aroundyou_test@127.0.0.1:{port}/aroundyou_group1_migration_test?connect_timeout=3","PYTHONPATH":str(root)}
    print("Running tests against isolated PostgreSQL (not backend/.env)",flush=True)
    result=subprocess.run([sys.executable,"-m","pytest",*sys.argv[1:]],cwd=root,env=env,capture_output=True,text=True)
    print(result.stdout,flush=True)
    print(result.stderr,flush=True)
    code=result.returncode
finally:
    subprocess.run([str(bin_dir/"pg_ctl"),"-D",str(cluster),"-m","fast","-w","stop"],stdout=log,stderr=log,creationflags=flags,timeout=60)
    if server.poll() is None: server.terminate()
    server.wait(timeout=15);log.close()
sys.exit(code)
