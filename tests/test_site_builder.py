import json
from pathlib import Path

from blog_tracker.site_builder import build_site, merge_archive


def test_merge_archive_deduplicates_by_guid():
    existing = [
        {
            "blog_id": "blog-1",
            "guid": "post-1",
            "published_at": "2026-03-29T10:00:00+09:00",
            "classification": "미분류",
            "group_name": "미분류",
            "display_name": "작성자1",
            "blog_title": "블로그1",
            "title": "기존 글",
            "summary": "기존 요약",
            "link": "https://example.com/1",
            "tags": [],
            "has_content": True,
        }
    ]
    payloads = [
        {
            "posts": [
                {
                    "blog_id": "blog-1",
                    "guid": "post-1",
                    "published_at": "2026-03-30T10:00:00+09:00",
                    "classification": "기업분석",
                    "group_name": "핵심",
                    "display_name": "작성자1",
                    "blog_title": "블로그1",
                    "title": "업데이트 글",
                    "summary": "새 요약",
                    "link": "https://example.com/1-new",
                    "tags": ["태그"],
                    "has_content": True,
                },
                {
                    "blog_id": "blog-2",
                    "guid": "post-2",
                    "published_at": "2026-03-28T10:00:00+09:00",
                    "classification": "반도체",
                    "group_name": "관심",
                    "display_name": "작성자2",
                    "blog_title": "블로그2",
                    "title": "새 글",
                    "summary": "설명",
                    "link": "https://example.com/2",
                    "tags": [],
                    "has_content": False,
                },
            ]
        }
    ]

    merged = merge_archive(existing, payloads, priority_bloggers={"post-1"}, max_posts=10)
    assert len(merged) == 2
    assert merged[0]["guid"] == "post-1"
    assert merged[0]["classification"] == "기업분석"


def test_build_site_writes_archive_and_index(tmp_path: Path):
    output_dir = tmp_path / "output"
    archive_dir = tmp_path / "data" / "site"
    site_dir = tmp_path / "site"
    output_dir.mkdir(parents=True)

    payload = {
        "generated_at": "2026-03-30T20:00:00+09:00",
        "post_count": 1,
        "posts": [
                {
                    "blog_id": "blog-1",
                    "guid": "post-1",
                    "published_at": "2026-03-30T19:00:00+09:00",
                "classification": "기업분석",
                "group_name": "핵심",
                "display_name": "작성자1",
                "blog_title": "블로그1",
                "title": "테스트 글",
                "summary": "테스트 요약",
                "link": "https://example.com/1",
                "tags": ["테스트"],
                "has_content": True,
            },
            {
                "blog_id": "ruffian71",
                "guid": "life-1",
                "published_at": "2026-03-30T18:00:00+09:00",
                "classification": "기업분석",
                "group_name": "통신",
                "display_name": "상실의 시대",
                "blog_title": "상실의 시대",
                "title": "일상 테스트 글",
                "summary": "별도 페이지로 이동해야 하는 글",
                "link": "https://blog.naver.com/ruffian71/1",
                "tags": [],
                "has_content": True,
            },
        ],
    }
    (output_dir / "digest_20260330_200000.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    archive = build_site(output_dir=output_dir, archive_dir=archive_dir, site_dir=site_dir)

    assert archive["post_count"] == 2
    assert (site_dir / "index.html").exists()
    assert (site_dir / "life.html").exists()
    assert (site_dir / "data" / "archive.json").exists()
    assert (site_dir / "data" / "life_posts.json").exists()
    assert (site_dir / "data" / "external_sources.json").exists()
    assert json.loads((site_dir / "data" / "archive.json").read_text(encoding="utf-8"))["posts"][0]["guid"] == "post-1"
    life_posts = json.loads((site_dir / "data" / "life_posts.json").read_text(encoding="utf-8"))
    assert life_posts["post_count"] == 1
    assert life_posts["posts"][0]["blog_id"] == "ruffian71"
    external_sources = json.loads((site_dir / "data" / "external_sources.json").read_text(encoding="utf-8"))
    assert "sources" in external_sources
    html = (site_dir / "index.html").read_text(encoding="utf-8")
    life_html = (site_dir / "life.html").read_text(encoding="utf-8")
    assert "./life.html" in html
    assert "상실의 시대 글 모음" in life_html
    assert "우선 블로거 전용 보드" in html
    assert "오늘" in html
    assert "우선 블로거 목록" in html
    assert "상실의 시대 별도 페이지" in html
    assert html.index('id="posts"') < html.index('id="life-board"')
    assert "외부 소스 링크 허브" in html
    assert "PC 최적화" in html
    assert "모바일 최적화" in html
