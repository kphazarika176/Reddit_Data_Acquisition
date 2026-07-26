import sqlite3
from src.database import DatabaseManager
from src.extractors.apify_extractor import (
    ApifyExtractor,
    normalize_apify_post,
    normalize_apify_comment
)
from src.config import APIFY_API_TOKEN, APIFY_ACTOR_ID
from src.logger import get_logger

logger = get_logger(__name__)


class ApifyIngestionPipeline:
    """Ingestion Pipeline: Apify Actor -> Raw Reddit Data -> SQLite (posts + comments)"""

    def __init__(self):
        self.db = DatabaseManager()
        self.extractor = ApifyExtractor(
            api_token=APIFY_API_TOKEN,
            actor_id=APIFY_ACTOR_ID
        )

    def run_full_ingestion(self, subreddit: str = "news", limit: int = 10):
        logger.info("Starting full Apify ingestion pipeline (single run)...")

        posts, comments = self.extractor.fetch_subreddit_data(
            subreddit=subreddit,
            limit=limit
        )

        post_count = 0
        comment_count = 0

        # Store posts
        if posts:
            for item in posts:
                try:
                    post_data = normalize_apify_post(item)

                    if self.db.insert_post(post_data):
                        post_count += 1
                        logger.info(
                            f"Inserted post: {post_data['post_id']} - "
                            f"{post_data['title'][:50]}..."
                        )
                    else:
                        logger.info(
                            f"Post {post_data['post_id']} already exists. Skipping."
                        )

                except (sqlite3.Error, KeyError, TypeError, ValueError) as e:
                    logger.error(f"Error inserting post: {e}")

        else:
            logger.warning("No posts fetched from Apify.")

        # Store comments
        if comments:
            for item in comments:
                try:
                    comment_data = normalize_apify_comment(item)

                    if self.db.insert_comment(comment_data):
                        comment_count += 1

                except (sqlite3.Error, KeyError, TypeError, ValueError) as e:
                    logger.error(f"Error inserting comment: {e}")

        else:
            logger.warning("No comments fetched from Apify.")

        logger.info(
            f"Full ingestion complete. Posts: {post_count}, Comments: {comment_count}"
        )

        return post_count, comment_count
