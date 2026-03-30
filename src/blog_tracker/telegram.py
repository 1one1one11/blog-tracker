from __future__ import annotations

import html

import httpx

from blog_tracker.models import BlogPost


def build_digest(posts: list[BlogPost]) -> str:
    lines = ["<b>네이버 블로그 새 글 브리핑</b>", ""]
    for post in posts:
        lines.append(
            "\n".join(
                [
                    f"<b>[{html.escape(post.classification or post.group_name)}]</b> {html.escape(post.title)}",
                    f"작성자: {html.escape(post.display_name)} | 그룹: {html.escape(post.group_name)}",
                    f"요약: {html.escape(post.summary)}",
                    f"<a href=\"{html.escape(post.link)}\">원문 보기</a>",
                ]
            )
        )
        lines.append("")
    body = "\n".join(lines).strip()
    return body[:3900]


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
