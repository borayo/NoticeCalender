"""
SQLite 데이터베이스 관리 모듈.
공지사항과 마감일 정보를 저장/조회한다.
"""

import sqlite3
from datetime import date, datetime
from typing import Optional

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """DB 연결을 반환한다."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """테이블 생성 (없으면)."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notices (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id   TEXT NOT NULL,           -- config의 source id (skku, sw_college 등)
            article_no  TEXT NOT NULL,            -- 게시글 고유번호
            title       TEXT NOT NULL,
            category    TEXT DEFAULT '일반',
            url         TEXT NOT NULL,
            posted_date TEXT,                     -- 게시일 (YYYY-MM-DD)
            deadline    TEXT,                     -- 마감일 (YYYY-MM-DD), 없으면 NULL
            created_at  TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE(source_id, article_no)
        );

        CREATE INDEX IF NOT EXISTS idx_notices_deadline
            ON notices(deadline) WHERE deadline IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_notices_source
            ON notices(source_id);
    """)
    conn.close()


def upsert_notice(
    source_id: str,
    article_no: str,
    title: str,
    category: str,
    url: str,
    posted_date: Optional[str],
    deadline: Optional[date],
) -> bool:
    """
    공지사항을 저장하거나 업데이트한다.
    새로 삽입되면 True, 이미 존재하면 False를 반환.
    """
    deadline_str = deadline.isoformat() if deadline else None

    conn = get_connection()
    cursor = conn.cursor()

    # 이미 존재하는지 확인
    cursor.execute(
        "SELECT id, deadline FROM notices WHERE source_id = ? AND article_no = ?",
        (source_id, article_no),
    )
    existing = cursor.fetchone()

    if existing:
        # 마감일이 새로 발견되었으면 업데이트
        if deadline_str and not existing["deadline"]:
            cursor.execute(
                "UPDATE notices SET deadline = ? WHERE id = ?",
                (deadline_str, existing["id"]),
            )
            conn.commit()
        conn.close()
        return False

    cursor.execute(
        """INSERT INTO notices (source_id, article_no, title, category, url, posted_date, deadline)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (source_id, article_no, title, category, url, posted_date, deadline_str),
    )
    conn.commit()
    conn.close()
    return True


def get_notices_with_deadlines(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    source_id: Optional[str] = None,
) -> list[dict]:
    """마감일이 있는 공지사항을 조회한다."""
    conn = get_connection()
    query = "SELECT * FROM notices WHERE deadline IS NOT NULL"
    params = []

    if start_date:
        query += " AND deadline >= ?"
        params.append(start_date)
    if end_date:
        query += " AND deadline <= ?"
        params.append(end_date)
    if source_id:
        query += " AND source_id = ?"
        params.append(source_id)

    query += " ORDER BY deadline ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_notices(limit: int = 200) -> list[dict]:
    """최근 공지사항을 모두 조회한다."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM notices ORDER BY posted_date DESC, created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """통계 정보를 반환한다."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as cnt FROM notices").fetchone()["cnt"]
    with_deadline = conn.execute(
        "SELECT COUNT(*) as cnt FROM notices WHERE deadline IS NOT NULL"
    ).fetchone()["cnt"]

    by_source = {}
    for row in conn.execute(
        "SELECT source_id, COUNT(*) as cnt FROM notices GROUP BY source_id"
    ).fetchall():
        by_source[row["source_id"]] = row["cnt"]

    conn.close()
    return {
        "total": total,
        "with_deadline": with_deadline,
        "by_source": by_source,
    }
