import sqlite3
import json
from datetime import datetime
from pathlib import Path

from grader._client import score_to_grade

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
        # 旧库平滑迁移：补齐后加的列
        migrations = {
            "source": "TEXT",
            "batch_id": "TEXT",
            "reviewed": "INTEGER DEFAULT 0",   # 是否经教师人工复核
            "teacher_score": "INTEGER",         # 教师修正后的分数
            "teacher_comment": "TEXT",          # 教师修正后的评语
            "student_name": "TEXT",             # 学生姓名（AI 从图片识别 / 教师修正）
            "class_name": "TEXT",               # 班级（AI 从图片识别 / 教师修正）
        }
        for col, coltype in migrations.items():
            try:
                con.execute(f"ALTER TABLE history ADD COLUMN {col} {coltype}")
            except Exception:
                pass


def save_result(filename: str, subject: str, result: dict,
                source: str = "单份批改", batch_id: str = None) -> int:
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO history
               (created_at, filename, subject, source, batch_id,
                score, grade, weak_points, full_result,
                student_name, class_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                result.get("student_name", ""),
                result.get("class_name", ""),
            ),
        )
        return cur.lastrowid


def update_review(record_id: int, new_score: int, new_comment: str,
                  new_student_name: str = None, new_class_name: str = None):
    """教师人工复核：用修正后的分数/评语/姓名覆盖记录，并保留 AI 原始结果备查。

    等级由分数统一换算；首次复核时把 AI 原始评分（含姓名）存进 full_result 的
    _ai_original，方便答辩时展示「AI 原评 → 教师修正」的对比。
    姓名/班级传 None 表示不修改，沿用原值。
    """
    new_grade = score_to_grade(new_score)
    with _conn() as con:
        row = con.execute(
            "SELECT full_result, reviewed FROM history WHERE id = ?", (record_id,)
        ).fetchone()
        if row is None:
            return

        result = json.loads(row["full_result"])
        if not row["reviewed"]:
            result["_ai_original"] = {
                "score": result.get("score"),
                "grade": result.get("grade"),
                "comment": result.get("comment", ""),
                "student_name": result.get("student_name", ""),
                "class_name": result.get("class_name", ""),
            }
        result["score"] = new_score
        result["grade"] = new_grade
        result["comment"] = new_comment
        result["reviewed"] = True
        if new_student_name is not None:
            result["student_name"] = new_student_name
        if new_class_name is not None:
            result["class_name"] = new_class_name

        con.execute(
            """UPDATE history
               SET score = ?, grade = ?, reviewed = 1,
                   teacher_score = ?, teacher_comment = ?, full_result = ?,
                   student_name = ?, class_name = ?
               WHERE id = ?""",
            (new_score, new_grade, new_score, new_comment,
             json.dumps(result, ensure_ascii=False),
             result.get("student_name", ""), result.get("class_name", ""),
             record_id),
        )


def save_batch_report(batch_id: str, subject: str, report: dict, total: int):
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
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM history ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_batch_report(batch_id: str) -> dict | None:
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
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM history WHERE batch_id = ? ORDER BY created_at ASC",
            (batch_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_record(record_id: int):
    with _conn() as con:
        con.execute("DELETE FROM history WHERE id = ?", (record_id,))


def delete_batch(batch_id: str):
    with _conn() as con:
        con.execute("DELETE FROM history WHERE batch_id = ?", (batch_id,))
        con.execute("DELETE FROM batch_reports WHERE batch_id = ?", (batch_id,))


def clear_history():
    with _conn() as con:
        con.execute("DELETE FROM history")
        con.execute("DELETE FROM batch_reports")


# 模块导入时建表 / 迁移一次，避免每次读写都重复执行
init_db()
