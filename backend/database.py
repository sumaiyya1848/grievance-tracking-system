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
"""


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
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