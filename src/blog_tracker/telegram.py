from __future__ import annotations

import html
from typing import Iterable

import httpx

from blog_tracker.dc_gallery import DcPost
from blog_tracker.models import BlogPost

HEADER = "<b>네이버 블로그 새 글 브리핑</b>"
MAX_MESSAGE_LENGTH = 3900
DASHBOARD_LINK_LABEL = "대시보드 홈페이지 바로가기"
DASHBOARD_BUTTON_LABEL = "브리핑 페이지 열기"


def _build_header(dashboard_url: str | None = None) -> str:
    header_lines = [HEADER]
    if dashboard_url:
        header_lines.append(_build_dashboard_link(dashboard_url))
    return "\n".join(header_lines)


def _build_dashboard_link(dashboard_url: str) -> str:
    return f"{DASHBOARD_LINK_LABEL}: {html.escape(dashboard_url)}"


def _build_footer(dashboard_url: str | None = None) -> str:
    return _build_dashboard_link(dashboard_url) if dashboard_url else ""


def _append_footer(message: str, dashboard_url: str | None = None) -> str:
    footer = _build_footer(dashboard_url)
    return f"{message}\n\n{footer}".strip() if footer else message.strip()


def _render_post(post: BlogPost) -> str:
    return "\n".join(
        [
            f"<b>[{html.escape(post.classification or post.group_name)}]</b> {html.escape(post.title)}",
            f"작성자: {html.escape(post.display_name)} | 그룹: {html.escape(post.group_name)}",
            f"요약: {html.escape(post.summary)}",
            f'<a href="{html.escape(post.link)}">원문 보기</a>',
        ]
    )


def build_digest(posts: Iterable[BlogPost], dashboard_url: str | None = None) -> str:
    blocks = [_build_header(dashboard_url), ""]
    for post in posts:
        blocks.append(_render_post(post))
        blocks.append("")
    return _append_footer("\n".join(blocks), dashboard_url)


def _render_dc_post(post: DcPost) -> str:
    return "\n".join(
        [
            f"<b>[{html.escape(post.source_title)}]</b> {html.escape(post.title)}",
            (
                f"작성자: {html.escape(post.author or '익명')} | 댓글: {html.escape(post.comments)} | "
                f"추천: {html.escape(post.recommends)} | 조회: {html.escape(post.views)}"
            ),
            f"요약: {html.escape(post.summary or post.excerpt)}",
            f'<a href="{html.escape(post.link)}">원문 보기</a>',
        ]
    )


def build_digest_messages(
    posts: list[BlogPost],
    dc_posts: list[DcPost] | None = None,
    priority_bloggers: set[str] | None = None,
    max_length: int = MAX_MESSAGE_LENGTH,
    dashboard_url: str | None = None,
) -> list[str]:
    priority_bloggers = priority_bloggers or set()
    dc_posts = dc_posts or []
    header = _build_header(dashboard_url)
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
        return [_append_footer(header, dashboard_url)]

    messages: list[str] = []
    current = header
    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if len(_append_footer(candidate, dashboard_url)) <= max_length:
            current = candidate
            continue

        if current:
            messages.append(_append_footer(current, dashboard_url))
        prefixed_block = f"{header}\n\n{block}"
        if len(_append_footer(prefixed_block, dashboard_url)) <= max_length:
            current = prefixed_block
        else:
            footer_len = len(_build_footer(dashboard_url))
            reserve = len(header) + footer_len + 4
            available = max(0, max_length - reserve)
            current = f"{header}\n\n{block[:available]}"

    if current:
        messages.append(_append_footer(current, dashboard_url))
    return messages


def send_digest(bot_token: str, chat_id: str, message: str, dashboard_url: str | None = None) -> dict:
    if not bot_token or not chat_id:
        return {"ok": False, "message": "텔레그램 설정이 비어 있어 발송을 건너뜁니다."}

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if dashboard_url:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {
                        "text": DASHBOARD_BUTTON_LABEL,
                        "url": dashboard_url,
                    }
                ]
            ]
        }
    try:
        with httpx.Client(timeout=20) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        return {"ok": False, "message": f"텔레그램 발송 실패: {exc}"}
    return {"ok": bool(data.get("ok")), "message": data}


def send_digest_messages(
    bot_token: str,
    chat_id: str,
    messages: list[str],
    dashboard_url: str | None = None,
) -> list[dict]:
    return [send_digest(bot_token, chat_id, message, dashboard_url=dashboard_url) for message in messages]
