from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from blog_tracker.rss import clean_html_text

BASE_URL = "https://gall.dcinside.com"
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}


@dataclass(slots=True, frozen=True)
class DcGallery:
    gallery_id: str
    title: str
    list_url: str
    curated_limit: int
    keywords: tuple[str, ...]


SEMICONDUCTOR_GALLERY = DcGallery(
    gallery_id="tsmcsamsungskhynix",
    title="반도체 산업 갤러리",
    list_url=f"{BASE_URL}/mgallery/board/lists/?id=tsmcsamsungskhynix",
    curated_limit=6,
    keywords=("반도체", "삼성", "하이닉스", "엔비디아", "hbm", "파운드리", "tsmc", "마이크론"),
)
KRSTOCK_GALLERY = DcGallery(
    gallery_id="krstock",
    title="한국 주식 갤러리",
    list_url=f"{BASE_URL}/mgallery/board/lists/?id=krstock",
    curated_limit=5,
    keywords=("코스피", "코스닥", "수급", "시황", "금투세", "공매도", "기관", "외인", "환율", "금리"),
)
USSTOCK_GALLERY = DcGallery(
    gallery_id="stockus",
    title="미국 주식 갤러리",
    list_url=f"{BASE_URL}/mgallery/board/lists/?id=stockus",
    curated_limit=5,
    keywords=("나스닥", "s&p", "연준", "파월", "엔비디아", "테슬라", "애플", "메타", "관세", "실적"),
)
GLOBALSTOCK_GALLERY = DcGallery(
    gallery_id="tenbagger",
    title="해외주식 갤러리",
    list_url=f"{BASE_URL}/mgallery/board/lists/?id=tenbagger",
    curated_limit=5,
    keywords=("미국", "중국", "반도체", "ai", "지수", "시황", "실적", "테마", "엔비디아", "테슬라"),
)

LIST_URL = SEMICONDUCTOR_GALLERY.list_url
CURATED_GALLERIES: tuple[DcGallery, ...] = (
    SEMICONDUCTOR_GALLERY,
    KRSTOCK_GALLERY,
    USSTOCK_GALLERY,
    GLOBALSTOCK_GALLERY,
)

MARKET_SIGNAL_KEYWORDS = (
    "시황",
    "시장",
    "지수",
    "금리",
    "환율",
    "관세",
    "실적",
    "반도체",
    "엔비디아",
    "테슬라",
    "코스피",
    "코스닥",
    "나스닥",
    "s&p",
    "fed",
    "연준",
    "파월",
    "수급",
)


@dataclass(slots=True)
class DcPost:
    source_id: str
    source_title: str
    source_link: str
    title: str
    link: str
    author: str
    published_at: str
    views: str
    recommends: str
    comments: str
    excerpt: str
    summary: str = ""
    score: float = 0.0

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["score"] = round(self.score, 3)
        return payload


def _parse_count(value: str) -> int:
    digits = re.sub(r"[^\d]", "", value or "")
    return int(digits) if digits else 0


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
                return text[:700]
    return ""


def _score_title(title: str, keywords: tuple[str, ...]) -> float:
    lowered = (title or "").lower()
    score = 0.0
    for keyword in MARKET_SIGNAL_KEYWORDS:
        if keyword.lower() in lowered:
            score += 1.2
    for keyword in keywords:
        if keyword.lower() in lowered:
            score += 0.9
    return score


def _score_post(title: str, views: int, recommends: int, comments: int, keywords: tuple[str, ...]) -> float:
    engagement = (
        math.log1p(views) * 1.0
        + math.log1p(comments) * 1.8
        + math.log1p(recommends) * 1.4
    )
    return engagement + _score_title(title, keywords)


def _fetch_gallery_rows(client: httpx.Client, gallery: DcGallery, limit: int) -> list[DcPost]:
    response = client.get(gallery.list_url)
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

        views_text = views.get_text(" ", strip=True) if views else "0"
        recommends_text = recommends.get_text(" ", strip=True) if recommends else "0"
        comments_text = clean_html_text(reply.get_text(" ", strip=True)).strip("[]") if reply else "0"
        score = _score_post(
            title=title,
            views=_parse_count(views_text),
            recommends=_parse_count(recommends_text),
            comments=_parse_count(comments_text),
            keywords=gallery.keywords,
        )
        posts.append(
            DcPost(
                source_id=gallery.gallery_id,
                source_title=gallery.title,
                source_link=gallery.list_url,
                title=title,
                link=link,
                author=author.get("data-nick", "").strip() if author else "",
                published_at=date.get("title", "").strip() if date else "",
                views=views_text,
                recommends=recommends_text,
                comments=comments_text,
                excerpt="",
                score=score,
            )
        )
        if len(posts) >= limit:
            break
    return posts


def fetch_dc_semiconductor_posts(limit: int = 30) -> list[DcPost]:
    return fetch_gallery_posts(SEMICONDUCTOR_GALLERY, limit=limit)


def fetch_gallery_posts(gallery: DcGallery, limit: int = 30) -> list[DcPost]:
    with httpx.Client(timeout=15, headers=DEFAULT_HEADERS) as client:
        posts = _fetch_gallery_rows(client, gallery=gallery, limit=limit)
        top_links = {post.link for post in sorted(posts, key=lambda item: item.score, reverse=True)[: gallery.curated_limit]}
        for post in posts:
            if post.link in top_links:
                post.excerpt = _fetch_post_excerpt(client, post.link)
                if post.excerpt:
                    post.score += min(2.5, len(post.excerpt) / 350)
        posts.sort(key=lambda item: item.score, reverse=True)
        return posts


def fetch_curated_dc_bundle(limit_per_gallery: int = 30) -> dict:
    galleries_payload: list[dict] = []
    featured_posts: list[DcPost] = []
    generated_posts: list[DcPost] = []

    for gallery in CURATED_GALLERIES:
        posts = fetch_gallery_posts(gallery, limit=limit_per_gallery)
        selected_posts = posts[: gallery.curated_limit]
        generated_posts.extend(selected_posts)
        galleries_payload.append(
            {
                "gallery_id": gallery.gallery_id,
                "title": gallery.title,
                "source_link": gallery.list_url,
                "total_posts": len(posts),
                "selected_posts": [post.to_dict() for post in selected_posts],
            }
        )
        featured_posts.extend(selected_posts)

    featured_posts.sort(key=lambda item: item.score, reverse=True)
    return {
        "galleries": galleries_payload,
        "featured_posts": [post.to_dict() for post in featured_posts[:12]],
        "selected_posts": generated_posts,
    }
