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


def load_archive_guids(path: Path) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"Archive data not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(post.get("guid") or "").strip() for post in payload.get("posts", []) if post.get("guid")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate that priority blogger RSS posts reached the dashboard data.")
    parser.add_argument("--blogs-csv", default=str(ROOT / "config" / "blogs.csv"))
    parser.add_argument("--priority-file", default=str(ROOT / "config" / "priority_bloggers.txt"))
    parser.add_argument("--site-data", default=str(ROOT / "site" / "data" / "archive.json"))
    parser.add_argument("--days-back", type=int, default=4)
    parser.add_argument("--timezone", default="Asia/Seoul")
    args = parser.parse_args()

    priority_bloggers = load_priority_bloggers(Path(args.priority_file))
    if not priority_bloggers:
        print("No priority bloggers configured.")
        return 0

    sources = ensure_priority_blog_sources(load_blog_sources(Path(args.blogs_csv)), priority_bloggers)
    priority_sources = [source for source in sources if source.blog_id in priority_bloggers]
    missing_sources = sorted(priority_bloggers - {source.blog_id for source in priority_sources})
    if missing_sources:
        print("Priority bloggers missing from source list after merge:")
        for blog_id in missing_sources:
            print(f"- {blog_id}")
        return 1

    archive_guids = load_archive_guids(Path(args.site_data))
    missing_posts: list[tuple[str, str, str]] = []
    live_count = 0
    for source in sorted(priority_sources, key=lambda item: item.blog_id):
        posts = fetch_recent_posts(source, days_back=args.days_back, timezone_name=args.timezone)
        live_count += len(posts)
        for post in posts:
            if post.guid not in archive_guids:
                missing_posts.append((source.blog_id, post.title, post.guid))

    if missing_posts:
        print("Priority blogger posts missing from dashboard archive:")
        for blog_id, title, guid in missing_posts:
            print(f"- {blog_id}: {title} ({guid})")
        print(f"Checked {len(priority_sources)} priority bloggers and {live_count} recent RSS posts.")
        return 1

    print(f"Priority dashboard check passed: {len(priority_sources)} bloggers, {live_count} recent RSS posts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
