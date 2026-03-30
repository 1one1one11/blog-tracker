import json
from pathlib import Path

from blog_tracker.site_builder import build_site, merge_archive


def test_merge_archive_deduplicates_by_guid():
    existing = [
        {
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

    merged = merge_archive(existing, payloads, max_posts=10)
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
            }
        ],
    }
    (output_dir / "digest_20260330_200000.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    archive = build_site(output_dir=output_dir, archive_dir=archive_dir, site_dir=site_dir)

    assert archive["post_count"] == 1
    assert (site_dir / "index.html").exists()
    assert (site_dir / "data" / "archive.json").exists()
    assert json.loads((site_dir / "data" / "archive.json").read_text(encoding="utf-8"))["posts"][0]["guid"] == "post-1"
