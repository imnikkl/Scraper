from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


def _key(name: str, phone: Optional[str]) -> str:
    base = f"{name.strip().lower()}|{(phone or '').strip()}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


class SQLiteCache:
    def __init__(self, db_path: Path, ttl_days: int):
        self.db_path = Path(db_path)
        self.ttl = timedelta(days=ttl_days)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS seen (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT,
                    seen_at TEXT NOT NULL
                )
            """)

    def is_recent(self, name: str, phone: Optional[str]) -> bool:
        k = _key(name, phone)
        cutoff = (datetime.now() - self.ttl).isoformat()
        with self._conn() as c:
            row = c.execute(
                "SELECT 1 FROM seen WHERE key = ? AND seen_at >= ?",
                (k, cutoff),
            ).fetchone()
        return row is not None

    def mark_seen(
        self, name: str, phone: Optional[str],
        seen_at: Optional[datetime] = None,
    ) -> None:
        k = _key(name, phone)
        when = (seen_at or datetime.now()).isoformat()
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO seen (key, name, phone, seen_at) "
                "VALUES (?, ?, ?, ?)",
                (k, name, phone, when),
            )

    def stats(self) -> dict[str, int]:
        cutoff = (datetime.now() - self.ttl).isoformat()
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) FROM seen").fetchone()[0]
            recent = c.execute(
                "SELECT COUNT(*) FROM seen WHERE seen_at >= ?", (cutoff,),
            ).fetchone()[0]
        return {"total": total, "recent": recent}

    def clear(self) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM seen")
