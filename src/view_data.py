import sys
from src.database import DatabaseManager
from src.logger import get_logger

logger = get_logger(__name__)


def safe_str(text: str) -> str:
    """Sanitizes strings for printing to console without encoding errors."""
    if not text:
        return ""

    encoding = sys.stdout.encoding or "utf-8"

    try:
        return text.encode(encoding, errors="ignore").decode(encoding)
    except (UnicodeError, LookupError):
        return text.encode("ascii", errors="ignore").decode("ascii")


def view_stored_data():
    db = DatabaseManager()

    print("\n" + "=" * 60)
    print("REDDIT CONTENT ACQUISITION DATABASE STATISTICS")
    print("=" * 60)

    # Database statistics
    posts_count = db.get_posts_count()
    comments_count = db.get_comments_count()
    qa_count = db.get_qa_count()

    print(f"Reddit Posts:    {posts_count}")
    print(f"Reddit Comments: {comments_count}")
    print(f"Q&A Pairs:       {qa_count}")

    print("\n" + "=" * 60)
    print("SAMPLE REDDIT POSTS (with comment count)")
    print("=" * 60)

    for post in db.get_latest_posts(3):
        title = post.get("title", "N/A")
        post_id = post.get("post_id", "N/A")
        subreddit = post.get("subreddit", "N/A")
        score = post.get("score", 0)
        num_comments = post.get("num_comments", 0)
        sentiment = post.get("sentiment_label", "neutral")
        keywords = post.get("keywords", "")

        print(f"\n[Post] {safe_str(title)[:70]}")
        print(f"   Post ID: {safe_str(post_id)} | Subreddit: r/{safe_str(subreddit)}")
        print(f"   Score: {score} | Comments: {num_comments}")
        print(f"   Sentiment: {sentiment} ({post.get('sentiment_score', 0.0)}) | Keywords: {safe_str(keywords)[:50]}")

    print("\n" + "=" * 60)
    print("SAMPLE REDDIT COMMENTS (latest 3)")
    print("=" * 60)

    for comment in db.get_latest_comments(3):
        body = comment.get("body", "N/A")
        author = comment.get("author", "N/A")
        post_id = comment.get("post_id", "N/A")
        parent_id = comment.get("parent_id", "N/A")
        score = comment.get("score", 0)
        depth = comment.get("depth", 0)
        sentiment = comment.get("sentiment_label", "neutral")
        keywords = comment.get("keywords", "")

        print(f"\n[Comment] u/{safe_str(author)}")
        print(f"   Post ID: {safe_str(post_id)} | Parent ID: {safe_str(parent_id)}")
        print(f"   Score: {score} | Depth: {depth}")
        print(f"   Sentiment: {sentiment} ({comment.get('sentiment_score', 0.0)}) | Keywords: {safe_str(keywords)[:50]}")
        print(f"   Body: {safe_str(body)[:80]}...")

    print("\n" + "=" * 60)
    print("SAMPLE Q&A PAIRS (latest 3)")
    print("=" * 60)

    for qa in db.get_latest_qa_pairs(3):
        question = qa.get("question", "N/A")
        answer = qa.get("answer", "N/A")
        post_id = qa.get("post_id", "N/A")
        match_type = qa.get("match_type", "unverified")
        status = qa.get("verification_status", "unverified_best_effort")
        confidence = qa.get("confidence_score", 0.5)

        print(f"\n[Q&A] Post: {safe_str(post_id)}")
        print(f"   Match Tier: {match_type} | Status: {status} | Confidence: {confidence}")
        print(f"   Q: {safe_str(question)[:80]}")
        print(f"   A: {safe_str(answer)[:80]}...")

    print("=" * 60 + "\n")

    db.close()


if __name__ == "__main__":
    view_stored_data()