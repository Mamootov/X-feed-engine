import sqlite3
from pathlib import Path
from loguru import logger

def reset_and_init_db(db_path: Path):
    """Wipes existing database and creates fresh schema on each execution."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    logger.info("Clearing previous database tables...")
    cursor.execute("DROP TABLE IF EXISTS tweets")
    
    cursor.execute("""
        CREATE TABLE tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_account TEXT,
            user TEXT,
            text TEXT,
            timestamp TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    logger.success(f"Database cleanly initialized at: {db_path}")

def save_tweets_to_db(db_path: Path, tweets: list[dict]):
    """Stores all collected tweets in SQLite."""
    if not tweets:
        logger.warning("No tweets available to persist.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.executemany(
        "INSERT INTO tweets (target_account, user, text, timestamp) VALUES (?, ?, ?, ?)",
        [(t["target_account"], t["user"], t["text"], t["timestamp"]) for t in tweets]
    )
    conn.commit()
    conn.close()
    logger.success(f"Saved total of {len(tweets)} tweets to database.")