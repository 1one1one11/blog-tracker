from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from blog_tracker.classifier import classify_post
from blog_tracker.config import load_blog_sources, load_settings
from blog_tracker.rss import fetch_post_content, fetch_recent_posts
from blog_tracker.state import load_seen_guids, save_seen_guids
from blog_tracker.summarizer import Summarizer
from blog_tracker.telegram import build_digest, send_digest


def format_console_report(posts) -> str:
    grouped = defaultdict(list)
    for post in posts:
        grouped[post.classification].append(post)
    lines = [f"새 글 {len(posts)}건"]
    for group_name, group_posts in grouped.items():
        lines.append(f"- {group_name}: {len(group_posts)}건")
    return "\n".join(lines)


def enrich_post(post):
    post.content_text = fetch_post_content(post.link)
    post.classification = classify_post(post)
    return post


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    sources = load_blog_sources(settings.blogs_csv_path)
    seen_guids = load_seen_guids(settings.state_path)
    days_back = args.days_back or settings.days_back

    fresh_posts = []
    for source in sources:
        for post in fetch_recent_posts(source, days_back=days_back):
            if post.guid in seen_guids:
                continue
            fresh_posts.append(post)

    if not fresh_posts:
        print("새 글이 없습니다.")
        return 0

    enriched_posts = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(enrich_post, post) for post in fresh_posts]
        for future in as_completed(futures):
            enriched_posts.append(future.result())

    enriched_posts.sort(key=lambda item: item.published_at, reverse=True)
    summarizer = Summarizer(
        settings.openai_api_key,
        settings.openai_model,
        settings.gemini_api_key,
        settings.gemini_model,
    )
    enriched_posts = summarizer.summarize_all(enriched_posts)
    digest = build_digest(enriched_posts)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    digest_path = settings.output_dir / f"digest_{timestamp}.md"
    digest_path.write_text(digest, encoding="utf-8")

    print(format_console_report(enriched_posts))
    print(f"리포트 저장: {digest_path}")

    if not args.dry_run:
        result = send_digest(settings.telegram_bot_token, settings.telegram_chat_id, digest)
        print(f"텔레그램: {result['ok']}")

    seen_guids.update(post.guid for post in enriched_posts)
    save_seen_guids(settings.state_path, seen_guids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
