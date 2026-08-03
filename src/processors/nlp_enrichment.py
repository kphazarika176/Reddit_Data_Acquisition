import re
import html
from collections import Counter
from typing import Dict, Any, List, Tuple
from src.database import DatabaseManager
from src.logger import get_logger

logger = get_logger(__name__)

# Try importing VADER Sentiment Analysis
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    vader_analyzer = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
except ImportError:
    vader_analyzer = None
    VADER_AVAILABLE = False
    logger.warning("vaderSentiment module not found. Falling back to rule-based sentiment analyzer.")


ENGLISH_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "http", "https", "com", "reddit", "submitted", "link"
}

# Lightweight fallback lexicon if VADER is unavailable
POSITIVE_WORDS = {"good", "great", "excellent", "awesome", "positive", "love", "like", "best", "happy", "success", "win", "support", "trust", "truth", "benefit", "safe"}
NEGATIVE_WORDS = {"bad", "worst", "terrible", "horrible", "negative", "hate", "dislike", "fail", "failure", "sad", "fraud", "scam", "danger", "fake", "die", "kill", "crime", "illegal"}


class NLPEnricher:
    """Enriches Reddit posts and comments with Sentiment Analysis & Keyword/Entity Extraction."""

    @staticmethod
    def analyze_sentiment(text: str) -> Tuple[float, str]:
        """Calculates compound sentiment score [-1.0 to 1.0] and assigns label."""
        if not text:
            return 0.0, "neutral"

        clean_text = html.unescape(str(text)).strip()

        if VADER_AVAILABLE and vader_analyzer:
            scores = vader_analyzer.polarity_scores(clean_text)
            compound = round(scores["compound"], 4)
        else:
            # Fallback simple rule-based sentiment
            tokens = re.findall(r'\w+', clean_text.lower())
            pos_count = sum(1 for t in tokens if t in POSITIVE_WORDS)
            neg_count = sum(1 for t in tokens if t in NEGATIVE_WORDS)
            total = pos_count + neg_count
            if total == 0:
                compound = 0.0
            else:
                compound = round((pos_count - neg_count) / total, 4)

        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"

        return compound, label

    @staticmethod
    def extract_keywords_and_entities(text: str, max_keywords: int = 7) -> str:
        """Extracts top keywords and capitalized proper entities from text."""
        if not text:
            return ""

        clean_text = html.unescape(str(text)).strip()

        # 1. Extract proper noun entities (Capitalized words/phrases not at start of sentence)
        entities = set(re.findall(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b', clean_text))
        filtered_entities = {
            e for e in entities
            if e.lower() not in ENGLISH_STOPWORDS and len(e) > 2
        }

        # 2. Tokenize and filter frequency-based keywords
        words = re.findall(r'\b[a-zA-Z]{3,}\b', clean_text.lower())
        meaningful_words = [w for w in words if w not in ENGLISH_STOPWORDS]

        counts = Counter(meaningful_words)
        top_words = [w for w, _ in counts.most_common(max_keywords)]

        # Combine entities and top keywords
        combined = list(filtered_entities)[:4] + [w for w in top_words if w not in [e.lower() for e in filtered_entities]]
        return ", ".join(combined[:max_keywords])

    def analyze_document(self, text: str) -> Dict[str, Any]:
        """Performs full NLP analysis on a single text string."""
        sentiment_score, sentiment_label = self.analyze_sentiment(text)
        keywords = self.extract_keywords_and_entities(text)

        return {
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "keywords": keywords
        }

    def enrich_database(self, db: DatabaseManager = None) -> Dict[str, int]:
        """Runs NLP analysis on all posts and comments in SQLite database."""
        close_db_on_finish = False
        if db is None:
            db = DatabaseManager()
            close_db_on_finish = True

        logger.info("Starting NLP enrichment pass over posts and comments...")

        posts = db.get_all_posts()
        comments = db.get_latest_comments(1000000)

        enriched_posts = 0
        enriched_comments = 0

        # Enrich posts
        for post in posts:
            post_id = post["post_id"]
            combined_text = f"{post.get('title', '')} {post.get('body', '')}"
            nlp_result = self.analyze_document(combined_text)

            db.update_post_nlp(
                post_id=post_id,
                sentiment_score=nlp_result["sentiment_score"],
                sentiment_label=nlp_result["sentiment_label"],
                keywords=nlp_result["keywords"]
            )
            enriched_posts += 1

        # Enrich comments
        for comment in comments:
            comment_id = comment["comment_id"]
            body_text = comment.get("body", "")
            nlp_result = self.analyze_document(body_text)

            db.update_comment_nlp(
                comment_id=comment_id,
                sentiment_score=nlp_result["sentiment_score"],
                sentiment_label=nlp_result["sentiment_label"],
                keywords=nlp_result["keywords"]
            )
            enriched_comments += 1

        logger.info(
            f"NLP enrichment complete. "
            f"Enriched {enriched_posts} posts and {enriched_comments} comments."
        )

        if close_db_on_finish:
            db.close()

        return {
            "posts_enriched": enriched_posts,
            "comments_enriched": enriched_comments
        }
