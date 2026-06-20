import sqlite3
import os
from pathlib import Path


class DatabaseManager:
    _instance = None
    _conn = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_connection()
        return cls._instance

    def _init_connection(self):
        db_dir = Path(__file__).resolve().parent.parent.parent / "data"
        db_dir.mkdir(exist_ok=True)
        db_path = db_dir / "reviews.db"

        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self):
        cursor = self._conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bad_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_no TEXT NOT NULL UNIQUE,
                stay_date TEXT NOT NULL,
                room_no TEXT NOT NULL,
                source TEXT NOT NULL,
                problem_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                responsibility TEXT NOT NULL,
                rectification_measure TEXT,
                rectification_status TEXT NOT NULL DEFAULT '待整改',
                review_result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(stay_date, room_no, source)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS special_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_name TEXT NOT NULL,
                problem_type TEXT NOT NULL,
                trigger_reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '进行中',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS topic_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                review_id INTEGER NOT NULL,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(topic_id) REFERENCES special_topics(id),
                FOREIGN KEY(review_id) REFERENCES bad_reviews(id),
                UNIQUE(topic_id, review_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS review_warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id INTEGER NOT NULL,
                warning_type TEXT NOT NULL,
                warning_reason TEXT NOT NULL,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                dismissed INTEGER DEFAULT 0,
                dismissed_at TEXT,
                dismissed_reason TEXT,
                FOREIGN KEY(review_id) REFERENCES bad_reviews(id) ON DELETE CASCADE,
                UNIQUE(review_id, warning_type)
            )
        ''')

        self._conn.commit()

    def get_connection(self):
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute_query(self, query, params=None):
        cursor = self._conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self._conn.commit()
        return cursor

    def fetch_all(self, query, params=None):
        cursor = self._conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()

    def fetch_one(self, query, params=None):
        cursor = self._conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchone()
