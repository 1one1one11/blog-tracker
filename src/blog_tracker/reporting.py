from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from blog_tracker.models import BlogPost


def serialize_post(post: BlogPost, priority_bloggers: set[str] | None = None) -> dict[str, Any]:
    priority_bloggers = priority_bloggers or set()
    payload = asdict(post)
    payload["published_at"] = post.published_at.isoformat()
    payload["tags"] = list(post.tags)
    payload["has_content"] = bool(post.content_text.strip())
    payload["summary_length"] = len(post.summary.strip())
    payload["is_priority"] = post.blog_id in priority_bloggers
    return payload


def build_digest_payload(
    posts: list[BlogPost],
    generated_at: datetime,
    days_back: int,
    priority_bloggers: set[str] | None = None,
) -> dict[str, Any]:
    priority_bloggers = priority_bloggers or set()
    classifications = Counter(post.classification or post.group_name or "미분류" for post in posts)
    authors = Counter(post.display_name for post in posts)
    groups = Counter(post.group_name or "미분류" for post in posts)
    return {
        "generated_at": generated_at.isoformat(),
        "days_back": days_back,
        "post_count": len(posts),
        "priority_post_count": sum(1 for post in posts if post.blog_id in priority_bloggers),
        "classifications": dict(classifications.most_common()),
        "authors": dict(authors.most_common()),
        "groups": dict(groups.most_common()),
        "posts": [serialize_post(post, priority_bloggers=priority_bloggers) for post in posts],
    }


def write_digest_payload(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
