from typing import List, Dict, Any
from src.database import DatabaseManager
from src.models.reddit import RedditComment
from src.processors.tree_builder import CommentTreeBuilder
from src.processors.qa_detector import QADetector
from src.logger import get_logger

logger = get_logger(__name__)


def dict_to_reddit_comment(doc: Dict[str, Any]) -> RedditComment:
    """Convert a SQLite row dictionary to a RedditComment object."""
    return RedditComment(
        comment_id=doc.get("comment_id", ""),
        post_id=doc.get("post_id", ""),
        parent_id=doc.get("parent_id"),
        author=doc.get("author", "unknown"),
        body=doc.get("body", ""),
        score=doc.get("score", 0),
        depth=doc.get("depth", 0),
        created_utc=doc.get("created_utc")
    )


class QAGenerator:
    """Process raw Reddit data from SQLite and generate Q&A pairs."""

    def __init__(self):
        self.db = DatabaseManager()

    def get_all_posts(self) -> List[Dict[str, Any]]:
        """Fetch all posts from the database."""
        return self.db.get_all_posts()

    def get_comments_for_post(self, post_id: str) -> List[RedditComment]:
        """Fetch all comments for a specific post."""
        docs = self.db.get_comments_for_post(post_id)
        return [dict_to_reddit_comment(doc) for doc in docs]

    def process_post(self, post: Dict[str, Any]) -> int:
        """Process a single post: build comment tree and detect Q&A pairs."""
        post_id = post.get("post_id")

        if not post_id:
            logger.warning("Post missing post_id, skipping")
            return 0

        logger.info(f"Processing post: {post_id} - {post.get('title', '')[:50]}...")

        # Get comments for this post
        comments = self.get_comments_for_post(post_id)

        if not comments:
            logger.info(f"No comments found for post {post_id}. Skipping.")
            return 0

        logger.info(f"Found {len(comments)} comments for post {post_id}")

        # Build comment tree
        comment_tree = CommentTreeBuilder.build_tree(comments, post_id)

        # Detect Q&A pairs
        qa_pairs = QADetector.extract_qa_pairs(post_id, comment_tree)

        # Store Q&A pairs
        qa_inserted_count = 0

        for qa in qa_pairs:
            try:
                if self.db.insert_qa_pair(qa.to_dict()):
                    qa_inserted_count += 1
            except Exception as e:
                logger.error(f"Error inserting Q&A pair: {e}")

        logger.info(
            f"Inserted {qa_inserted_count} new Q&A pairs for post {post_id}"
        )

        return qa_inserted_count

    def run(self, post_ids: List[str] = None) -> Dict[str, int]:
        """Process all posts or specific posts and generate Q&A pairs."""
        logger.info("Starting Q&A generation from raw SQLite data...")

        if post_ids:
            posts = self.db.get_posts_by_ids(post_ids)
        else:
            posts = self.get_all_posts()

        total_qa_pairs = 0
        posts_processed = 0

        for post in posts:
            qa_count = self.process_post(post)
            total_qa_pairs += qa_count
            posts_processed += 1

        logger.info(
            f"Q&A generation complete. "
            f"Processed {posts_processed} posts, "
            f"generated {total_qa_pairs} Q&A pairs"
        )

        return {
            "posts_processed": posts_processed,
            "qa_pairs_generated": total_qa_pairs
        }

    def run_for_all_posts(self) -> Dict[str, int]:
        """Process all posts in the database."""
        return self.run()


def run_qa_generation():
    """Entry point for Q&A generation."""
    generator = QAGenerator()

    print("\n====== Q&A Generation from Raw Data ======")
    print("This will process raw Reddit posts/comments and generate Q&A pairs.")

    confirm = input("Continue? (y/N): ").strip().lower()

    if confirm != "y":
        print("Cancelled.")
        return

    result = generator.run_for_all_posts()

    print("\nQ&A Generation Results:")
    print(f"  Posts processed: {result['posts_processed']}")
    print(f"  Q&A pairs generated: {result['qa_pairs_generated']}")


if __name__ == "__main__":
    run_qa_generation()