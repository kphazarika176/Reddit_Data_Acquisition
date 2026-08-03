import html
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.config import DB_PATH
from src.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages SQLite connection and schema for the Reddit pipeline."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        logger.info("Setting up SQLite schema...")
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS db_metadata (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS posts (
                post_id         TEXT PRIMARY KEY,
                subreddit       TEXT,
                title           TEXT,
                body            TEXT,
                author          TEXT,
                score           INTEGER,
                url             TEXT,
                created_utc     TEXT,
                num_comments    INTEGER,
                sentiment_score REAL DEFAULT 0.0,
                sentiment_label TEXT DEFAULT 'neutral',
                keywords        TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS comments (
                comment_id      TEXT PRIMARY KEY,
                post_id         TEXT NOT NULL REFERENCES posts(post_id),
                parent_id       TEXT,
                body            TEXT,
                author          TEXT,
                score           INTEGER,
                depth           INTEGER,
                created_utc     TEXT,
                sentiment_score REAL DEFAULT 0.0,
                sentiment_label TEXT DEFAULT 'neutral',
                keywords        TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);

            CREATE TABLE IF NOT EXISTS qa_pairs (
                question_comment_id TEXT NOT NULL,
                answer_comment_id   TEXT NOT NULL,
                post_id             TEXT NOT NULL REFERENCES posts(post_id),
                question            TEXT,
                answer              TEXT,
                score_signal        INTEGER DEFAULT 0,
                match_type          TEXT DEFAULT 'unverified',
                verification_status TEXT DEFAULT 'unverified_best_effort',
                confidence_score    REAL DEFAULT 0.5,
                PRIMARY KEY (question_comment_id, answer_comment_id)
            );
            CREATE INDEX IF NOT EXISTS idx_qa_post ON qa_pairs(post_id);
        """)
        self.conn.commit()
        self._ensure_columns_exist()
        self.clean_existing_data()
        logger.info("SQLite schema ready.")

    def _ensure_columns_exist(self):
        """Adds missing columns dynamically if database was created with an older schema."""
        cur = self.conn.cursor()
        
        # Helper to check if a column exists in a table
        def has_col(table: str, col: str) -> bool:
            cols = [info[1] for info in cur.execute(f"PRAGMA table_info({table})").fetchall()]
            return col in cols

        # Check posts columns
        if not has_col("posts", "sentiment_score"):
            cur.execute("ALTER TABLE posts ADD COLUMN sentiment_score REAL DEFAULT 0.0")
        if not has_col("posts", "sentiment_label"):
            cur.execute("ALTER TABLE posts ADD COLUMN sentiment_label TEXT DEFAULT 'neutral'")
        if not has_col("posts", "keywords"):
            cur.execute("ALTER TABLE posts ADD COLUMN keywords TEXT DEFAULT ''")

        # Check comments columns
        if not has_col("comments", "sentiment_score"):
            cur.execute("ALTER TABLE comments ADD COLUMN sentiment_score REAL DEFAULT 0.0")
        if not has_col("comments", "sentiment_label"):
            cur.execute("ALTER TABLE comments ADD COLUMN sentiment_label TEXT DEFAULT 'neutral'")
        if not has_col("comments", "keywords"):
            cur.execute("ALTER TABLE comments ADD COLUMN keywords TEXT DEFAULT ''")

        # Check qa_pairs columns
        if not has_col("qa_pairs", "match_type"):
            cur.execute("ALTER TABLE qa_pairs ADD COLUMN match_type TEXT DEFAULT 'unverified'")
        if not has_col("qa_pairs", "verification_status"):
            cur.execute("ALTER TABLE qa_pairs ADD COLUMN verification_status TEXT DEFAULT 'unverified_best_effort'")
        if not has_col("qa_pairs", "confidence_score"):
            cur.execute("ALTER TABLE qa_pairs ADD COLUMN confidence_score REAL DEFAULT 0.5")

        self.conn.commit()

    def clean_existing_data(self, force: bool = False):
        """
        Retroactively unescapes HTML entities and cleans Reddit submission boilerplate in existing rows.
        Runs ONCE as a migration step unless force=True.
        """
        cur = self.conn.cursor()
        
        if not force:
            flag = cur.execute("SELECT value FROM db_metadata WHERE key = 'html_cleaned_v1'").fetchone()
            if flag and flag["value"] == "true":
                logger.info("Data cleaning migration 'html_cleaned_v1' already executed. Skipping per-run scan.")
                return

        logger.info("Executing full table scan for HTML cleaning & boilerplate removal...")

        # Clean posts
        posts = cur.execute("SELECT post_id, title, body FROM posts").fetchall()
        for p in posts:
            title_clean = html.unescape(p["title"] or "").strip()
            body_raw = html.unescape(p["body"] or "").strip()
            if "submitted by" in body_raw and "[link]" in body_raw:
                body_raw = body_raw.split("submitted by")[0].strip()
            if title_clean != p["title"] or body_raw != p["body"]:
                cur.execute("UPDATE posts SET title = ?, body = ? WHERE post_id = ?", (title_clean, body_raw, p["post_id"]))

        # Clean comments
        comments = cur.execute("SELECT comment_id, body FROM comments").fetchall()
        for c in comments:
            body_clean = html.unescape(c["body"] or "").strip()
            if body_clean != c["body"]:
                cur.execute("UPDATE comments SET body = ? WHERE comment_id = ?", (body_clean, c["comment_id"]))

        # Clean QA pairs
        qa_pairs = cur.execute("SELECT rowid, question, answer FROM qa_pairs").fetchall()
        for q in qa_pairs:
            q_clean = html.unescape(q["question"] or "").strip()
            a_clean = html.unescape(q["answer"] or "").strip()
            if q_clean != q["question"] or a_clean != q["answer"]:
                cur.execute("UPDATE qa_pairs SET question = ?, answer = ? WHERE rowid = ?", (q_clean, a_clean, q["rowid"]))

        # Mark migration as complete
        cur.execute("INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('html_cleaned_v1', 'true')")
        self.conn.commit()
        logger.info("Data cleaning migration complete.")

    def force_clean_existing_data(self):
        """Forces clean_existing_data to run regardless of migration flag."""
        self.clean_existing_data(force=True)

    @staticmethod
    def _iso(value) -> str:
        """Ensure created_utc is a plain ISO string before insert (sqlite3 no longer auto-adapts datetime)."""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value) if value is not None else ""

    # ---------- Inserts ----------
    def insert_post(self, post: Dict[str, Any]) -> bool:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO posts
            (post_id, subreddit, title, body, author, score, url, created_utc, num_comments, sentiment_score, sentiment_label, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post["post_id"], post["subreddit"], post["title"], post["body"],
            post["author"], post["score"], post["url"],
            self._iso(post["created_utc"]), post["num_comments"],
            post.get("sentiment_score", 0.0), post.get("sentiment_label", "neutral"), post.get("keywords", "")
        ))
        self.conn.commit()
        return cur.rowcount > 0

    def insert_comment(self, comment: Dict[str, Any]) -> bool:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO comments
            (comment_id, post_id, parent_id, body, author, score, depth, created_utc, sentiment_score, sentiment_label, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            comment["comment_id"], comment["post_id"], comment.get("parent_id"),
            comment["body"], comment["author"], comment["score"],
            comment["depth"], self._iso(comment["created_utc"]),
            comment.get("sentiment_score", 0.0), comment.get("sentiment_label", "neutral"), comment.get("keywords", "")
        ))
        self.conn.commit()
        return cur.rowcount > 0

    def insert_qa_pair(self, qa: Dict[str, Any]) -> bool:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO qa_pairs
            (question_comment_id, answer_comment_id, post_id, question, answer, score_signal, match_type, verification_status, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            qa["question_comment_id"], qa["answer_comment_id"], qa["post_id"],
            qa["question"], qa["answer"], qa.get("score_signal", 0),
            qa.get("match_type", "unverified"), qa.get("verification_status", "unverified_best_effort"),
            qa.get("confidence_score", 0.5)
        ))
        self.conn.commit()
        return cur.rowcount > 0

    # ---------- NLP Updates ----------
    def update_post_nlp(self, post_id: str, sentiment_score: float, sentiment_label: str, keywords: str):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE posts
            SET sentiment_score = ?, sentiment_label = ?, keywords = ?
            WHERE post_id = ?
        """, (sentiment_score, sentiment_label, keywords, post_id))
        self.conn.commit()

    def update_comment_nlp(self, comment_id: str, sentiment_score: float, sentiment_label: str, keywords: str):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE comments
            SET sentiment_score = ?, sentiment_label = ?, keywords = ?
            WHERE comment_id = ?
        """, (sentiment_score, sentiment_label, keywords, comment_id))
        self.conn.commit()

    # ---------- Reads ----------
    def get_all_post_ids(self) -> List[str]:
        cur = self.conn.execute("SELECT post_id FROM posts")
        return [row["post_id"] for row in cur.fetchall()]

    def get_all_posts(self) -> List[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM posts")
        return [dict(row) for row in cur.fetchall()]

    def get_posts_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        placeholders = ",".join("?" for _ in ids)
        cur = self.conn.execute(f"SELECT * FROM posts WHERE post_id IN ({placeholders})", ids)
        return [dict(row) for row in cur.fetchall()]

    def get_comments_for_post(self, post_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM comments WHERE post_id = ? ORDER BY score DESC", (post_id,)
        )
        return [dict(row) for row in cur.fetchall()]

    def get_posts_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]

    def get_comments_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]

    def get_qa_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM qa_pairs").fetchone()[0]

    def get_latest_posts(self, n: int = 3) -> List[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM posts ORDER BY rowid DESC LIMIT ?", (n,))
        return [dict(row) for row in cur.fetchall()]

    def get_latest_comments(self, n: int = 3) -> List[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM comments ORDER BY rowid DESC LIMIT ?", (n,))
        return [dict(row) for row in cur.fetchall()]

    def get_latest_qa_pairs(self, n: int = 3) -> List[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM qa_pairs ORDER BY rowid DESC LIMIT ?", (n,))
        return [dict(row) for row in cur.fetchall()]


    def drop_all_tables(self):
        self.conn.executescript("""
            DROP TABLE IF EXISTS qa_pairs;
            DROP TABLE IF EXISTS comments;
            DROP TABLE IF EXISTS posts;
        """)
        self.conn.commit()
        logger.info("All tables dropped.")

    def clear_qa_pairs(self):
        """Clears all rows from qa_pairs table so fresh Q&A pairs can be generated."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM qa_pairs")
        logger.info(f"Cleared qa_pairs table: {cur.rowcount} rows removed.")
        self.conn.commit()

    def clear_database(self):
        """Equivalent of old Mongo clear_database() — deletes rows but keeps schema."""
        cur = self.conn.cursor()
        for table in ("qa_pairs", "comments", "posts"):
            cur.execute(f"DELETE FROM {table}")
            logger.info(f"Cleared {table}: {cur.rowcount} rows removed.")
        self.conn.commit()

    def close(self):
        self.conn.close()
        