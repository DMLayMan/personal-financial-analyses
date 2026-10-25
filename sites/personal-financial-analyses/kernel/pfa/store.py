"""A single-user transactional ledger. Financial numbers are decimal strings."""
import contextlib
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def uid(prefix):
    return prefix + "_" + uuid.uuid4().hex[:16]


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def digest(value):
    return hashlib.sha256(dump(value).encode()).hexdigest()


class Store:
    def __init__(self, path="data/pfa.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.tx() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, issuer TEXT NOT NULL,
                    payload TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS records_kind ON records(kind, issuer);
                CREATE TABLE IF NOT EXISTS audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    issuer TEXT NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, issuer TEXT NOT NULL, payload TEXT NOT NULL,
                    status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                    error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                PRAGMA user_version=1;
            """)

    @contextlib.contextmanager
    def tx(self):
        db = sqlite3.connect(str(self.path), timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=15000")
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def add(self, db, kind, issuer, payload, ident=None):
        ident = ident or uid(kind)
        db.execute("INSERT INTO records VALUES (?, ?, ?, ?, ?)",
                   (ident, kind, issuer, dump(payload), now()))
        return dict(payload, id=ident, kind=kind, issuer=issuer)

    def get(self, db, ident):
        row = db.execute("SELECT * FROM records WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise ValueError("记录不存在")
        return self.unpack(row)

    @staticmethod
    def unpack(row):
        return dict(json.loads(row["payload"]), id=row["id"], kind=row["kind"],
                    issuer=row["issuer"], created_at=row["created_at"])

    def list(self, db, kind, issuer=None):
        if issuer is None:
            rows = db.execute("SELECT * FROM records WHERE kind=? ORDER BY rowid", (kind,))
        else:
            rows = db.execute("SELECT * FROM records WHERE kind=? AND issuer=? ORDER BY rowid",
                              (kind, issuer))
        return [self.unpack(row) for row in rows]

    def log(self, db, issuer, action, payload):
        db.execute("INSERT INTO audit(issuer,action,payload,created_at) VALUES (?,?,?,?)",
                   (issuer, action, dump(payload), now()))

    def revision(self, db, issuer):
        return db.execute("SELECT COALESCE(MAX(sequence),0) FROM audit WHERE issuer=?",
                          (issuer,)).fetchone()[0]

    def history(self, db, issuer):
        return [dict(r, payload=json.loads(r["payload"])) for r in db.execute(
            "SELECT * FROM audit WHERE issuer=? ORDER BY sequence DESC", (issuer,))]

    def backup(self, destination):
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.path)) as source, sqlite3.connect(str(destination)) as target:
            source.backup(target)
        return destination
