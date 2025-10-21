from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Row
from typing import List, Optional, Dict, Any
import json
from config import DB_PATH

def get_engine() -> Engine:
    """Create a SQLAlchemy engine connected to the SQLite file."""
    return create_engine(f"sqlite:///{DB_PATH}", future=True)

def init_db():
    """
    Initialize DB by executing schema.sql with SQLite executescript(),
    which supports multiple statements in a single call.
    """
    engine = get_engine()
    with open("schema.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    # Use a SQLAlchemy connection to get the raw DB-API connection
    with engine.begin() as conn:
        # In SQLAlchemy 2.x the DB-API connection is exposed as:
        raw = conn.connection.driver_connection  # <-- DB-API sqlite3.Connection
        raw.executescript(sql)  # executes multiple statements safely

def get_or_create_user(tg_user_id: int, first_name: str = "", last_name: str = "", username: str = "") -> int:
    """Fetch existing internal user ID by Telegram user ID, or create a new record."""
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(text("SELECT id FROM users WHERE tg_user_id=:tid"), {"tid": tg_user_id}).fetchone()
        if row:
            return int(row[0])
        conn.execute(text("""
            INSERT INTO users (tg_user_id, first_name, last_name, username)
            VALUES (:tid, :fn, :ln, :un)
        """), {"tid": tg_user_id, "fn": first_name, "ln": last_name, "un": username})
        uid = conn.execute(text("SELECT last_insert_rowid()")).scalar_one()
        return int(uid)

def log_message(user_id: int, direction: str, text_: str, intent: Optional[str], conf: Optional[float]) -> int:
    """Append a message record (in/out) to the log."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO messages (user_id, direction, text, intent, confidence)
            VALUES (:uid, :dir, :tx, :it, :cf)
        """), {"uid": user_id, "dir": direction, "tx": text_, "it": intent, "cf": conf})
        mid = conn.execute(text("SELECT last_insert_rowid()")).scalar_one()
        return int(mid)

def add_feedback(user_id: int, message_id: Optional[int], rating: int, comment: str):
    """Insert a feedback record for a user/message."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO feedback (user_id, message_id, rating, comment)
            VALUES (:uid, :mid, :rt, :cm)
        """), {"uid": user_id, "mid": message_id, "rt": rating, "cm": comment})

def list_faqs() -> List[Row]:
    """Return all FAQs (id, question, answer, tags)."""
    engine = get_engine()
    with engine.begin() as conn:
        return conn.execute(text("SELECT id, question, answer, tags FROM faqs ORDER BY id")).fetchall()

def upsert_intent(name: str, patterns_json: str):
    """Insert or update an intent pattern set (JSON)."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO intents (name, patterns) VALUES (:n, :p)
            ON CONFLICT(name) DO UPDATE SET patterns=excluded.patterns
        """), {"n": name, "p": patterns_json})

def get_intents() -> List[Row]:
    """Fetch all intents with their pattern JSON."""
    engine = get_engine()
    with engine.begin() as conn:
        return conn.execute(text("SELECT name, patterns FROM intents")).fetchall()

# ---------------- Session (multi-turn) ----------------

def get_session(user_id: int) -> Dict[str, Any]:
    """Get conversation context for a user, creating a default one if missing."""
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(text("SELECT context_json FROM sessions WHERE user_id=:u"), {"u": user_id}).fetchone()
        if row:
            return json.loads(row[0])
        ctx = {"pending_intent": None, "slots": {}, "last_course": None, "last_assignment": None}
        conn.execute(text("INSERT INTO sessions (user_id, context_json) VALUES (:u, :c)"),
                     {"u": user_id, "c": json.dumps(ctx, ensure_ascii=False)})
        return ctx

def save_session(user_id: int, ctx: Dict[str, Any]):
    """Persist conversation context after changes."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO sessions (user_id, context_json, updated_at)
            VALUES (:u, :c, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET context_json=excluded.context_json, updated_at=excluded.updated_at
        """), {"u": user_id, "c": json.dumps(ctx, ensure_ascii=False)})

def reset_session(user_id: int):
    """Reset the conversation context to a clean state."""
    engine = get_engine()
    with engine.begin() as conn:
        ctx = {"pending_intent": None, "slots": {}, "last_course": None, "last_assignment": None}
        conn.execute(text("""
            INSERT INTO sessions (user_id, context_json, updated_at)
            VALUES (:u, :c, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET context_json=excluded.context_json, updated_at=excluded.updated_at
        """), {"u": user_id, "c": json.dumps(ctx, ensure_ascii=False)})

# ---------------- Business queries ----------------

def get_schedule_by_course(course_code: str) -> Optional[Dict[str, str]]:
    """Return latest schedule info for a given course code."""
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT title, details FROM schedules WHERE course_code=:c ORDER BY id DESC LIMIT 1
        """), {"c": course_code}).fetchone()
        if row:
            return {"title": row.title or "", "details": row.details or ""}
        return None

def get_deadline(course_code: str, assignment: str) -> Optional[Dict[str, str]]:
    """Return deadline info for (course_code, assignment)."""
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT due_at, submit_to FROM deadlines
            WHERE course_code=:c AND assignment=:a
            ORDER BY id DESC LIMIT 1
        """), {"c": course_code, "a": assignment}).fetchone()
        if row:
            return {"due_at": row.due_at or "", "submit_to": row.submit_to or ""}
        return None
