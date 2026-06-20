from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime

@dataclass
class RedditPost:
    post_id: str
    news_id: str
    subreddit: str
    title: str
    body: str
    author: str
    score: int
    created_utc: datetime
    num_comments: int

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

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class QAPair:
    news_id: str
    post_id: str
    question_comment_id: str
    answer_comment_id: str
    question: str
    answer: str

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class DiscussionThread:
    news_id: str
    post_id: str
    thread_id: str
    comments: List[dict]  # Ordered list of comments

    def to_dict(self) -> dict:
        return asdict(self)
