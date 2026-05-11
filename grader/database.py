import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "grading_history.db"


def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT    NOT NULL,
                filename    TEXT    NOT NULL,
                subject     TEXT    NOT NULL,
                score       INTEGER,
                grade       TEXT,
                weak_points TEXT,
                full_result TEXT    NOT NULL
            )
        """)


def save_result(filename: str, subject: str, result: dict):
    init_db()
    with _conn() as con:
        con.execute(
            """INSERT INTO history
               (created_at, filename, subject, score, grade, weak_points, full_result)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                filename,
                subject,
                result.get("score"),
                result.get("grade"),
                json.dumps(result.get("weak_points", []), ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
            ),
        )


def get_history(limit: int = 100) -> list[dict]:
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM history ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_record(record_id: int):
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM history WHERE id = ?", (record_id,))


def clear_history():
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM history")
