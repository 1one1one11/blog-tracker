from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from blog_tracker.config import ensure_priority_blog_sources, load_blog_sources, load_priority_bloggers
from blog_tracker.rss import fetch_recent_posts


def load_post_guids(path: Path) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"Dashboard data not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(post.get("guid") or "").strip() for post in payload.get("posts", []) if post.get("guid")}


def load_live_priority_posts(priority_sources, days_back: int, timezone_name: str) -> dict[str, tuple[str, str, str]]:
    live_posts: dict[str, tuple[str, str, str]] = {}
    for source in sorted(priority_sources, key=lambda item: item.blog_id):
        posts = fetch_recent_posts(source, days_back=days_back, timezone_name=timezone_name)
        for post in posts:
            live_posts[post.guid] = (source.blog_id, post.title, post.link)
    return live_posts


def report_missing(label: str, missing: list[tuple[str, str, str]]) -> None:
    print(f"Priority blogger posts missing from {label}:")
    for blog_id, title, link in missing:
        print(f"- {blog_id}: {title} ({link})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate that priority blogger RSS posts reached the dashboard data.")
    parser.add_argument("--blogs-csv", default=str(ROOT / "config" / "blogs.csv"))
    parser.add_argument("--priority-file", default=str(ROOT / "config" / "priority_bloggers.txt"))
    parser.add_argument("--output-latest", default=str(ROOT / "output" / "latest.json"))
    parser.add_argument("--docs-latest", default=str(ROOT / "docs" / "data" / "latest.json"))
    parser.add_argument("--archive-data", default=str(ROOT / "data" / "site" / "archive.json"))
    parser.add_argument("--site-data", default=str(ROOT / "site" / "data" / "archive.json"))
    parser.add_argument("--days-back", type=int, default=4)
    parser.add_argument("--timezone", default="Asia/Seoul")
    args = parser.parse_args()

    priority_bloggers = load_priority_bloggers(Path(args.priority_file))
    if not priority_bloggers:
        print("No priority bloggers configured.")
        return 0

    raw_sources = load_blog_sources(Path(args.blogs_csv))
    raw_source_ids = {source.blog_id for source in raw_sources}
    missing_from_csv = sorted(priority_bloggers - raw_source_ids)
    if missing_from_csv:
        print("Priority bloggers missing from config/blogs.csv before merge:")
        for blog_id in missing_from_csv:
            print(f"- {blog_id}")
        return 1

    sources = ensure_priority_blog_sources(raw_sources, priority_bloggers)
    priority_sources = [source for source in sources if source.blog_id in priority_bloggers]
    missing_sources = sorted(priority_bloggers - {source.blog_id for source in priority_sources})
    if missing_sources:
        print("Priority bloggers missing from source list after merge:")
        for blog_id in missing_sources:
            print(f"- {blog_id}")
        return 1

    live_posts = load_live_priority_posts(priority_sources, days_back=args.days_back, timezone_name=args.timezone)
    if not live_posts:
        print(f"Priority dashboard check passed: {len(priority_sources)} bloggers, 0 recent RSS posts.")
        return 0

    # latest.json can represent only the current run's fresh digest when runtime
    # state is restored in CI. The deploy gate should validate persistent
    # dashboard archives, which are what the site actually renders from.
    targets = [
        ("data/site/archive.json", Path(args.archive_data)),
        ("site/data/archive.json", Path(args.site_data)),
    ]

    failed = False
    for label, path in targets:
        target_guids = load_post_guids(path)
        missing = [
            (blog_id, title, link)
            for guid, (blog_id, title, link) in live_posts.items()
            if guid not in target_guids
        ]
        if missing:
            report_missing(label, missing)
            print(f"Checked {len(priority_sources)} priority bloggers and {len(live_posts)} recent RSS posts.")
            failed = True

    if failed:
        return 1

    print(f"Priority dashboard check passed: {len(priority_sources)} bloggers, {len(live_posts)} recent RSS posts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
