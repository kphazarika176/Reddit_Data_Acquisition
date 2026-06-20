from dataclasses import dataclass, asdict
from typing import List
from datetime import datetime

@dataclass
class NewsArticle:
    """Data model representing a news article."""
    news_id: str
    title: str
    url: str
    published_date: datetime
    keywords: List[str]

    def to_dict(self) -> dict:
        return asdict(self)
