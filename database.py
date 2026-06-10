"""
database.py
All persistence is handled here via SQLite.

Tables
------
pdf_meta    read / favourite / tags per PDF
comments    per-PDF notes
recent      recently-opened log
page_pos    last-read page per PDF  ← new
"""

import sqlite3
import json
from contextlib import contextmanager
from typing import Generator

from config import DB_PATH


# ─── Connection helper ────────────────────────────────────────────────────────

@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ─── Schema ───────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create tables if they don't already exist."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pdf_meta (
                key     TEXT PRIMARY KEY,
                is_read INTEGER NOT NULL DEFAULT 0,
                is_fav  INTEGER NOT NULL DEFAULT 0,
                tags    TEXT    NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS comments (
                key  TEXT PRIMARY KEY,
                body TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS recent (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                key       TEXT NOT NULL,
                opened_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS page_pos (
                key       TEXT PRIMARY KEY,
                last_page INTEGER NOT NULL DEFAULT 1
            );
        """)


# ─── pdf_meta ─────────────────────────────────────────────────────────────────

def get_meta(key: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT is_read, is_fav, tags FROM pdf_meta WHERE key = ?", (key,)
        ).fetchone()
    if row:
        return {"is_read": bool(row["is_read"]),
                "is_fav":  bool(row["is_fav"]),
                "tags":    json.loads(row["tags"])}
    return {"is_read": False, "is_fav": False, "tags": []}


def _upsert_meta(key: str, **fields) -> None:
    meta = get_meta(key)
    meta.update(fields)
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO pdf_meta (key, is_read, is_fav, tags)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                is_read = excluded.is_read,
                is_fav  = excluded.is_fav,
                tags    = excluded.tags
        """, (key, int(meta["is_read"]), int(meta["is_fav"]),
              json.dumps(meta["tags"])))


def set_read(key: str, value: bool) -> None:
    _upsert_meta(key, is_read=value)


def set_fav(key: str, value: bool) -> None:
    _upsert_meta(key, is_fav=value)


def set_tags(key: str, tags: list[str]) -> None:
    _upsert_meta(key, tags=tags)


def all_meta() -> dict[str, dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT key, is_read, is_fav, tags FROM pdf_meta"
        ).fetchall()
    return {
        r["key"]: {
            "is_read": bool(r["is_read"]),
            "is_fav":  bool(r["is_fav"]),
            "tags":    json.loads(r["tags"]),
        }
        for r in rows
    }


# ─── Comments ─────────────────────────────────────────────────────────────────

def get_comment(key: str) -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT body FROM comments WHERE key = ?", (key,)
        ).fetchone()
    return row["body"] if row else ""


def save_comment(key: str, body: str) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO comments (key, body) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET body = excluded.body
        """, (key, body))


def all_comments() -> dict[str, str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, body FROM comments").fetchall()
    return {r["key"]: r["body"] for r in rows}


# ─── Recent activity ──────────────────────────────────────────────────────────

def log_recent(key: str, limit: int = 20) -> None:
    with get_conn() as conn:
        conn.execute("INSERT INTO recent (key) VALUES (?)", (key,))
        conn.execute("""
            DELETE FROM recent WHERE id NOT IN (
                SELECT id FROM recent ORDER BY id DESC LIMIT ?
            )
        """, (limit,))


def get_recent(limit: int = 20) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT key FROM recent ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    seen:   set[str]  = set()
    result: list[str] = []
    for r in rows:
        if r["key"] not in seen:
            seen.add(r["key"])
            result.append(r["key"])
    return result


# ─── Page position ────────────────────────────────────────────────────────────

def get_page_pos(key: str) -> int:
    """Return the last-read page (1-indexed).  Defaults to 1."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT last_page FROM page_pos WHERE key = ?", (key,)
        ).fetchone()
    return int(row["last_page"]) if row else 1


def save_page_pos(key: str, page: int) -> None:
    """Persist the current page (1-indexed) for a PDF."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO page_pos (key, last_page) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET last_page = excluded.last_page
        """, (key, page))
