from __future__ import annotations

import html
from typing import Iterable

import httpx

from blog_tracker.dc_gallery import DcPost
from blog_tracker.models import BlogPost

HEADER = "<b>네이버 블로그 새 글 브리핑</b>"
MAX_MESSAGE_LENGTH = 3900


def _render_post(post: BlogPost) -> str:
    return "\n".join(
        [
            f"<b>[{html.escape(post.classification or post.group_name)}]</b> {html.escape(post.title)}",
            f"작성자: {html.escape(post.display_name)} | 그룹: {html.escape(post.group_name)}",
            f"요약: {html.escape(post.summary)}",
            f"<a href=\"{html.escape(post.link)}\">원문 보기</a>",
        ]
    )


def build_digest(posts: Iterable[BlogPost]) -> str:
    blocks = [HEADER, ""]
    for post in posts:
        blocks.append(_render_post(post))
        blocks.append("")
    return "\n".join(blocks).strip()


def _render_dc_post(post: DcPost) -> str:
    return "\n".join(
        [
            f"<b>[{html.escape(post.source_title)}]</b> {html.escape(post.title)}",
            f"작성자: {html.escape(post.author or '익명')} | 댓글: {html.escape(post.comments)} | 추천: {html.escape(post.recommends)} | 조회: {html.escape(post.views)}",
            f"요약: {html.escape(post.summary or post.excerpt)}",
            f"<a href=\"{html.escape(post.link)}\">원문 보기</a>",
        ]
    )


def build_digest_messages(
    posts: list[BlogPost],
    dc_posts: list[DcPost] | None = None,
    priority_bloggers: set[str] | None = None,
    max_length: int = MAX_MESSAGE_LENGTH,
) -> list[str]:
    priority_bloggers = priority_bloggers or set()
    dc_posts = dc_posts or []
    priority_posts = [post for post in posts if post.blog_id in priority_bloggers]
    regular_posts = [post for post in posts if post.blog_id not in priority_bloggers]

    blocks: list[str] = []
    if priority_posts:
        blocks.append("<b>우선 블로거 새 글</b>")
        blocks.extend(_render_post(post) for post in priority_posts)
    if dc_posts:
        blocks.append("<b>디시 커뮤니티 픽</b>")
        blocks.extend(_render_dc_post(post) for post in dc_posts)
    if regular_posts:
        if priority_posts or dc_posts:
            blocks.append("<b>전체 새 글</b>")
        blocks.extend(_render_post(post) for post in regular_posts)

    if not blocks:
        return [HEADER]

    messages: list[str] = []
    current = HEADER
    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) <= max_length:
            current = candidate
            continue

        if current:
            messages.append(current)
        current = f"{HEADER}\n\n{block}" if len(block) + len(HEADER) + 2 <= max_length else block[:max_length]

    if current:
        messages.append(current)
    return messages


def send_digest(bot_token: str, chat_id: str, message: str) -> dict:
    if not bot_token or not chat_id:
        return {"ok": False, "message": "텔레그램 설정이 비어 있어 발송을 건너뜁니다."}

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    with httpx.Client(timeout=20) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    return {"ok": bool(data.get("ok")), "message": data}


def send_digest_messages(bot_token: str, chat_id: str, messages: list[str]) -> list[dict]:
    return [send_digest(bot_token, chat_id, message) for message in messages]
