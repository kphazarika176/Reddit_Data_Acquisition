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
    except Exception:
        return text.encode("ascii", errors="ignore").decode("ascii")

def view_stored_data():
    db = DatabaseManager()

    print("\n" + "="*60)
    print("REDDIT CONTENT ACQUISITION DATABASE STATISTICS")
    print("="*60)

    # Count documents in each collection
    news_count = db.news.count_documents({})
    posts_count = db.reddit_posts.count_documents({})
    comments_count = db.reddit_comments.count_documents({})
    qa_count = db.qa_pairs.count_documents({})

    print(f"News Articles:   {news_count}")
    print(f"Reddit Posts:    {posts_count}")
    print(f"Reddit Comments: {comments_count}")
    print(f"Q&A Pairs:       {qa_count}")

    print("\n" + "="*60)
    print("SAMPLE NEWS ARTICLES")
    print("="*60)
    for article in db.news.find().sort("_id", -1).limit(3):
        title = article.get("title", "N/A")
        url = article.get("url", "N/A")
        news_id = article.get("news_id", "N/A")
        keywords = article.get("keywords", [])
        print(f"\n[News] {safe_str(title)[:70]}")
        print(f"   ID: {safe_str(news_id)}")
        print(f"   URL: {safe_str(url)}")
        print(f"   Keywords: {', '.join(safe_str(kw) for kw in keywords)}")

    print("\n" + "="*60)
    print("SAMPLE REDDIT POSTS (with comment count)")
    print("="*60)

    for post in db.reddit_posts.find().sort("_id", -1).limit(3):
        title = post.get("title", "N/A")
        post_id = post.get("post_id", "N/A")
        subreddit = post.get("subreddit", "N/A")
        news_id = post.get("news_id", "N/A")
        
        # Count comments for this post
        comment_count = db.reddit_comments.count_documents({"post_id": post_id})
        
        print(f"\n[Post] {safe_str(title)[:70]}")
        print(f"   Post ID: {safe_str(post_id)}")
        print(f"   Source News ID: {safe_str(news_id)}")
        print(f"   Subreddit: r/{safe_str(subreddit)}")
        print(f"   Comments: {comment_count}")

    print("\n" + "="*60)
    print("SAMPLE REDDIT COMMENTS (latest 3)")
    print("="*60)

    for comment in db.reddit_comments.find().sort("_id", -1).limit(3):
        body = comment.get("body", "N/A")
        author = comment.get("author", "N/A")
        post_id = comment.get("post_id", "N/A")
        parent_id = comment.get("parent_id", "N/A")
        
        print(f"\n[Comment] u/{safe_str(author)}")
        print(f"   Post ID: {safe_str(post_id)}")
        print(f"   Parent ID: {safe_str(parent_id)}")
        print(f"   Body: {safe_str(body)[:80]}...")

    print("\n" + "="*60)
    print("SAMPLE Q&A PAIRS (latest 3)")
    print("="*60)

    for qa in db.qa_pairs.find().sort("_id", -1).limit(3):
        question = qa.get("question", "N/A")
        answer = qa.get("answer", "N/A")
        post_id = qa.get("post_id", "N/A")
        news_id = qa.get("news_id", "N/A")
        
        print(f"\n[Q&A] Post: {safe_str(post_id)} | News: {safe_str(news_id)}")
        print(f"   Q: {safe_str(question)[:80]}")
        print(f"   A: {safe_str(answer)[:80]}...")

    print("="*60 + "\n")

if __name__ == "__main__":
    view_stored_data()