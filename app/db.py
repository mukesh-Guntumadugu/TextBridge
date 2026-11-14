import sqlite3
import time

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_phone TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  category TEXT,
  urgency TEXT,
  summary TEXT,
  language TEXT DEFAULT 'en',
  assigned_chw TEXT,
  created_at REAL,
  updated_at REAL
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id INTEGER REFERENCES cases(id),
  sender TEXT NOT NULL,          -- patient | chw | dashboard | system
  from_phone TEXT,
  to_phone TEXT,
  body TEXT,
  channel TEXT,                  -- twilio | dev | inbound
  sid TEXT,
  created_at REAL
);
CREATE INDEX IF NOT EXISTS idx_cases_phone ON cases(patient_phone, status);
CREATE INDEX IF NOT EXISTS idx_messages_case ON messages(case_id);
"""


def connect() -> sqlite3.Connection:
    c = sqlite3.connect(config.DB_PATH, check_same_thread=False, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


def now() -> float:
    return time.time()


def open_case_for(phone: str):
    with connect() as c:
        return c.execute(
            "SELECT * FROM cases WHERE patient_phone=? AND status='open' ORDER BY id DESC LIMIT 1",
            (phone,),
        ).fetchone()


def get_case(case_id: int):
    with connect() as c:
        return c.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()


def create_case(phone: str, triage: dict) -> int:
    t = now()
    with connect() as c:
        cur = c.execute(
            "INSERT INTO cases(patient_phone, category, urgency, summary, language, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (phone, triage["category"], triage["urgency"], triage["summary"], triage["language"], t, t),
        )
        return cur.lastrowid


def update_case(case_id: int, **fields) -> None:
    fields["updated_at"] = now()
    cols = ", ".join(f"{k}=?" for k in fields)
    with connect() as c:
        c.execute(f"UPDATE cases SET {cols} WHERE id=?", (*fields.values(), case_id))


def add_message(case_id, sender, from_phone, to_phone, body, channel, sid=None) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO messages(case_id, sender, from_phone, to_phone, body, channel, sid, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (case_id, sender, from_phone, to_phone, body, channel, sid, now()),
        )
        if case_id:
            c.execute("UPDATE cases SET updated_at=? WHERE id=?", (now(), case_id))


def list_cases(status: str | None = None):
    q = """SELECT c.*,
             (SELECT body FROM messages m WHERE m.case_id=c.id AND m.sender='patient'
              ORDER BY m.id DESC LIMIT 1) AS last_patient_message
           FROM cases c"""
    args: tuple = ()
    if status:
        q += " WHERE c.status=?"
        args = (status,)
    q += """ ORDER BY c.status='open' DESC,
             CASE c.urgency WHEN 'emergency' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
             c.updated_at DESC"""
    with connect() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def case_messages(case_id: int):
    with connect() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM messages WHERE case_id=? ORDER BY id", (case_id,)).fetchall()]


def phone_messages(phone: str, since_id: int = 0):
    """Everything sent to or from one phone (used by the dev phone simulator)."""
    with connect() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM messages WHERE (to_phone=? OR from_phone=?) AND id>? ORDER BY id",
            (phone, phone, since_id)).fetchall()]
