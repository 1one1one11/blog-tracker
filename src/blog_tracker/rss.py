from __future__ import annotations

import email.utils
import re
import warnings
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

from blog_tracker.models import BlogPost, BlogSource

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def clean_html_text(value: str) -> str:
    soup = BeautifulSoup(value or "", "html.parser")
    text = soup.get_text(" ", strip=True)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_pub_date(raw: str) -> datetime:
    return email.utils.parsedate_to_datetime(raw)


def fetch_post_content(link: str) -> str:
    try:
        with httpx.Client(timeout=12, headers={"User-Agent": "Mozilla/5.0"}) as client:
            response = client.get(link)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            frame = soup.find("iframe", id="mainFrame")
            if frame and frame.get("src"):
                post_url = urljoin(str(response.url), frame["src"])
                response = client.get(post_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
    except Exception:
        return ""

    containers = [
        soup.select_one(".se-main-container"),
        soup.select_one("#postViewArea"),
        soup.select_one(".post_view"),
        soup.select_one(".contents_style"),
    ]
    for container in containers:
        if container:
            text = clean_html_text(str(container))
            if text:
                return text
    return ""


def fetch_recent_posts(source: BlogSource, days_back: int) -> list[BlogPost]:
    try:
        with httpx.Client(timeout=12, headers={"User-Agent": "Mozilla/5.0"}) as client:
            response = client.get(source.resolved_rss_url)
            response.raise_for_status()
    except Exception:
        return []

    root = ET.fromstring(response.text)
    channel = root.find("channel")
    if channel is None:
        return []

    cutoff = datetime.now().astimezone() - timedelta(days=days_back)
    posts: list[BlogPost] = []
    for item in channel.findall("item"):
        raw_pub_date = item.findtext("pubDate", default="")
        if not raw_pub_date:
            continue
        published_at = parse_pub_date(raw_pub_date)
        if published_at < cutoff:
            continue

        description_text = clean_html_text(item.findtext("description", default=""))
        tags = [
            tag.strip()
            for tag in (item.findtext("tag", default="") or "").split(",")
            if tag.strip()
        ]
        posts.append(
            BlogPost(
                blog_id=source.blog_id,
                display_name=source.display_name,
                blog_title=source.blog_title,
                group_name=source.group_name,
                title=clean_html_text(item.findtext("title", default="")),
                link=(item.findtext("link", default="") or "").strip(),
                guid=(item.findtext("guid", default="") or item.findtext("link", default="")).strip(),
                published_at=published_at,
                category=clean_html_text(item.findtext("category", default="")),
                tags=tags,
                description_text=description_text,
            )
        )
    return posts
