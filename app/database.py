import sqlite3
import os
from datetime import datetime

MAX_ENTRIES = 20

def get_db_path():
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    folder = os.path.join(appdata, "Kopirovacka")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "history.db")


class Database:
    def __init__(self, path=None):
        self.path = path or get_db_path()
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    meta TEXT DEFAULT '',
                    pinned INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def add_entry(self, type_, content, meta=""):
        """Add new entry. Pinned items are NOT removed. Returns new ID or None if duplicate."""
        with self._conn() as conn:
            # Check duplicate (last 5 entries for perf)
            cur = conn.execute(
                "SELECT id, content FROM entries ORDER BY id DESC LIMIT 5")
            for row in cur.fetchall():
                if row["content"] == content and row["type"] == type_ if hasattr(row, "__getitem__") else False:
                    return None

            # Actually check for duplicate properly
            cur2 = conn.execute(
                "SELECT id FROM entries WHERE type=? AND content=? ORDER BY id DESC LIMIT 1",
                (type_, content))
            existing = cur2.fetchone()
            if existing:
                # Move to top by updating timestamp
                now = datetime.now().isoformat()
                conn.execute("UPDATE entries SET created_at=? WHERE id=?",
                             (now, existing["id"]))
                conn.commit()
                return existing["id"]

            # Insert new
            now = datetime.now().isoformat()
            cur3 = conn.execute(
                "INSERT INTO entries (type, content, meta, pinned, created_at) VALUES (?,?,?,0,?)",
                (type_, content, meta, now))
            new_id = cur3.lastrowid
            conn.commit()

            # Enforce MAX_ENTRIES: delete oldest non-pinned if over limit
            self._enforce_limit(conn)
            return new_id

    def _enforce_limit(self, conn):
        cur = conn.execute(
            "SELECT COUNT(*) as cnt FROM entries WHERE pinned=0")
        count = cur.fetchone()["cnt"]
        if count > MAX_ENTRIES:
            excess = count - MAX_ENTRIES
            conn.execute("""
                DELETE FROM entries WHERE id IN (
                    SELECT id FROM entries WHERE pinned=0
                    ORDER BY created_at ASC LIMIT ?
                )
            """, (excess,))
            conn.commit()

    def get_entries(self, search=""):
        with self._conn() as conn:
            if search:
                like = f"%{search}%"
                cur = conn.execute("""
                    SELECT * FROM entries
                    WHERE (content LIKE ? OR meta LIKE ?)
                    ORDER BY pinned DESC, created_at DESC
                    LIMIT 20
                """, (like, like))
            else:
                cur = conn.execute("""
                    SELECT * FROM entries
                    ORDER BY pinned DESC, created_at DESC
                    LIMIT 20
                """)
            return [dict(row) for row in cur.fetchall()]

    def get_entry(self, eid):
        with self._conn() as conn:
            cur = conn.execute("SELECT * FROM entries WHERE id=?", (eid,))
            row = cur.fetchone()
            return dict(row) if row else None

    def delete_entry(self, eid):
        with self._conn() as conn:
            conn.execute("DELETE FROM entries WHERE id=?", (eid,))
            conn.commit()

    def clear_all(self):
        with self._conn() as conn:
            conn.execute("DELETE FROM entries")
            conn.commit()

    def toggle_pin(self, eid):
        with self._conn() as conn:
            cur = conn.execute("SELECT pinned FROM entries WHERE id=?", (eid,))
            row = cur.fetchone()
            if row:
                new_pin = 0 if row["pinned"] else 1
                conn.execute("UPDATE entries SET pinned=? WHERE id=?", (new_pin, eid))
                conn.commit()
