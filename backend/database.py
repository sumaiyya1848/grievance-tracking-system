import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "grievances.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS grievances (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    description      TEXT NOT NULL,
    complainant_name TEXT NOT NULL,
    department       TEXT,
    priority         TEXT NOT NULL DEFAULT 'medium'
                     CHECK (priority IN ('low', 'medium', 'high')),
    status           TEXT NOT NULL DEFAULT 'open'
                     CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    due_date         TEXT,
    last_reminded_at TEXT
);

CREATE TABLE IF NOT EXISTS grievance_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    grievance_id INTEGER NOT NULL,
    action       TEXT NOT NULL,
    timestamp    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (grievance_id) REFERENCES grievances (id)
);

CREATE TABLE IF NOT EXISTS followups (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    grievance_id INTEGER NOT NULL,
    note         TEXT NOT NULL,
    remind_at    TEXT NOT NULL,
    done         INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (grievance_id) REFERENCES grievances (id)
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_grievances_status ON grievances (status);
CREATE INDEX IF NOT EXISTS idx_grievances_due_date ON grievances (due_date);
CREATE INDEX IF NOT EXISTS idx_history_grievance ON grievance_history (grievance_id);
CREATE INDEX IF NOT EXISTS idx_followups_grievance ON followups (grievance_id);
CREATE INDEX IF NOT EXISTS idx_followups_remind ON followups (done, remind_at);
"""


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        columns = [
            row["name"]
            for row in conn.execute("PRAGMA table_info(grievances)")
        ]
        if "updated_at" not in columns:
            conn.execute("ALTER TABLE grievances ADD COLUMN updated_at TEXT")
        if "escalation_level" not in columns:
            conn.execute(
                "ALTER TABLE grievances "
                "ADD COLUMN escalation_level INTEGER NOT NULL DEFAULT 0"
            )
        followup_columns = [
            row["name"]
            for row in conn.execute("PRAGMA table_info(followups)")
        ]
        if "notified" not in followup_columns:
            conn.execute(
                "ALTER TABLE followups "
                "ADD COLUMN notified INTEGER NOT NULL DEFAULT 0"
            )    
