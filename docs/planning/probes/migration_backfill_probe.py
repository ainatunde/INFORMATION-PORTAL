"""Probe: does migration 002's backfill produce a chain the runtime verifier accepts?"""
import os, sys, sqlite3, subprocess, tempfile, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

work = Path(__file__).resolve().parent / "work"
os.chdir(work)
db = Path(tempfile.mkdtemp()) / "populated.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db}"
os.environ["ENVIRONMENT"] = "test"
os.environ["OBJECT_STORE_PATH"] = tempfile.mkdtemp()

def alembic(*args):
    r = subprocess.run([str(work.parent / "venv/bin/alembic"), *args],
                       capture_output=True, text=True, cwd=work,
                       env={**os.environ, "DATABASE_URL": os.environ["DATABASE_URL"]})
    return r.returncode, (r.stdout + r.stderr)[-400:]

rc, out = alembic("upgrade", "001")
print(f"upgrade 001 -> rc={rc}")
if rc: print(out); sys.exit(1)

# Insert two pre-002 snapshots the way the old schema held them (no chain columns).
base = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
con = sqlite3.connect(db)
cols = [r[1] for r in con.execute("PRAGMA table_info(content_snapshots)")]
print(f"pre-002 columns: {cols}")
cs = [r[1] for r in con.execute("PRAGMA table_info(sources)")]
notnull = {r[1] for r in con.execute("PRAGMA table_info(sources)") if r[3] and r[1] != 'id'}
vals = {"id": "src-mig"}
for c in cs:
    if c in vals: continue
    if c in notnull:
        vals[c] = 1 if c.startswith("is_") or "count" in c else "probe"
ks = ",".join(vals); qs = ",".join("?" * len(vals))
con.execute(f"INSERT INTO sources ({ks}) VALUES ({qs})", tuple(vals.values()))
for i in range(2):
    ts = (base + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M:%S")
    con.execute(
        "INSERT INTO content_snapshots (id, source_id, content_sha256, storage_pointer, byte_size, retrieved_at, title, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (f"snap-{i}", "src-mig", f"{i:064x}", f"snapshots/src-mig/{i:064x}.bin", 100 + i, ts, f"legacy doc {i}", ts))
con.commit(); con.close()
print("inserted 2 legacy snapshots")

rc, out = alembic("upgrade", "002")
print(f"upgrade 002 -> rc={rc}")
if rc: print(out); sys.exit(1)

con = sqlite3.connect(db)
rows = con.execute("SELECT id, chain_index, prev_hash, retrieved_at FROM content_snapshots ORDER BY chain_index").fetchall()
con.close()
print("\nafter backfill:")
for r in rows: print(f"  {r[0]}  chain_index={r[1]}  prev_hash={str(r[2])[:16]}...  retrieved_at={r[3]!r}")

# Now verify with the RUNTIME validator, as a real caller would.
sys.path.insert(0, str(work))
from app.pipeline.hash_chain import HashChainValidator
class S:
    def __init__(self, i, ci, ph, ts, sha, size):
        self.id, self.chain_index, self.prev_hash = i, ci, ph
        self.retrieved_at, self.content_sha256, self.byte_size = ts, sha, size
    storage_pointer = ""
con = sqlite3.connect(db)
det = con.execute("SELECT id, chain_index, prev_hash, retrieved_at, content_sha256, byte_size "
                  "FROM content_snapshots ORDER BY chain_index").fetchall()
con.close()
snaps = [S(d[0], d[1], d[2], datetime.fromisoformat(d[3]) if isinstance(d[3], str) else d[3], d[4], d[5]) for d in det]
ok, err = HashChainValidator.verify_chain(snaps)
print(f"\nRUNTIME verify_chain on migrated data: ok={ok} err={err!r}")
print("VERDICT:", "PASS - backfill is verifier-consistent" if ok
      else "FAIL - migrated history does not verify")
