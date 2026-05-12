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
                source      TEXT    NOT NULL DEFAULT '单份批改',
                batch_id    TEXT,
                score       INTEGER,
                grade       TEXT,
                weak_points TEXT,
                full_result TEXT    NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS batch_reports (
                batch_id    TEXT PRIMARY KEY,
                created_at  TEXT NOT NULL,
                subject     TEXT NOT NULL,
                total       INTEGER,
                report_json TEXT NOT NULL
            )
        """)
        for col in ["source", "batch_id"]:
            try:
                con.execute(f"ALTER TABLE history ADD COLUMN {col} TEXT")
            except Exception:
                pass


def save_result(filename: str, subject: str, result: dict,
                source: str = "单份批改", batch_id: str = None):
    init_db()
    with _conn() as con:
        con.execute(
            """INSERT INTO history
               (created_at, filename, subject, source, batch_id,
                score, grade, weak_points, full_result)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                filename,
                subject,
                source,
                batch_id,
                result.get("score"),
                result.get("grade"),
                json.dumps(result.get("weak_points", []), ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
            ),
        )


def save_batch_report(batch_id: str, subject: str, report: dict, total: int):
    init_db()
    with _conn() as con:
        con.execute(
            """INSERT OR REPLACE INTO batch_reports
               (batch_id, created_at, subject, total, report_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                batch_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                subject,
                total,
                json.dumps(report, ensure_ascii=False),
            ),
        )


def get_history(limit: int = 100) -> list[dict]:
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM history ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_batch_report(batch_id: str) -> dict | None:
    init_db()
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM batch_reports WHERE batch_id = ?", (batch_id,)
        ).fetchone()
    if row:
        r = dict(row)
        r["report_json"] = json.loads(r["report_json"])
        return r
    return None


def get_batch_records(batch_id: str) -> list[dict]:
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM history WHERE batch_id = ? ORDER BY created_at ASC",
            (batch_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_record(record_id: int):
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM history WHERE id = ?", (record_id,))


def delete_batch(batch_id: str):
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM history WHERE batch_id = ?", (batch_id,))
        con.execute("DELETE FROM batch_reports WHERE batch_id = ?", (batch_id,))


def clear_history():
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM history")
        con.execute("DELETE FROM batch_reports")
