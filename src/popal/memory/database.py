"""Memory / database foundation.

Phase 0 initializes a SQLite database for future storage of:
- Command history
- User preferences
- Application information
- Settings

Only basic initialization and health check are implemented.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from popal.utils.logger import get_logger

logger = get_logger("memory.database")

_DEFAULT_DB_PATH = Path("data") / "popal.db"


class Database:
    """Minimal SQLite database wrapper for POPAL memory."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        """Create the database and required tables if they don't exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()
        logger.info("Database initialized: %s", self._db_path)

    def _create_tables(self) -> None:
        """Create the Phase 0 schema."""
        if self._conn is None:
            return
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_id TEXT NOT NULL,
                intent TEXT NOT NULL,
                target TEXT,
                source TEXT,
                success INTEGER NOT NULL,
                message TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        self._conn.commit()

    def health_check(self) -> bool:
        """Verify the database connection is alive.

        Returns:
            True if the database is accessible.
        """
        if self._conn is None:
            return False
        try:
            self._conn.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.debug("Database connection closed.")