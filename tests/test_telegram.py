from datetime import datetime, timezone

from blog_tracker.models import BlogPost
from blog_tracker.telegram import HEADER, build_digest, build_digest_messages, send_digest


def _make_post(index: int, summary: str = "요약") -> BlogPost:
    return BlogPost(
        blog_id=f"blog-{index}",
        display_name=f"작성자 {index}",
        blog_title=f"블로그 {index}",
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
    digest = build_digest(posts, dashboard_url="https://example.com/dashboard")

    assert digest.count("<a href=") == 2
    assert digest.count("대시보드 홈페이지 바로가기") == 2
    assert digest.count("https://example.com/dashboard") == 2
    assert digest.startswith(HEADER)
    assert digest.endswith("https://example.com/dashboard")


def test_build_digest_messages_splits_without_dropping_posts():
    posts = [_make_post(index, summary="긴요약" * 80) for index in range(1, 5)]
    messages = build_digest_messages(posts, max_length=500, dashboard_url="https://example.com/dashboard")

    assert len(messages) > 1
    assert sum(message.count("대시보드 홈페이지 바로가기") for message in messages) == len(messages) * 2
    assert sum(message.count("https://example.com/dashboard") for message in messages) == len(messages) * 2
    assert sum(message.count("<a href=") for message in messages) == len(posts)
    assert all(len(message) <= 500 for message in messages)
    assert all(message.endswith("https://example.com/dashboard") for message in messages)


def test_send_digest_attaches_dashboard_button(monkeypatch):
    captured_payload = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json):
            captured_payload.update(json)
            return FakeResponse()

    monkeypatch.setattr("blog_tracker.telegram.httpx.Client", FakeClient)

    result = send_digest(
        "token",
        "chat-id",
        "message",
        dashboard_url="https://1one1one11.github.io/blog-tracker/",
    )

    assert result["ok"] is True
    assert captured_payload["reply_markup"]["inline_keyboard"][0][0] == {
        "text": "브리핑 페이지 열기",
        "url": "https://1one1one11.github.io/blog-tracker/",
    }
