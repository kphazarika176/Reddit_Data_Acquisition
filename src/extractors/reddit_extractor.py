import requests
import time
import uuid
from typing import List
from datetime import datetime
from src.models.reddit import RedditPost, RedditComment
from src.logger import get_logger

logger = get_logger(__name__)

class RedditExtractor:
    """Extracts Reddit posts and comments using the free Pullpush API."""
    
    BASE_URL = "https://api.pullpush.io/reddit"
    
    # Popular subreddits to fetch trending posts from
    SUBREDDITS = [
        "technology", "programming", "science", "news", "worldnews",
        "gadgets", "IAmA", "todayilearned", "explainlikeimfive", "AskReddit"
    ]
    
    # Keywords for additional searches
    SEARCH_KEYWORDS = [
        "AI", "machine learning", "crypto", "startup", "innovation",
        "breakthrough", "discovery", "technology", "software", "hardware"
    ]

    def fetch_trending_posts(self, limit: int = 10) -> List[RedditPost]:
        """Fetch trending/hot posts from popular subreddits."""
        all_posts = []
        
        for subreddit in self.SUBREDDITS[:5]:  # Limit to 5 subreddits to avoid rate limits
            url = f"{self.BASE_URL}/search/submission/?subreddit={subreddit}&size={limit}&sort=desc"
            
            logger.info(f"Fetching trending posts from r/{subreddit}...")
            
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json().get('data', [])
                
                for item in data:
                    if len(all_posts) >= limit:
                        break
                        
                    created_utc = item.get('created_utc', 0)
                    post = RedditPost(
                        post_id=item.get('id', ''),
                        news_id="trending",  # Mark as trending, not from news
                        subreddit=item.get('subreddit', 'unknown'),
                        title=item.get('title', ''),
                        body=item.get('selftext', ''),
                        author=item.get('author', 'unknown'),
                        score=item.get('score', 0),
                        created_utc=datetime.fromtimestamp(created_utc) if created_utc else datetime.utcnow(),
                        num_comments=item.get('num_comments', 0)
                    )
                    all_posts.append(post)
                
                time.sleep(1)  # Rate limit
                
            except Exception as e:
                logger.warning(f"Error fetching from r/{subreddit}: {e}")
                continue
        
        logger.info(f"Fetched {len(all_posts)} trending posts")
        return all_posts

    def search_posts_by_keywords(self, keywords: List[str], limit: int = 5) -> List[RedditPost]:
        query = " OR ".join(keywords)
        url = f"{self.BASE_URL}/search/submission/?q={query}&size={limit}"
        
        logger.info(f"Searching Pullpush for posts matching: {query}")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json().get('data', [])
            
            posts = []
            for item in data:
                created_utc = item.get('created_utc', 0)
                posts.append(RedditPost(
                    post_id=item.get('id', ''),
                    news_id="search",  # Mark as from keyword search, not from news
                    subreddit=item.get('subreddit', 'unknown'),
                    title=item.get('title', ''),
                    body=item.get('selftext', ''),
                    author=item.get('author', 'unknown'),
                    score=item.get('score', 0),
                    created_utc=datetime.fromtimestamp(created_utc) if created_utc else datetime.utcnow(),
                    num_comments=item.get('num_comments', 0)
                ))
            
            time.sleep(1) # Rate limit
            return posts
            
        except Exception as e:
            logger.error(f"Error fetching posts from Pullpush: {e}")
            return []

    def fetch_comments_for_post(self, post_id: str) -> List[RedditComment]:
        """Fetches all comments for a given post_id using Pullpush."""
        link_id = f"t3_{post_id}"
        url = f"{self.BASE_URL}/search/comment/?link_id={link_id}&size=100"
        
        logger.info(f"Fetching comments for post {post_id}...")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json().get('data', [])
            
            comments = []
            for item in data:
                created_utc = item.get('created_utc', 0)
                parent_id = item.get('parent_id')
                if not parent_id:
                    clean_parent = None
                else:
                    clean_parent = parent_id.replace('t1_', '').replace('t3_', '')
                
                comments.append(RedditComment(
                    comment_id=item.get('id', ''),
                    post_id=post_id,
                    parent_id=clean_parent,
                    author=item.get('author', 'unknown'),
                    body=item.get('body', ''),
                    score=item.get('score', 0),
                    depth=0,
                    created_utc=datetime.fromtimestamp(created_utc) if created_utc else datetime.utcnow()
                ))
            
            time.sleep(1)
            
            if not comments:
                logger.info(f"No comments found for post {post_id}. Returning empty list.")
            
            return comments
            
        except Exception as e:
            logger.error(f"Error fetching comments: {e}")
            return []
