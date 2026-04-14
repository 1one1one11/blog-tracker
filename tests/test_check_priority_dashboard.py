from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

from blog_tracker.models import BlogPost, BlogSource


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_priority_dashboard.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_priority_dashboard", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_post(blog_id: str, guid: str, title: str) -> BlogPost:
    return BlogPost(
        blog_id=blog_id,
        display_name=blog_id,
        blog_title=f"{blog_id} blog",
        group_name="investment",
        title=title,
        link=f"https://example.com/{guid}",
        guid=guid,
        published_at=datetime(2026, 4, 14, tzinfo=timezone.utc),
    )


def write_payload(path: Path, guids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-14T09:00:00+09:00",
                "posts": [
                    {
                        "guid": guid,
                        "blog_id": "priority-blog",
                        "title": guid,
                        "link": f"https://example.com/{guid}",
                    }
                    for guid in guids
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["blog_id,display_name,blog_title,group_name,relationship,enabled,rss_url,notes"]
    for blog_id, display_name in rows:
        lines.append(f"{blog_id},{display_name},{display_name},미분류,이웃,true,,")
    path.write_text("\n".join(lines), encoding="utf-8")


def test_checker_fails_when_priority_bloggers_drop_out_of_raw_csv(tmp_path: Path, monkeypatch, capsys):
    module = load_script()
    blogs_csv = tmp_path / "config" / "blogs.csv"
    priority_file = tmp_path / "config" / "priority_bloggers.txt"
    output_latest = tmp_path / "output" / "latest.json"
    docs_latest = tmp_path / "docs" / "data" / "latest.json"
    archive_data = tmp_path / "data" / "site" / "archive.json"
    site_data = tmp_path / "site" / "data" / "archive.json"

    write_csv(blogs_csv, [("existing", "Existing")])
    priority_file.parent.mkdir(parents=True, exist_ok=True)
    priority_file.write_text("existing\npriority-blog\n", encoding="utf-8")

    monkeypatch.setattr(module, "fetch_recent_posts", lambda source, days_back, timezone_name: [make_post("priority-blog", "guid-1", "Priority title")])
    monkeypatch.setattr(
        "sys.argv",
        [
            "check_priority_dashboard.py",
            "--blogs-csv",
            str(blogs_csv),
            "--priority-file",
            str(priority_file),
            "--output-latest",
            str(output_latest),
            "--docs-latest",
            str(docs_latest),
            "--archive-data",
            str(archive_data),
            "--site-data",
            str(site_data),
        ],
    )

    assert module.main() == 1
    captured = capsys.readouterr().out
    assert "config/blogs.csv" in captured
    assert "priority-blog" in captured


def test_checker_fails_when_one_dashboard_file_lags(tmp_path: Path, monkeypatch, capsys):
    module = load_script()
    blogs_csv = tmp_path / "config" / "blogs.csv"
    priority_file = tmp_path / "config" / "priority_bloggers.txt"
    output_latest = tmp_path / "output" / "latest.json"
    docs_latest = tmp_path / "docs" / "data" / "latest.json"
    archive_data = tmp_path / "data" / "site" / "archive.json"
    site_data = tmp_path / "site" / "data" / "archive.json"

    write_csv(blogs_csv, [("priority-blog", "Priority")])
    priority_file.parent.mkdir(parents=True, exist_ok=True)
    priority_file.write_text("priority-blog\n", encoding="utf-8")

    monkeypatch.setattr(
        module,
        "fetch_recent_posts",
        lambda source, days_back, timezone_name: [
            make_post("priority-blog", "guid-1", "Priority title"),
            make_post("priority-blog", "guid-2", "Second title"),
        ],
    )

    write_payload(output_latest, ["guid-1", "guid-2"])
    write_payload(docs_latest, ["guid-1"])
    write_payload(archive_data, ["guid-1", "guid-2"])
    write_payload(site_data, ["guid-1", "guid-2"])

    monkeypatch.setattr(
        "sys.argv",
        [
            "check_priority_dashboard.py",
            "--blogs-csv",
            str(blogs_csv),
            "--priority-file",
            str(priority_file),
            "--output-latest",
            str(output_latest),
            "--docs-latest",
            str(docs_latest),
            "--archive-data",
            str(archive_data),
            "--site-data",
            str(site_data),
        ],
    )

    assert module.main() == 1
    captured = capsys.readouterr().out
    assert "docs/data/latest.json" in captured
    assert "guid-2" in captured
