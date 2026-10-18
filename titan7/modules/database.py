"""Database stub module."""

import sqlite3
import os


class Database:
    def __init__(self, path=None):
        self.path = path or os.path.join(os.path.dirname(__file__), "soundscape.db")
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.path)
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()


db = Database()


def init_db():
    conn = db.connect()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS dispatches (id INTEGER PRIMARY KEY, status TEXT, reason TEXT)"
    )
    conn.commit()
    conn.close()


init_db()
