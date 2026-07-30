import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with open(SCHEMA_PATH, "r") as f:
        schema = f.read()

    conn = get_connection()
    try:
        # Execute schema statements one by one so CREATE VIEW / TRIGGER lines
        # don't trip over semicolons inside the statement body.
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()

    # Load sample data only on a fresh database (no admin yet)
    conn2 = get_connection()
    try:
        row = conn2.execute("SELECT COUNT(*) FROM Users").fetchone()
        if row[0] == 0:
            import sample_data
            sample_data.load_sample_data()
    finally:
        conn2.close()
