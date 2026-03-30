from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from blog_tracker.models import BlogSource

ROOT = Path(__file__).resolve().parents[2]


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
    telegram_chat_id: str
    openai_api_key: str
    openai_model: str
    gemini_api_key: str
    gemini_model: str


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    runtime_dir = ROOT / "data" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    output_dir = ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        root_dir=ROOT,
        blogs_csv_path=ROOT / "config" / "blogs.csv",
        priority_bloggers_path=ROOT / "config" / "priority_bloggers.txt",
        state_path=runtime_dir / "state.json",
        output_dir=output_dir,
        timezone=os.getenv("BLOG_TRACKER_TIMEZONE", "Asia/Seoul"),
        days_back=int(os.getenv("BLOG_TRACKER_DAYS_BACK", "3")),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
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
