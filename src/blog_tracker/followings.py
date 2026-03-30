from __future__ import annotations

import csv
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup


def _extract_blog_id(href: str) -> str:
    parsed = urlparse(href)
    if parsed.path.endswith("GoRepresentBlog.naver"):
        return parse_qs(parsed.query).get("userId", [""])[0]
    path = parsed.path.strip("/")
    if path and path not in {"PostList.naver", "PostView.naver"}:
        return path
    return parse_qs(parsed.query).get("blogId", [""])[0]


def scrape_followings(followings_url: str, max_pages: int = 200) -> list[dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with httpx.Client(timeout=20, headers={"User-Agent": "Mozilla/5.0"}) as client:
        for page in range(1, max_pages + 1):
            separator = "&" if "?" in followings_url else "?"
            page_url = f"{followings_url}{separator}currentPage={page}"
            response = client.get(page_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select("ul.my_buddy_list > li")
            if not items:
                break

            page_added = 0
            for item in items:
                name_link = item.select_one("a.buddy_name[href]")
                title_link = item.select_one("a.blog_name[href]")
                if not name_link or not title_link:
                    continue
                href = title_link["href"]
                if "GoRepresentBlog" in href:
                    continue
                blog_id = _extract_blog_id(href)
                if not blog_id:
                    continue
                rows[blog_id] = {
                    "blog_id": blog_id,
                    "display_name": " ".join(name_link.get_text(" ", strip=True).split()),
                    "blog_title": " ".join(title_link.get_text(" ", strip=True).split()),
                    "group_name": "미분류",
                    "relationship": "이웃",
                    "enabled": "true",
                    "rss_url": "",
                    "notes": "",
                }
                page_added += 1

            if page_added == 0:
                break
    return list(rows.values())


def write_blogs_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["blog_id", "display_name", "blog_title", "group_name", "relationship", "enabled", "rss_url", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows)
