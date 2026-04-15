import sqlite3
import os
from datetime import datetime

class CodecDatabase:
    """SQLite-backed database for caching video codec information."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS codec_cache (
                file_path TEXT PRIMARY KEY,
                codec_name TEXT NOT NULL,
                file_mtime REAL NOT NULL,
                file_size INTEGER NOT NULL,
                cached_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def get(self, file_path):
        """Returns cached codec if file hasn't changed, otherwise None."""
        if not os.path.exists(file_path):
            self._delete(file_path)
            return None

        stat = os.stat(file_path)
        cursor = self.conn.execute(
            "SELECT codec_name, file_mtime, file_size FROM codec_cache WHERE file_path = ?",
            (file_path,)
        )
        row = cursor.fetchone()
        if row is None:
            return None

        cached_codec, cached_mtime, cached_size = row
        if cached_mtime == stat.st_mtime and cached_size == stat.st_size:
            return cached_codec
        else:
            # File changed, remove stale entry
            self._delete(file_path)
            return None

    def set(self, file_path, codec):
        """Inserts or updates a codec entry."""
        stat = os.stat(file_path)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            """INSERT OR REPLACE INTO codec_cache
               (file_path, codec_name, file_mtime, file_size, cached_at)
               VALUES (?, ?, ?, ?, ?)""",
            (file_path, codec, stat.st_mtime, stat.st_size, now)
        )
        self.conn.commit()

    def _delete(self, file_path):
        self.conn.execute("DELETE FROM codec_cache WHERE file_path = ?", (file_path,))
        self.conn.commit()

    def cleanup(self, source_dir):
        """Removes entries for files that no longer exist in source_dir."""
        cursor = self.conn.execute("SELECT file_path FROM codec_cache")
        to_delete = []
        for (file_path,) in cursor:
            if not os.path.exists(file_path):
                to_delete.append(file_path)

        if to_delete:
            self.conn.executemany(
                "DELETE FROM codec_cache WHERE file_path = ?",
                [(p,) for p in to_delete]
            )
            self.conn.commit()
            print(f"  [DB CLEANUP] Removed {len(to_delete)} stale entries")

    def close(self):
        self.conn.close()