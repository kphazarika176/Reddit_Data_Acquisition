import uuid
import feedparser
from datetime import datetime
from src.models.news import NewsArticle
from src.logger import get_logger

logger = get_logger(__name__)

class NewsExtractor:
    """Fetches real news from multiple RSS feeds."""
    
    # Popular tech and general news RSS feeds
    RSS_FEEDS = [
        "https://feeds.arstechnica.com/arstechnica/index",  # Ars Technica
        "https://www.techradar.com/feeds/article",  # TechRadar
        "https://feeds.theverge.com/vergefeeds/rss/index.xml",  # The Verge
        "https://feeds.bloomberg.com/markets/news/rss.xml",  # Bloomberg
        "https://feeds.reuters.com/reuters/technologyNews",  # Reuters Tech
        "https://feeds.wired.com/wired/index",  # Wired
    ]

    def fetch_latest_news(self, limit: int = 10) -> list[NewsArticle]:
        """Fetches latest news from RSS feeds with keywords for Reddit search."""
        articles = []
        
        for feed_url in self.RSS_FEEDS:
            try:
                logger.info(f"Fetching from: {feed_url}")
                feed = feedparser.parse(feed_url)
                
                if feed.bozo:
                    logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")
                
                for entry in feed.entries[:3]:  # Take top 3 from each feed
                    try:
                        # Extract keywords from title and summary
                        title = entry.get('title', 'No title')
                        summary = entry.get('summary', '')[:200]
                        
                        keywords = self._extract_keywords(title, summary)
                        
                        published = entry.get('published_parsed')
                        published_date = datetime(*published[:6]) if published else datetime.utcnow()
                        
                        article = NewsArticle(
                            news_id=str(uuid.uuid4()),
                            title=title,
                            url=entry.get('link', ''),
                            published_date=published_date,
                            keywords=keywords
                        )
                        articles.append(article)
                        logger.info(f"Added article: {title[:60]}...")
                        
                        if len(articles) >= limit:
                            return articles
                    except Exception as e:
                        logger.warning(f"Error processing entry: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error fetching feed {feed_url}: {e}")
                continue
        
        logger.info(f"Fetched {len(articles)} real news articles from RSS feeds")
        return articles if articles else self._get_fallback_articles()

    @staticmethod
    def _extract_keywords(title: str, summary: str) -> list[str]:
        """Extract keywords from title and summary."""
        # Simple keyword extraction: split and filter common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'is', 'be', 'by', 'are', 'as', 'was', 'been', 'this', 'that', 'with', 'from', 'new', 'more'}
        
        text = (title + ' ' + summary).lower()
        words = text.split()
        keywords = [w.strip(',.!?;:') for w in words if len(w) > 3 and w.lower() not in common_words]
        
        # Return top 5 unique keywords
        return list(dict.fromkeys(keywords))[:5]

    @staticmethod
    def _get_fallback_articles() -> list[NewsArticle]:
        """Returns mock articles if RSS fetching fails."""
        logger.warning("RSS fetching failed, using fallback synthetic data")
        return [
            NewsArticle(
                news_id=str(uuid.uuid4()),
                title="AI Breakthrough in 2025: New Models Released",
                url="https://example.com/ai-news",
                published_date=datetime.utcnow(),
                keywords=["AI", "models", "technology", "machine", "learning"]
            )
        ]

