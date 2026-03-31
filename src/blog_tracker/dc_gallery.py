from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from blog_tracker.rss import clean_html_text

BASE_URL = "https://gall.dcinside.com"
LIST_URL = f"{BASE_URL}/mgallery/board/lists/?id=tsmcsamsungskhynix"


@dataclass(slots=True)
class DcPost:
    title: str
    link: str
    author: str
    published_at: str
    views: str
    recommends: str
    comments: str
    excerpt: str


def _fetch_post_excerpt(client: httpx.Client, link: str) -> str:
    try:
        response = client.get(link)
        response.raise_for_status()
    except Exception:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for selector in [".writing_view_box", ".write_div", ".view_content_wrap"]:
        node = soup.select_one(selector)
        if node:
            text = clean_html_text(str(node))
            if text:
                return text[:500]
    return ""


def fetch_dc_semiconductor_posts(limit: int = 30) -> list[DcPost]:
    with httpx.Client(timeout=15, headers={"User-Agent": "Mozilla/5.0"}) as client:
        response = client.get(LIST_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        posts: list[DcPost] = []
        for row in soup.select("tr.us-post"):
            if row.get("data-type") == "icon_notice":
                continue
            title_link = row.select_one("td.gall_tit a[href]")
            if not title_link:
                continue
            title = clean_html_text(title_link.get_text(" ", strip=True))
            link = urljoin(BASE_URL, title_link["href"])
            author = row.select_one("td.gall_writer")
            date = row.select_one("td.gall_date")
            views = row.select_one("td.gall_count")
            recommends = row.select_one("td.gall_recommend")
            reply = row.select_one(".reply_num")
            excerpt = _fetch_post_excerpt(client, link)
            posts.append(
                DcPost(
                    title=title,
                    link=link,
                    author=author.get("data-nick", "").strip() if author else "",
                    published_at=date.get("title", "").strip() if date else "",
                    views=views.get_text(" ", strip=True) if views else "",
                    recommends=recommends.get_text(" ", strip=True) if recommends else "",
                    comments=clean_html_text(reply.get_text(" ", strip=True)).strip("[]") if reply else "0",
                    excerpt=excerpt,
                )
            )
            if len(posts) >= limit:
                break
    return posts
