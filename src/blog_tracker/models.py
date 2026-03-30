from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class BlogSource:
    blog_id: str
    display_name: str
    blog_title: str
    group_name: str = "미분류"
    relationship: str = "이웃"
    enabled: bool = True
    rss_url: str | None = None
    notes: str = ""

    @property
    def resolved_rss_url(self) -> str:
        return self.rss_url or f"https://rss.blog.naver.com/{self.blog_id}.xml"


@dataclass(slots=True)
class BlogPost:
    blog_id: str
    display_name: str
    blog_title: str
    group_name: str
    title: str
    link: str
    guid: str
    published_at: datetime
    category: str = ""
    tags: list[str] = field(default_factory=list)
    description_text: str = ""
    content_text: str = ""
    summary: str = ""
    classification: str = ""
