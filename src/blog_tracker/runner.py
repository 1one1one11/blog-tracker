from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from blog_tracker.classifier import classify_post
from blog_tracker.config import load_blog_sources, load_priority_bloggers, load_settings
from blog_tracker.dc_gallery import CURATED_GALLERIES, DcPost, fetch_curated_dc_bundle
from blog_tracker.reporting import build_digest_payload, write_digest_payload
from blog_tracker.rss import fetch_post_content, fetch_recent_posts
from blog_tracker.state import load_seen_guids, save_seen_guids
from blog_tracker.summarizer import Summarizer
from blog_tracker.telegram import build_digest, build_digest_messages, send_digest_messages


def format_console_report(label: str, posts) -> str:
    grouped = defaultdict(list)
    for post in posts:
        grouped[post.classification].append(post)
    lines = [f"{label}: {len(posts)}"]
    for group_name, group_posts in grouped.items():
        lines.append(f"- {group_name}: {len(group_posts)}")
    return "\n".join(lines)


def enrich_post(post):
    post.content_text = fetch_post_content(post.link)
    post.classification = classify_post(post)
    return post


def export_dashboard_json(settings, posts, priority_bloggers: set[str], generated_at: datetime) -> None:
    docs_data_dir = settings.root_dir / "docs" / "data"
    docs_data_dir.mkdir(parents=True, exist_ok=True)

    classification_counts = Counter(post.classification or "unclassified" for post in posts)
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


def empty_dc_bundle() -> dict:
    return {"galleries": [], "featured_posts": []}


def export_dc_gallery_json(settings, generated_at: datetime, bundle: dict | None = None) -> None:
    docs_data_dir = settings.root_dir / "docs" / "data"
    docs_data_dir.mkdir(parents=True, exist_ok=True)
    bundle = bundle or fetch_curated_dc_bundle(limit_per_gallery=30)

    community_payload = {
        "generated_at": generated_at.isoformat(),
        "source_title": "DC stock gallery curation",
        "total_posts": sum(section["total_posts"] for section in bundle["galleries"]),
        "featured_posts": bundle["featured_posts"],
        "galleries": bundle["galleries"],
    }
    legacy_payload = {
        "generated_at": generated_at.isoformat(),
        "source_title": "DC community picks",
        "source_link": CURATED_GALLERIES[0].list_url,
        "total_posts": len(bundle["featured_posts"]),
        "posts": bundle["featured_posts"],
    }

    for path in [settings.output_dir / "dc_community.json", docs_data_dir / "dc_community.json"]:
        path.write_text(json.dumps(community_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for path in [settings.output_dir / "dc_semiconductor.json", docs_data_dir / "dc_semiconductor.json"]:
        path.write_text(json.dumps(legacy_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def flatten_dc_selected_posts(bundle: dict) -> list[DcPost]:
    posts: list[DcPost] = []
    for gallery in bundle["galleries"]:
        for item in gallery["selected_posts"]:
            posts.append(
                DcPost(
                    source_id=item["source_id"],
                    source_title=item["source_title"],
                    source_link=item["source_link"],
                    title=item["title"],
                    link=item["link"],
                    author=item["author"],
                    published_at=item["published_at"],
                    views=item["views"],
                    recommends=item["recommends"],
                    comments=item["comments"],
                    excerpt=item["excerpt"],
                    summary=item.get("summary", ""),
                    score=float(item.get("score", 0.0)),
                )
            )
    return posts


def summarize_dc_posts(summarizer: Summarizer, posts: list[DcPost]) -> None:
    for post in posts:
        fallback = post.excerpt[:220] + ("..." if len(post.excerpt) > 220 else "") if post.excerpt else "Open the original post for details."
        prompt = (
            f"Summarize this DCInside post from {post.source_title} in Korean using at most 2 sentences. "
            "Prioritize market context, sector trend, ticker discussion, and investor sentiment. "
            "If it is mostly chatter, summarize the mood briefly.\n\n"
            f"Title: {post.title}\n"
            f"Author: {post.author}\n"
            f"Excerpt: {post.excerpt[:3000]}"
        )
        post.summary = summarizer.summarize_text(prompt, fallback)


def inject_dc_summaries(bundle: dict, summarized_posts: list[DcPost]) -> dict:
    summary_map = {post.link: post.summary for post in summarized_posts}
    for gallery in bundle["galleries"]:
        for item in gallery["selected_posts"]:
            item["summary"] = summary_map.get(item["link"], item.get("summary", ""))
    for item in bundle["featured_posts"]:
        item["summary"] = summary_map.get(item["link"], item.get("summary", ""))
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    sources = load_blog_sources(settings.blogs_csv_path)
    priority_bloggers = load_priority_bloggers(settings.priority_bloggers_path)
    seen_guids = load_seen_guids(settings.state_path)
    days_back = args.days_back if args.days_back is not None else settings.days_back

    recent_post_map = {}
    for source in sources:
        for post in fetch_recent_posts(source, days_back=days_back, timezone_name=settings.timezone):
            recent_post_map[post.guid] = post

    if not recent_post_map:
        print("No recent blog posts found.")
        generated_at = datetime.now().astimezone()
        export_dashboard_json(settings, [], priority_bloggers, generated_at)
        export_dc_gallery_json(settings, generated_at, empty_dc_bundle())
        return 0

    recent_posts = list(recent_post_map.values())
    recent_posts.sort(key=lambda item: (item.blog_id not in priority_bloggers, -item.published_at.timestamp()))

    enriched_posts = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(enrich_post, post) for post in recent_posts]
        for future in as_completed(futures):
            enriched_posts.append(future.result())

    enriched_posts.sort(key=lambda item: (item.blog_id not in priority_bloggers, -item.published_at.timestamp()))
    summarizer = Summarizer(
        settings.openai_api_key,
        settings.openai_model,
        settings.gemini_api_key,
        settings.gemini_model,
    )
    enriched_posts = summarizer.summarize_all(enriched_posts)

    dc_bundle = fetch_curated_dc_bundle(limit_per_gallery=30)
    dc_posts = flatten_dc_selected_posts(dc_bundle)
    summarize_dc_posts(summarizer, dc_posts)
    dc_bundle = inject_dc_summaries(dc_bundle, dc_posts)

    fresh_posts = [post for post in enriched_posts if post.guid not in seen_guids]
    digest = build_digest(fresh_posts) if fresh_posts else ""
    digest_messages = build_digest_messages(
        fresh_posts,
        dc_posts=dc_posts,
        priority_bloggers=priority_bloggers,
    ) if (fresh_posts or dc_posts) else []

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
    export_dc_gallery_json(settings, generated_at, dc_bundle)

    print(format_console_report("Recent blog posts", enriched_posts))
    print(format_console_report("Fresh blog posts", fresh_posts))
    print(f"Priority bloggers total: {len([post for post in enriched_posts if post.blog_id in priority_bloggers])}")
    print(f"Priority bloggers fresh: {len([post for post in fresh_posts if post.blog_id in priority_bloggers])}")
    print(f"Curated DC posts: {len(dc_posts)}")
    print(f"Digest path: {digest_path}")
    print(f"Digest JSON path: {digest_json_path}")
    print(f"Telegram message count: {len(digest_messages)}")

    should_persist_state = True
    if digest_messages and not args.dry_run:
        results = send_digest_messages(settings.telegram_bot_token, settings.telegram_chat_id, digest_messages)
        all_ok = all(result["ok"] for result in results)
        print(f"Telegram success: {all_ok}")
        should_persist_state = all_ok

    if should_persist_state:
        seen_guids.update(post.guid for post in fresh_posts)
        save_seen_guids(settings.state_path, seen_guids)
        return 0

    print("Skipping state save because Telegram delivery failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
