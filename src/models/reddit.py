from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime

@dataclass
class RedditPost:
    post_id: str
    subreddit: str
    title: str
    body: str
    author: str
    score: int
    url: str
    created_utc: datetime
    num_comments: int
    sentiment_score: float = 0.0
    sentiment_label: str = "neutral"
    keywords: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class RedditComment:
    comment_id: str
    post_id: str
    parent_id: Optional[str]
    author: str
    body: str
    score: int
    depth: int
    created_utc: datetime
    sentiment_score: float = 0.0
    sentiment_label: str = "neutral"
    keywords: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class QAPair:
    post_id: str
    question_comment_id: str
    answer_comment_id: str
    question: str
    answer: str
    score_signal: int = 0
    match_type: str = "unverified"
    verification_status: str = "unverified_best_effort"
    confidence_score: float = 0.5

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class DiscussionThread:
    post_id: str
    thread_id: str
    comments: List[dict]  # Ordered list of comments

    def to_dict(self) -> dict:
        return asdict(self)

