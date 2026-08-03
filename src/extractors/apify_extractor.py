import html
import socket
import time
import requests
import urllib3.util.connection as urllib3_cn
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from src.logger import get_logger

# Force IPv4 socket resolution to prevent Windows IPv6 DNS getaddrinfo timeouts [Errno 11002/11001]
def _allowed_gai_family():
    return socket.AF_INET

urllib3_cn.allowed_gai_family = _allowed_gai_family

logger = get_logger(__name__)


def clean_reddit_post_text(text: str) -> str:
    """Decodes HTML entities and strips Reddit RSS submission boilerplate."""
    if not text:
        return ""
    
    # Unescape HTML entities (&#32; -> space, &#39; -> ', &quot; -> ", &amp; -> &)
    cleaned = html.unescape(str(text)).strip()
    
    # Strip submission tagline boilerplate like "submitted by /u/user [link] [comments]"
    if "submitted by" in cleaned and "[link]" in cleaned:
        parts = cleaned.split("submitted by")
        main_content = parts[0].strip()
        return main_content
        
    return cleaned


def clean_reddit_comment_text(text: str) -> str:
    """Decodes HTML entities in comment bodies."""
    if not text:
        return ""
    return html.unescape(str(text)).strip()


class ApifyExtractor:
    """Extracts Reddit posts and comments using the Apify Reddit Scraper Lite Actor (trudax/reddit-scraper-lite)."""

    BASE_URL = "https://api.apify.com/v2"

    def __init__(self, api_token: str, actor_id: str = "trudax/reddit-scraper-lite"):
        self.api_token = api_token
        self.actor_id = actor_id

    def _start_actor(self, run_input: Dict[str, Any], max_retries: int = 3) -> Optional[str]:
        """Starts the Apify actor with automatic retries for transient network/DNS errors."""
        url = f"{self.BASE_URL}/acts/{self.actor_id}/runs"

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(url, json=run_input, headers=headers, timeout=60)
                response.raise_for_status()
                data = response.json()
                run_id = data.get("data", {}).get("id")
                logger.info(f"Started Apify actor run: {run_id}")
                return run_id
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt}/{max_retries} failed to start Apify actor: {e}")
                if attempt < max_retries:
                    time.sleep(3 * attempt)
                else:
                    logger.error(f"All {max_retries} attempts to start Apify actor failed.")
                    return None

    def _wait_for_completion(self, run_id: str, max_wait_minutes: int = 15) -> Optional[str]:
        """Waits for the actor run to complete and returns the dataset ID."""
        url = f"{self.BASE_URL}/acts/{self.actor_id}/runs/{run_id}"
        headers = {"Authorization": f"Bearer {self.api_token}"}

        max_attempts = max_wait_minutes * 6  # Check every 10 seconds
        attempts = 0

        while attempts < max_attempts:
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json().get("data", {})
                status = data.get("status")

                if status == "SUCCEEDED":
                    dataset_id = data.get("defaultDatasetId")
                    logger.info(f"Apify run completed. Dataset ID: {dataset_id}")
                    return dataset_id
                elif status in ("FAILED", "ABORTED", "TIMED_OUT"):
                    from pprint import pprint

                    logger.error(f"Apify run {status}")
                    print("\n========== FULL RUN DATA ==========")
                    pprint(data)
                    print("===================================\n")
                    return None

                logger.info(f"Apify run status: {status}. Waiting...")
                time.sleep(10)
                attempts += 1

            except requests.RequestException as e:
                logger.error(f"Error checking run status: {e}")
                time.sleep(10)
                attempts += 1

        logger.error(f"Apify run timed out after {max_wait_minutes} minutes")
        return None

    def _fetch_dataset_items(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Fetches all items from the dataset."""
        url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
        headers = {"Authorization": f"Bearer {self.api_token}"}

        all_items = []
        offset = 0
        limit = 1000

        while True:
            try:
                params = {"offset": offset, "limit": limit}
                response = requests.get(url, headers=headers, params=params, timeout=60)
                response.raise_for_status()

                items = response.json()
                if not items:
                    break

                all_items.extend(items)
                logger.info(f"Fetched {len(items)} items (total: {offset + len(items)})")

                if len(items) < limit:
                    break

                offset += limit
                time.sleep(1)  # Rate limit

            except requests.RequestException as e:
                logger.error(f"Error fetching dataset items: {e}")
                break

        return all_items

    def fetch_subreddit_data(self, subreddit: str = "news", limit: int = 10) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Fetches both posts and comments from a subreddit in a single Apify run."""
        if not self.api_token:
            logger.error("APIFY_API_TOKEN is not set")
            return [], []

        logger.info(f"Fetching data from r/{subreddit} via Apify actor '{self.actor_id}' (limit={limit})...")

        # Select schema depending on actor ID
        if "harshmaur" in self.actor_id:
            run_input = {
                "startUrls": [{"url": f"https://www.reddit.com/r/{subreddit}/"}],
                "maxPostsCount": limit,
                "crawlCommentsPerPost": True,
                "maxCommentsPerPost": 50,
                "maxCommentsCount": limit * 50,
                "proxy": {
                    "useApifyProxy": True
                }
            }
        else:
            run_input = {
                "startUrls": [{"url": f"https://www.reddit.com/r/{subreddit}/"}],
                "skipComments": False,
                "maxPostCount": limit,
                "maxComments": limit * 20,
                "maxCommentDepth": 5,
                "commentsMode": "ALL",
                "sortCommentsBy": "TOP",
                "maxItems": limit * 25,
                "scrollTimeout": 40,
                "proxy": {
                    "useApifyProxy": True
                }
            }

        # Start the actor
        run_id = self._start_actor(run_input)
        if not run_id:
            return [], []

        # Wait for completion
        dataset_id = self._wait_for_completion(run_id)
        if not dataset_id:
            return [], []

        # Fetch items
        items = self._fetch_dataset_items(dataset_id)

        logger.info(f"Got {len(items)} total items from dataset")

        # Separate posts and comments strictly using dataType
        posts = []
        comments = []

        for item in items:
            data_type = item.get("dataType")
            if data_type == "post":
                posts.append(item)
            elif data_type == "comment":
                comments.append(item)

        logger.info(f"Extracted {len(posts)} posts and {len(comments)} comments")
        return posts, comments

    def fetch_subreddit_posts(self, subreddit: str = "news", limit: int = 10) -> List[Dict[str, Any]]:
        """Fetches posts from a subreddit using Apify actor."""
        posts, _ = self.fetch_subreddit_data(subreddit=subreddit, limit=limit)
        return posts

    def fetch_comments_for_subreddit(self, subreddit: str = "news", limit: int = 100) -> List[Dict[str, Any]]:
        """Fetches comments from a subreddit using Apify actor."""
        _, comments = self.fetch_subreddit_data(subreddit=subreddit, limit=limit)
        return comments


def normalize_apify_post(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes an Apify post item to our RedditPost format, supporting harshmaur/reddit-scraper and trudax/reddit-scraper-lite."""

    post_id = item.get("id", f"t3_{item.get('parsedId', '')}")
    if not post_id.startswith("t3_"):
        post_id = f"t3_{post_id}"

    created_utc = item.get("createdAt") or item.get("crawledAt")
    if isinstance(created_utc, str):
        try:
            created_utc = datetime.fromisoformat(created_utc.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            created_utc = datetime.now(timezone.utc)
    else:
        created_utc = datetime.now(timezone.utc)

    # Get community name and strip off the 'r/' prefix
    subreddit = item.get("parsedCommunityName", item.get("communityName", item.get("subredditName", "")))
    if subreddit.startswith("r/"):
        subreddit = subreddit[2:]

    title = clean_reddit_post_text(item.get("title", ""))
    body = clean_reddit_post_text(item.get("body", ""))

    author = item.get("authorName", item.get("username", item.get("author", "unknown")))
    score = item.get("upVotes", item.get("score", 0))
    url = item.get("postUrl", item.get("url", ""))
    num_comments = item.get("commentsCount", item.get("numberOfComments", item.get("numComments", 0)))

    return {
        "post_id": post_id,
        "subreddit": subreddit,
        "title": title,
        "body": body,
        "author": author,
        "score": score,
        "url": url,
        "created_utc": created_utc,
        "num_comments": num_comments
    }


def normalize_apify_comment(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes an Apify comment item to our RedditComment format.
    Robustly captures parent_id and calculates comment depth for nested trees.
    """

    comment_id = item.get("id", f"t1_{item.get('parsedId', '')}")
    if not comment_id.startswith("t1_"):
        comment_id = f"t1_{comment_id}"

    post_id = item.get("postId", item.get("post_id", ""))
    if post_id and not post_id.startswith("t3_"):
        post_id = f"t3_{post_id}"

    # Extract parent ID from possible field aliases
    raw_parent = (
        item.get("parentId")
        or item.get("parent_id")
        or item.get("replyToId")
        or item.get("parentCommentId")
        or post_id
    )

    parent_id = str(raw_parent) if raw_parent else post_id
    if parent_id and not parent_id.startswith("t1_") and not parent_id.startswith("t3_"):
        if parent_id == post_id.replace("t3_", "") or parent_id == post_id:
            parent_id = f"t3_{parent_id}" if not parent_id.startswith("t3_") else parent_id
        else:
            parent_id = f"t1_{parent_id}"

    # Determine depth
    depth = item.get("depth", item.get("commentDepth"))
    if depth is None:
        depth = 0 if (parent_id == post_id or parent_id.startswith("t3_")) else 1
    else:
        try:
            depth = int(depth)
        except (ValueError, TypeError):
            depth = 0

    created_utc = item.get("createdAt") or item.get("crawledAt")
    if isinstance(created_utc, str):
        try:
            created_utc = datetime.fromisoformat(created_utc.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            created_utc = datetime.now(timezone.utc)
    else:
        created_utc = datetime.now(timezone.utc)

    body = clean_reddit_comment_text(item.get("body", ""))
    author = item.get("authorName", item.get("username", item.get("author", "unknown")))
    score = item.get("upVotes", item.get("score", 0))

    return {
        "comment_id": comment_id,
        "post_id": post_id,
        "parent_id": parent_id,
        "author": author,
        "body": body,
        "score": score,
        "depth": depth,
        "created_utc": created_utc
    }

