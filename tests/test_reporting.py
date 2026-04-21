from datetime import datetime, timezone

from blog_tracker.models import BlogPost
from blog_tracker.reporting import build_digest_payload


def test_build_digest_payload_marks_priority_posts():
    posts = [
        BlogPost(
            blog_id="priority-blog",
            display_name="작성자",
            blog_title="블로그",
            group_name="주식",
            title="제목",
            link="https://example.com/1",
            guid="guid-1",
            published_at=datetime.now(timezone.utc),
            summary="요약",
            classification="기업분석",
        )
    ]

    payload = build_digest_payload(
        posts,
        generated_at=datetime.now(timezone.utc),
        days_back=3,
        priority_bloggers={"priority-blog"},
    )

    assert payload["priority_post_count"] == 1
    assert payload["posts"][0]["is_priority"] is True
