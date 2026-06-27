from pymongo.errors import DuplicateKeyError
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
    """Ingestion Pipeline: Apify Actor -> Raw Reddit Data -> MongoDB (posts + comments)"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.extractor = ApifyExtractor(
            api_token=APIFY_API_TOKEN,
            actor_id=APIFY_ACTOR_ID
        )
    
    def run_posts_ingestion(self, subreddit: str = "news", limit: int = 10):
        """Run Apify actor to fetch posts and store raw data in reddit_posts."""
        logger.info(f"Starting Apify posts ingestion: r/{subreddit}, limit={limit}")
        
        posts = self.extractor.fetch_subreddit_posts(subreddit=subreddit, limit=limit)
        
        if not posts:
            logger.warning("No posts fetched from Apify. Check API token and actor.")
            return 0
        
        inserted_count = 0
        for item in posts:
            try:
                post_data = normalize_apify_post(item)
                self.db.reddit_posts.insert_one(post_data)
                inserted_count += 1
                logger.info(f"Inserted post: {post_data['post_id']} - {post_data['title'][:50]}...")
            except DuplicateKeyError:
                logger.info(f"Post {item.get('id')} already exists. Skipping.")
                continue
            except Exception as e:
                logger.error(f"Error inserting post: {e}")
        
        logger.info(f"Posts ingestion complete. Inserted {inserted_count} posts.")
        return inserted_count
    
    def run_comments_ingestion(self, subreddit: str = "news", limit: int = 100):
        """Run Apify actor to fetch comments and store raw data in reddit_comments."""
        logger.info(f"Starting Apify comments ingestion: r/{subreddit}, limit={limit}")
        
        comments = self.extractor.fetch_comments_for_subreddit(subreddit=subreddit, limit=limit)
        
        if not comments:
            logger.warning("No comments fetched from Apify. Check API token and actor.")
            return 0
        
        inserted_count = 0
        for item in comments:
            try:
                comment_data = normalize_apify_comment(item)
                self.db.reddit_comments.insert_one(comment_data)
                inserted_count += 1
            except DuplicateKeyError:
                logger.info(f"Comment {item.get('id')} already exists. Skipping.")
                continue
            except Exception as e:
                logger.error(f"Error inserting comment: {e}")
        
        logger.info(f"Comments ingestion complete. Inserted {inserted_count} comments.")
        return inserted_count
    
    def run_full_ingestion(self, subreddit: str = "news", limit: int = 10):
        """Run full ingestion: fetch posts AND comments in a single Apify run (more efficient)."""
        logger.info("Starting full Apify ingestion pipeline (single run)...")
        
        # Fetch both posts and comments in one go
        posts, comments = self.extractor.fetch_subreddit_data(subreddit=subreddit, limit=limit)
        
        post_count = 0
        comment_count = 0
        
        # Store posts
        if posts:
            for item in posts:
                try:
                    post_data = normalize_apify_post(item)
                    self.db.reddit_posts.insert_one(post_data)
                    post_count += 1
                    logger.info(f"Inserted post: {post_data['post_id']} - {post_data['title'][:50]}...")
                except DuplicateKeyError:
                    logger.info(f"Post {item.get('id')} already exists. Skipping.")
                    continue
                except Exception as e:
                    logger.error(f"Error inserting post: {e}")
        else:
            logger.warning("No posts fetched from Apify.")
        
        # Store comments
        if comments:
            for item in comments:
                try:
                    comment_data = normalize_apify_comment(item)
                    self.db.reddit_comments.insert_one(comment_data)
                    comment_count += 1
                except DuplicateKeyError:
                    continue
                except Exception as e:
                    logger.error(f"Error inserting comment: {e}")
        else:
            logger.warning("No comments fetched from Apify.")
        
        logger.info(f"Full ingestion complete. Posts: {post_count}, Comments: {comment_count}")
        return post_count, comment_count


def run_ingestion():
    """Entry point for Apify ingestion."""
    pipeline = ApifyIngestionPipeline()
    
    subreddit = input("Enter subreddit (default: news): ").strip() or "news"
    
    try:
        limit = int(input("Enter post limit (default: 10): ").strip() or "10")
    except ValueError:
        limit = 10
    
    return pipeline.run_full_ingestion(subreddit=subreddit, limit=limit)


if __name__ == "__main__":
    run_ingestion()