import json
import hashlib
from datetime import datetime
from .models import get_conn

PLAN_KEYWORD_LIMITS = {"free": 2, "standard": 10, "pro": None}


# ---------- users ----------

def get_or_create_user(kakao_user_key: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE kakao_user_key = ?", (kakao_user_key,)
        ).fetchone()
        if row:
            return dict(row)
        conn.execute(
            "INSERT INTO users (kakao_user_key) VALUES (?)", (kakao_user_key,)
        )
    return {"kakao_user_key": kakao_user_key, "plan": "free", "plan_expires_at": None}


def get_user_plan(kakao_user_key: str) -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT plan, plan_expires_at FROM users WHERE kakao_user_key = ?",
            (kakao_user_key,),
        ).fetchone()
        if not row:
            return "free"
        if row["plan_expires_at"]:
            expires = datetime.fromisoformat(row["plan_expires_at"])
            if expires < datetime.utcnow():
                conn.execute(
                    "UPDATE users SET plan='free' WHERE kakao_user_key=?",
                    (kakao_user_key,),
                )
                return "free"
        return row["plan"]


def set_user_plan(kakao_user_key: str, plan: str, expires_at: datetime | None = None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET plan=?, plan_expires_at=? WHERE kakao_user_key=?",
            (plan, expires_at.isoformat() if expires_at else None, kakao_user_key),
        )


# ---------- keywords ----------

def count_keywords(kakao_user_key: str) -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM keywords WHERE kakao_user_key=? AND active=1",
            (kakao_user_key,),
        ).fetchone()[0]


def keyword_limit(plan: str) -> int | None:
    return PLAN_KEYWORD_LIMITS.get(plan)


def add_keyword(
    kakao_user_key: str,
    term: str,
    exclude_words: list[str],
    exact_match: bool,
) -> dict:
    """Returns the new keyword row, or raises ValueError if limit exceeded."""
    plan = get_user_plan(kakao_user_key)
    limit = keyword_limit(plan)
    if limit is not None and count_keywords(kakao_user_key) >= limit:
        raise ValueError(f"limit:{limit}:{plan}")

    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO keywords (kakao_user_key, term, exclude_words, exact_match)
               VALUES (?, ?, ?, ?)""",
            (kakao_user_key, term, json.dumps(exclude_words, ensure_ascii=False), int(exact_match)),
        )
        return {
            "id": cur.lastrowid,
            "term": term,
            "exclude_words": exclude_words,
            "exact_match": exact_match,
        }


def list_keywords(kakao_user_key: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM keywords WHERE kakao_user_key=? AND active=1 ORDER BY id",
            (kakao_user_key,),
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["exclude_words"] = json.loads(d["exclude_words"])
        d["exact_match"] = bool(d["exact_match"])
        result.append(d)
    return result


def delete_keyword(kakao_user_key: str, keyword_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE keywords SET active=0 WHERE id=? AND kakao_user_key=?",
            (keyword_id, kakao_user_key),
        )


def all_active_keywords() -> list[dict]:
    """Return all active keywords across all users (for scheduler)."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT k.*, u.plan FROM keywords k
               JOIN users u ON k.kakao_user_key = u.kakao_user_key
               WHERE k.active=1""",
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["exclude_words"] = json.loads(d["exclude_words"])
        d["exact_match"] = bool(d["exact_match"])
        result.append(d)
    return result


# ---------- seen mentions ----------

def _url_hash(url: str, kakao_user_key: str) -> str:
    return hashlib.md5(f"{kakao_user_key}:{url}".encode()).hexdigest()


def is_seen(url: str, kakao_user_key: str) -> bool:
    h = _url_hash(url, kakao_user_key)
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM seen_mentions WHERE url_hash=?", (h,)
        ).fetchone() is not None


def mark_seen(url: str, kakao_user_key: str):
    h = _url_hash(url, kakao_user_key)
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_mentions (url_hash, kakao_user_key) VALUES (?, ?)",
            (h, kakao_user_key),
        )


def purge_old_seen(days: int = 90):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM seen_mentions WHERE seen_at < datetime('now', ?)",
            (f"-{days} days",),
        )
