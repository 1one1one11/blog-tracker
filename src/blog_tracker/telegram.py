from __future__ import annotations

import html

import httpx

from blog_tracker.models import BlogPost

MAX_MESSAGE_LENGTH = 3800


def _render_post(post: BlogPost) -> str:
    return "\n".join(
        [
            f"<b>[{html.escape(post.classification or post.group_name)}]</b> {html.escape(post.title)}",
            f"작성: {html.escape(post.display_name)}",
            f"요약: {html.escape(post.summary)}",
            f"<a href=\"{html.escape(post.link)}\">원문 보기</a>",
        ]
    )


def build_digest_messages(posts: list[BlogPost], priority_bloggers: set[str]) -> list[str]:
    priority_posts = [post for post in posts if post.blog_id in priority_bloggers]
    regular_posts = [post for post in posts if post.blog_id not in priority_bloggers]

    blocks: list[str] = []
    if priority_posts:
        blocks.append("<b>우선 블로거 새 글</b>")
        blocks.extend(_render_post(post) for post in priority_posts)
    if regular_posts:
        blocks.append("<b>전체 새 글</b>")
        blocks.extend(_render_post(post) for post in regular_posts)

    messages: list[str] = []
    current = "<b>네이버 블로그 브리핑</b>"
    for block in blocks:
        candidate = current + "\n\n" + block if current.strip() else block
        if len(candidate) > MAX_MESSAGE_LENGTH and current.strip():
            messages.append(current.strip())
            current = block
        else:
            current = candidate
    if current.strip():
        messages.append(current.strip())
    return messages


def send_digest(bot_token: str, chat_id: str, messages: list[str]) -> dict:
    if not bot_token or not chat_id:
        return {"ok": False, "message": "텔레그램 설정이 비어 있어 발송을 건너뜁니다."}

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    with httpx.Client(timeout=20) as client:
        for message in messages:
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                return {"ok": False, "message": data}
    return {"ok": True, "message": f"{len(messages)}개 메시지 전송 성공"}
