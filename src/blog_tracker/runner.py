from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from blog_tracker.classifier import classify_post
from blog_tracker.config import load_blog_sources, load_priority_bloggers, load_settings
from blog_tracker.reporting import build_digest_payload, write_digest_payload
from blog_tracker.rss import fetch_post_content, fetch_recent_posts
from blog_tracker.state import load_seen_guids, save_seen_guids
from blog_tracker.summarizer import Summarizer
from blog_tracker.telegram import build_digest, build_digest_messages, send_digest_messages


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


def export_dashboard_json(settings, posts, priority_bloggers: set[str], generated_at: datetime) -> None:
    docs_data_dir = settings.root_dir / "docs" / "data"
    docs_data_dir.mkdir(parents=True, exist_ok=True)

    classification_counts = Counter(post.classification or "미분류" for post in posts)
    payload = {
        "generated_at": generated_at.isoformat(),
        "total_posts": len(posts),
        "priority_post_count": sum(1 for post in posts if post.blog_id in priority_bloggers),
        "classification_counts": dict(sorted(classification_counts.items())),
        "priority_bloggers": sorted(priority_bloggers),
        "posts": [
            {
                "blog_id": post.blog_id,
                "display_name": post.display_name,
                "blog_title": post.blog_title,
                "group_name": post.group_name,
                "title": post.title,
                "link": post.link,
                "guid": post.guid,
                "published_at": post.published_at.isoformat(),
                "category": post.category,
                "tags": post.tags,
                "summary": post.summary,
                "classification": post.classification,
                "is_priority": post.blog_id in priority_bloggers,
            }
            for post in posts
        ],
    }
    for path in [settings.output_dir / "latest.json", docs_data_dir / "latest.json"]:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    sources = load_blog_sources(settings.blogs_csv_path)
    priority_bloggers = load_priority_bloggers(settings.priority_bloggers_path)
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

    enriched_posts.sort(
        key=lambda item: (item.blog_id not in priority_bloggers, -item.published_at.timestamp())
    )
    summarizer = Summarizer(
        settings.openai_api_key,
        settings.openai_model,
        settings.gemini_api_key,
        settings.gemini_model,
    )
    enriched_posts = summarizer.summarize_all(enriched_posts)
    digest = build_digest(enriched_posts)
    digest_messages = build_digest_messages(enriched_posts, priority_bloggers=priority_bloggers)

    generated_at = datetime.now().astimezone()
    timestamp = generated_at.strftime("%Y%m%d_%H%M%S")
    digest_path = settings.output_dir / f"digest_{timestamp}.md"
    digest_json_path = settings.output_dir / f"digest_{timestamp}.json"
    digest_path.write_text(digest, encoding="utf-8")
    write_digest_payload(
        digest_json_path,
        build_digest_payload(
            enriched_posts,
            generated_at=generated_at,
            days_back=days_back,
            priority_bloggers=priority_bloggers,
        ),
    )
    export_dashboard_json(settings, enriched_posts, priority_bloggers, generated_at)

    print(format_console_report(enriched_posts))
    print(f"우선 블로거: {len([post for post in enriched_posts if post.blog_id in priority_bloggers])}건")
    print(f"리포트 저장: {digest_path}")
    print(f"리포트 JSON 저장: {digest_json_path}")
    print(f"텔레그램 메시지 수: {len(digest_messages)}")

    should_persist_state = True
    if not args.dry_run:
        results = send_digest_messages(settings.telegram_bot_token, settings.telegram_chat_id, digest_messages)
        all_ok = all(result["ok"] for result in results)
        print(f"텔레그램: {all_ok}")
        should_persist_state = all_ok

    if should_persist_state:
        seen_guids.update(post.guid for post in enriched_posts)
        save_seen_guids(settings.state_path, seen_guids)
        return 0

    print("텔레그램 발송 실패로 state 저장을 건너뜁니다.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
