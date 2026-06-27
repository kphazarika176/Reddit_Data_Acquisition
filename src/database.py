from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from src.config import MONGO_URI, DB_NAME
from src.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """Manages MongoDB connections and enforces schema indexes."""
    
    def __init__(self):
        self.client = MongoClient(
            MONGO_URI,
            connectTimeoutMS=30000,
            socketTimeoutMS=60000,
            serverSelectionTimeoutMS=30000,
            tls=True,
            tlsAllowInvalidCertificates=True,  # Temporarily allow for testing
            tlsAllowInvalidHostnames=True,
        )
        self.db: Database = self.client[DB_NAME]
        self._setup_collections()

    def _setup_collections(self):
        """Creates unique indexes to prevent duplicate insertions."""
        logger.info("Setting up database indexes to avoid duplicates...")
        
        self.reddit_posts.create_index([("post_id", 1)], unique=True)
        self.reddit_comments.create_index([("comment_id", 1)], unique=True)
        self.qa_pairs.create_index(
            [("question_comment_id", 1), ("answer_comment_id", 1)],
            unique=True
        )
        
        logger.info("Database indexes successfully verified.")

    @property
    def reddit_posts(self) -> Collection:
        return self.db["reddit_posts"]

    @property
    def reddit_comments(self) -> Collection:
        return self.db["reddit_comments"]

    @property
    def qa_pairs(self) -> Collection:
        return self.db["qa_pairs"]

    def clear_database(self):
        """Clears all collections in the database."""
        collections = ["reddit_posts", "reddit_comments", "qa_pairs"]
        for col_name in collections:
            count = self.db[col_name].delete_many({})
            logger.info(f"Cleared {col_name}: {count.deleted_count} documents removed.")

