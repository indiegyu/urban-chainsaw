import os
import sqlite3
from pathlib import Path

# Fly.io에서는 /app/data 볼륨에 저장, 로컬에서는 nabot/ 디렉터리에 저장
_data_dir = Path(os.environ.get("DATA_DIR", Path(__file__).parent.parent))
DB_PATH = _data_dir / "nabot.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                kakao_user_key TEXT PRIMARY KEY,
                plan           TEXT    DEFAULT 'free',
                plan_expires_at DATETIME,
                created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS keywords (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                kakao_user_key  TEXT    NOT NULL,
                term            TEXT    NOT NULL,
                exclude_words   TEXT    DEFAULT '[]',
                exact_match     INTEGER DEFAULT 1,
                active          INTEGER DEFAULT 1,
                FOREIGN KEY (kakao_user_key) REFERENCES users(kakao_user_key)
            );

            CREATE TABLE IF NOT EXISTS seen_mentions (
                url_hash        TEXT PRIMARY KEY,
                kakao_user_key  TEXT NOT NULL,
                seen_at         DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
