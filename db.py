# db.py
# SQLite DB 초기화 및 CRUD
import sqlite3
import os
from datetime import date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corp_dashboard.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """테이블이 없으면 생성"""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS financial (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                corp_name   TEXT    NOT NULL,
                source      TEXT    NOT NULL,  -- 'dart' | 'pdf'
                fs_div      TEXT,              -- CFS / OFS / (null for pdf)
                year        INTEGER NOT NULL,
                item_name   TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS news (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                corp_name   TEXT    NOT NULL,
                pub_date    TEXT    NOT NULL,
                title       TEXT    NOT NULL,
                link        TEXT,
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_financial_corp ON financial(corp_name, year);
            CREATE INDEX IF NOT EXISTS idx_news_corp      ON news(corp_name);
        """)


# --------------------------------------------------
# 재무 데이터 저장 / 조회
# --------------------------------------------------
def upsert_financial(corp_name: str, source: str, fs_div: str,
                     year: int, item_name: str, amount: float):
    """같은 기업·연도·항목이 있으면 UPDATE, 없으면 INSERT"""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM financial WHERE corp_name=? AND source=? AND year=? AND item_name=? AND (fs_div=? OR fs_div IS NULL)",
            (corp_name, source, year, item_name, fs_div)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE financial SET amount=?, created_at=datetime('now','localtime') WHERE id=?",
                (amount, existing["id"])
            )
        else:
            conn.execute(
                "INSERT INTO financial (corp_name, source, fs_div, year, item_name, amount) VALUES (?,?,?,?,?,?)",
                (corp_name, source, fs_div, year, item_name, amount)
            )


def query_financial(corp_name: str, item_name: str = None, source: str = None) -> list[dict]:
    """재무 데이터 조회, 연도 오름차순"""
    sql    = "SELECT * FROM financial WHERE corp_name=?"
    params = [corp_name]
    if item_name:
        sql += " AND item_name=?";  params.append(item_name)
    if source:
        sql += " AND source=?";     params.append(source)
    sql += " ORDER BY year ASC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


# --------------------------------------------------
# 뉴스 저장 / 조회
# --------------------------------------------------
def insert_news_bulk(corp_name: str, news_list: list[dict]):
    """뉴스 리스트 일괄 저장 (기존 데이터 삭제 후 재삽입)"""
    with get_conn() as conn:
        conn.execute("DELETE FROM news WHERE corp_name=?", (corp_name,))
        conn.executemany(
            "INSERT INTO news (corp_name, pub_date, title, link) VALUES (?,?,?,?)",
            [(corp_name, str(n["작성일"]), n["제목"], n.get("링크", "")) for n in news_list]
        )


def query_news(corp_name: str) -> list[dict]:
    """뉴스 조회, 날짜 내림차순"""
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT pub_date, title, link FROM news WHERE corp_name=? ORDER BY pub_date DESC",
            (corp_name,)
        ).fetchall()]
