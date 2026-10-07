"""Transactional labels and immutable experiment snapshots, independent of the UI."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3


def now():
    return datetime.now(timezone.utc).isoformat()


class ReviewStore:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / 'review.sqlite3'
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS commits (
                    hash TEXT PRIMARY KEY, subject TEXT, body TEXT, files TEXT, date TEXT,
                    candidate INTEGER NOT NULL, matches TEXT, score REAL);
                CREATE TABLE IF NOT EXISTS labels (
                    hash TEXT, role TEXT, label TEXT, note TEXT, updated TEXT,
                    PRIMARY KEY(hash, role));
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, hash TEXT, role TEXT, label TEXT, note TEXT,
                    updated TEXT);
                CREATE INDEX IF NOT EXISTS candidates ON commits(candidate);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, key, default=None):
        with self.connect() as db:
            row = db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row['value']) if row else default

    def put(self, key, value):
        with self.connect() as db:
            self.set_meta(db, key, value)

    @staticmethod
    def set_meta(db, key, value):
        db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',
                   (key, json.dumps(value, ensure_ascii=False)))

    def records(self, candidate=None):
        with self.connect() as db:
            if candidate is None:
                rows = db.execute('SELECT * FROM commits ORDER BY hash').fetchall()
            else:
                rows = db.execute('SELECT * FROM commits WHERE candidate=? ORDER BY hash',
                                  (int(candidate),)).fetchall()
        return [dict(row) for row in rows]

    def record(self, commit_hash):
        with self.connect() as db:
            row = db.execute('SELECT * FROM commits WHERE hash=?', (commit_hash,)).fetchone()
        if row is None:
            raise ValueError('不存在的 commit')
        return dict(row)

    def labels(self, role):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM labels WHERE role=? ORDER BY updated,hash',
                              (role,)).fetchall()
        return {row['hash']: dict(row) for row in rows}

    def label(self, commit_hash, role, label, note=''):
        if role not in ('train', 'validation', 'audit') or label not in ('related', 'unrelated', 'uncertain'):
            raise ValueError('无效的标注类别')
        self.record(commit_hash)
        timestamp = now()
        values = (commit_hash, role, label, str(note)[:4000], timestamp)
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO labels VALUES (?,?,?,?,?)', values)
            db.execute('INSERT INTO events(hash,role,label,note,updated) VALUES (?,?,?,?,?)', values)

    def scores(self, scores):
        with self.connect() as db:
            db.executemany('UPDATE commits SET score=? WHERE hash=?',
                           ((float(score), h) for h, score in scores.items()))

    def events(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM events ORDER BY id')]
