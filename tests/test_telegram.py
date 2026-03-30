from datetime import datetime, timezone

from blog_tracker.models import BlogPost
from blog_tracker.telegram import HEADER, build_digest, build_digest_messages


def _make_post(index: int, summary: str = "요약") -> BlogPost:
    return BlogPost(
        blog_id=f"blog-{index}",
        display_name=f"작성자{index}",
        blog_title=f"블로그{index}",
        group_name="미분류",
        title=f"제목 {index}",
        link=f"https://example.com/{index}",
        guid=f"guid-{index}",
        published_at=datetime.now(timezone.utc),
        summary=summary,
        classification="기업분석",
    )


def test_build_digest_keeps_all_posts():
    posts = [_make_post(1), _make_post(2)]
    digest = build_digest(posts)
    assert digest.count("<a href=") == 2
    assert digest.startswith(HEADER)


def test_build_digest_messages_splits_without_dropping_posts():
    posts = [_make_post(index, summary="긴요약 " * 80) for index in range(1, 5)]
    messages = build_digest_messages(posts, max_length=500)

    assert len(messages) > 1
    assert sum(message.count("<a href=") for message in messages) == len(posts)
    assert all(len(message) <= 500 for message in messages)
