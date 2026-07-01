import sqlite3
from pathlib import Path

def get_db_connection(db_path: str) -> sqlite3.Connection:
    """
    Establishes a connection to the SQLite database and sets journal mode to WAL.
    """
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db(db_path: str) -> None:
    """
    Initializes the jobs table in the SQLite database if it doesn't exist.
    """
    with get_db_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                word TEXT PRIMARY KEY,
                status TEXT DEFAULT 'NEW',  -- NEW, DONE, FAILED
                error TEXT                  -- Error reason
            );
        """)
        conn.commit()

def get_pending_words(db_path: str, all_words: list[str]) -> list[str]:
    """
    Inserts newly discovered words into the database with 'NEW' status,
    and returns all words that have not been successfully processed yet (status != 'DONE').
    """
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        # Insert any new words not already in jobs. Use INSERT OR IGNORE.
        conn.executemany(
            "INSERT OR IGNORE INTO jobs (word, status) VALUES (?, 'NEW')",
            [(w,) for w in all_words]
        )
        conn.commit()
        
        # Retrieve pending words (status is NEW or FAILED)
        cursor = conn.execute("SELECT word FROM jobs WHERE status != 'DONE'")
        pending = [row[0] for row in cursor.fetchall()]
        return pending

def mark_done(db_path: str, word: str) -> None:
    """
    Marks a word as successfully processed ('DONE') in the database.
    """
    with get_db_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO jobs (word, status, error) VALUES (?, 'DONE', NULL) "
            "ON CONFLICT(word) DO UPDATE SET status='DONE', error=NULL",
            (word,)
        )
        conn.commit()

def mark_failed(db_path: str, word: str, error_msg: str) -> None:
    """
    Marks a word as failed ('FAILED') and logs the error message in the database.
    """
    with get_db_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO jobs (word, status, error) VALUES (?, 'FAILED', ?) "
            "ON CONFLICT(word) DO UPDATE SET status='FAILED', error=?",
            (word, error_msg, error_msg)
        )
        conn.commit()
