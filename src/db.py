from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Feed:
    id: int
    url: str
    paused: bool
    created_at: str


class Database:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                paused INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id INTEGER NOT NULL,
                entry_uid TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(feed_id, entry_uid),
                FOREIGN KEY(feed_id) REFERENCES feeds(id)
            )
            """
        )
        self.conn.commit()

    def add_feed(self, url: str) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO feeds (url, paused, created_at) VALUES (?, 0, ?)",
            (url, _utc_now_iso()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_feeds(self) -> list[Feed]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT id, url, paused, created_at FROM feeds ORDER BY id ASC"
        ).fetchall()
        return [
            Feed(
                id=int(r["id"]),
                url=str(r["url"]),
                paused=bool(r["paused"]),
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]

    def remove_feed(self, feed_id: int) -> bool:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
        changed = cur.rowcount > 0
        self.conn.commit()
        return changed

    def set_paused(self, feed_id: int, paused: bool) -> bool:
        cur = self.conn.cursor()
        cur.execute("UPDATE feeds SET paused = ? WHERE id = ?", (1 if paused else 0, feed_id))
        changed = cur.rowcount > 0
        self.conn.commit()
        return changed

    def active_feeds(self) -> list[Feed]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT id, url, paused, created_at FROM feeds WHERE paused = 0 ORDER BY id ASC"
        ).fetchall()
        return [
            Feed(
                id=int(r["id"]),
                url=str(r["url"]),
                paused=bool(r["paused"]),
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]

    def seen_entry(self, feed_id: int, entry_uid: str) -> bool:
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT 1 FROM entries WHERE feed_id = ? AND entry_uid = ?",
            (feed_id, entry_uid),
        ).fetchone()
        return row is not None

    def mark_entry_seen(self, feed_id: int, entry_uid: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO entries (feed_id, entry_uid, created_at) VALUES (?, ?, ?)",
            (feed_id, entry_uid, _utc_now_iso()),
        )
        self.conn.commit()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

