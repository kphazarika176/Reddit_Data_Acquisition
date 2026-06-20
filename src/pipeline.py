import uuid
from pymongo.errors import DuplicateKeyError
from src.database import DatabaseManager
from src.extractors.reddit_extractor import RedditExtractor
from src.extractors.news_extractor import NewsExtractor
from src.processors.tree_builder import CommentTreeBuilder
from src.processors.qa_detector import QADetector
from src.logger import get_logger

logger = get_logger(__name__)

class ContentPipeline:
    """End-to-End Pipeline: News RSS -> Keywords -> Reddit search -> Comments -> Comment Tree -> Q&A Pairs -> MongoDB"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.news_extractor = NewsExtractor()
        self.reddit_extractor = RedditExtractor()

    def run(self):
        logger.info("Starting Full Pipeline: News RSS -> Reddit Posts -> Comments -> Q&A Detection")
        
        # 1. Fetch latest news articles from RSS feeds
        news_articles = self.news_extractor.fetch_latest_news(limit=10)
        logger.info(f"Fetched {len(news_articles)} news articles to process.")
        
        for article in news_articles:
            # Save news article in database
            try:
                self.db.news.insert_one(article.to_dict())
                logger.info(f"Inserted News Article: {article.title[:50]}...")
            except DuplicateKeyError:
                logger.info(f"News Article '{article.title[:30]}...' already exists. Skipping.")
                continue  # Skip if already processed

            # 2. Extract keywords and search Reddit
            keywords = article.keywords
            if not keywords:
                logger.info(f"No keywords found for news article: {article.title[:30]}. Skipping.")
                continue

            # 3. Search for posts by keywords
            reddit_posts = self.reddit_extractor.search_posts_by_keywords(keywords, limit=3)
            if not reddit_posts:
                logger.info(f"No Reddit posts found for keywords: {keywords}")
                continue

            logger.info(f"Processing {len(reddit_posts)} Reddit posts for news: {article.title[:30]}...")

            for post in reddit_posts:
                # Link the post to this news article
                post.news_id = article.news_id
                
                # Store Reddit Post
                try:
                    self.db.reddit_posts.insert_one(post.to_dict())
                    logger.info(f"Inserted Reddit Post: {post.post_id} - {post.title[:50]}...")
                except DuplicateKeyError:
                    logger.info(f"Reddit Post {post.post_id} already exists. Skipping.")
                    continue

                # 4. Fetch all comments for this post
                comments = self.reddit_extractor.fetch_comments_for_post(post.post_id)
                if not comments:
                    logger.info(f"No comments found for post {post.post_id}. Skipping tree build.")
                    continue

                # Store all comments
                inserted_count = 0
                for comment in comments:
                    try:
                        self.db.reddit_comments.insert_one(comment.to_dict())
                        inserted_count += 1
                    except DuplicateKeyError:
                        pass
                logger.info(f"Inserted {inserted_count} new comments for post {post.post_id}")

                # 5. Build comment tree hierarchy (Phase 2)
                comment_tree = CommentTreeBuilder.build_tree(comments, post.post_id)

                # 6. Detect question-answer pairs (Phase 3)
                qa_pairs = QADetector.extract_qa_pairs(article.news_id, post.post_id, comment_tree)
                
                # Store detected QA pairs
                qa_inserted_count = 0
                for qa in qa_pairs:
                    try:
                        self.db.qa_pairs.insert_one(qa.to_dict())
                        qa_inserted_count += 1
                    except DuplicateKeyError:
                        pass
                if qa_inserted_count > 0:
                    logger.info(f"Inserted {qa_inserted_count} new Q&A pairs for post {post.post_id}")

        logger.info("Pipeline execution completed.")
