import requests
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from src.logger import get_logger

logger = get_logger(__name__)


class ApifyExtractor:
    """Extracts Reddit posts and comments using the Apify Reddit Scraper Lite Actor (trudax/reddit-scraper-lite)."""

    BASE_URL = "https://api.apify.com/v2"

    def __init__(self, api_token: str, actor_id: str = "trudax/reddit-scraper-lite"):
        self.api_token = api_token
        self.actor_id = actor_id

    def _start_actor(self, run_input: Dict[str, Any]) -> Optional[str]:
        """Starts the Apify actor and returns the run ID."""
        url = f"{self.BASE_URL}/acts/{self.actor_id}/runs"

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, json=run_input, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            run_id = data.get("data", {}).get("id")
            logger.info(f"Started Apify actor run: {run_id}")
            return run_id
        except requests.RequestException as e:
            logger.error(f"Failed to start Apify actor: {e}")
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

        logger.info(f"Fetching data from r/{subreddit} via Apify (limit={limit})...")

        # Minimal run input (only what's strictly necessary)
        run_input = {
            "startUrls": [{"url": f"https://www.reddit.com/r/{subreddit}/"}],
            "skipComments": False,
            "maxPostCount": limit,
            "maxItems": limit * 3,
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
            if item.get("dataType") == "post":
                posts.append(item)
            elif item.get("dataType") == "comment":
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
    """Normalizes an Apify post item to our RedditPost format, using the actual fields from trudax/reddit-scraper-lite."""

    # Extract raw fields from the item (based on official README examples)
    post_id = item.get("id", f"t3_{item.get('parsedId', '')}")
    if not post_id.startswith("t3_"):
        post_id = f"t3_{post_id}"

    created_utc = item.get("createdAt")
    if isinstance(created_utc, str):
        try:
            created_utc = datetime.fromisoformat(created_utc.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            created_utc = datetime.now(timezone.utc)
    else:
        created_utc = datetime.now(timezone.utc)

    # Get community name and strip off the 'r/' prefix
    subreddit = item.get("parsedCommunityName", item.get("communityName", ""))
    if subreddit.startswith("r/"):
        subreddit = subreddit[2:]

    return {
        "post_id": post_id,
        "subreddit": subreddit,
        "title": item.get("title", ""),
        "body": item.get("body", ""),
        "author": item.get("username", "unknown"),
        "score": item.get("upVotes", 0),
        "url": item.get("url", ""),
        "created_utc": created_utc,
        "num_comments": item.get("numberOfComments", 0)
    }


def normalize_apify_comment(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes an Apify comment item to our RedditComment format, using the actual fields from trudax/reddit-scraper-lite."""

    comment_id = item.get("id", f"t1_{item.get('parsedId', '')}")
    if not comment_id.startswith("t1_"):
        comment_id = f"t1_{comment_id}"

    post_id = item.get("postId", "")
    parent_id = item.get("parentId", item.get("postId", ""))

    created_utc = item.get("createdAt")
    if isinstance(created_utc, str):
        try:
            created_utc = datetime.fromisoformat(created_utc.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            created_utc = datetime.now(timezone.utc)
    else:
        created_utc = datetime.now(timezone.utc)

    return {
        "comment_id": comment_id,
        "post_id": post_id,
        "parent_id": parent_id,
        "author": item.get("username", "unknown"),
        "body": item.get("body", ""),
        "score": item.get("upVotes", 0),
        "depth": item.get("depth", 0),
        "created_utc": created_utc
    }
