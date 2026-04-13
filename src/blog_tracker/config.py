from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from blog_tracker.models import BlogSource

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class TelegramDestination:
    bot_token: str
    chat_id: str


@dataclass(slots=True)
class Settings:
    root_dir: Path
    blogs_csv_path: Path
    priority_bloggers_path: Path
    state_path: Path
    output_dir: Path
    timezone: str
    days_back: int
    telegram_bot_token: str
    telegram_bot_tokens: list[str]
    telegram_chat_id: str
    telegram_extra_chat_id: str
    telegram_destinations: list[TelegramDestination]
    dashboard_url: str
    openai_api_key: str
    openai_model: str
    gemini_api_key: str
    gemini_model: str


def _split_env_list(value: str) -> list[str]:
    return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]


def _unique_nonempty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _parse_extra_destinations(value: str) -> list[TelegramDestination]:
    destinations: list[TelegramDestination] = []
    for item in _split_env_list(value):
        if "|" in item:
            bot_token, chat_id = item.split("|", 1)
        elif "::" in item:
            bot_token, chat_id = item.split("::", 1)
        else:
            continue
        bot_token = bot_token.strip()
        chat_id = chat_id.strip()
        if bot_token and chat_id:
            destinations.append(TelegramDestination(bot_token=bot_token, chat_id=chat_id))
    return destinations


def _unique_destinations(destinations: list[TelegramDestination]) -> list[TelegramDestination]:
    seen: set[tuple[str, str]] = set()
    unique: list[TelegramDestination] = []
    for destination in destinations:
        key = (destination.bot_token, destination.chat_id)
        if key not in seen:
            seen.add(key)
            unique.append(destination)
    return unique


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    runtime_dir = ROOT / "data" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    output_dir = ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    telegram_extra_chat_id = os.getenv("TELEGRAM_EXTRA_CHAT_ID", "").strip()
    default_bot_tokens = _unique_nonempty([telegram_bot_token] + _split_env_list(os.getenv("TELEGRAM_BOT_TOKENS", "")))
    extra_bot_tokens = _unique_nonempty(_split_env_list(os.getenv("TELEGRAM_EXTRA_BOT_TOKENS", "")))
    telegram_bot_tokens = _unique_nonempty(default_bot_tokens + extra_bot_tokens)
    telegram_destinations = [
        TelegramDestination(bot_token=bot_token, chat_id=telegram_chat_id)
        for bot_token in default_bot_tokens
        if telegram_chat_id
    ]
    extra_chat_id = telegram_extra_chat_id or telegram_chat_id
    telegram_destinations.extend(
        TelegramDestination(bot_token=bot_token, chat_id=extra_chat_id)
        for bot_token in extra_bot_tokens
        if extra_chat_id
    )
    telegram_destinations = _unique_destinations(
        telegram_destinations + _parse_extra_destinations(os.getenv("TELEGRAM_EXTRA_DESTINATIONS", ""))
    )
    return Settings(
        root_dir=ROOT,
        blogs_csv_path=ROOT / "config" / "blogs.csv",
        priority_bloggers_path=ROOT / "config" / "priority_bloggers.txt",
        state_path=runtime_dir / "state.json",
        output_dir=output_dir,
        timezone=os.getenv("BLOG_TRACKER_TIMEZONE", "Asia/Seoul"),
        days_back=int(os.getenv("BLOG_TRACKER_DAYS_BACK", "4")),
        telegram_bot_token=telegram_bot_token,
        telegram_bot_tokens=telegram_bot_tokens,
        telegram_chat_id=telegram_chat_id,
        telegram_extra_chat_id=telegram_extra_chat_id,
        telegram_destinations=telegram_destinations,
        dashboard_url=os.getenv("BLOG_TRACKER_DASHBOARD_URL", "https://1one1one11.github.io/blog-tracker/").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "").strip(),
    )


def load_blog_sources(csv_path: Path) -> list[BlogSource]:
    rows: list[BlogSource] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            enabled = row.get("enabled", "true").strip().lower() not in {"false", "0", "no", "n"}
            rows.append(
                BlogSource(
                    blog_id=row["blog_id"].strip(),
                    display_name=row.get("display_name", "").strip() or row["blog_id"].strip(),
                    blog_title=row.get("blog_title", "").strip(),
                    group_name=row.get("group_name", "").strip() or "미분류",
                    relationship=row.get("relationship", "").strip() or "이웃",
                    enabled=enabled,
                    rss_url=row.get("rss_url", "").strip() or None,
                    notes=row.get("notes", "").strip(),
                )
            )
    return [row for row in rows if row.enabled]


def load_priority_bloggers(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
