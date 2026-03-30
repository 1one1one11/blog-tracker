from __future__ import annotations

import csv
import re
from pathlib import Path


HEADER = ["blog_id", "display_name", "blog_title", "group_name", "relationship", "enabled", "rss_url", "notes"]


def parse_followings_dump(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    rows: list[dict[str, str]] = []
    current_group = "미분류"
    current_relationship = "이웃"

    for index, line in enumerate(lines):
        if line in {"dummy", "그룹전체", "이웃전체", "새글소식전체", "최근 글", "이웃추가일"}:
            continue
        if "|" in line:
            blog_id, blog_title = [part.strip() for part in line.split("|", 1)]
            if not blog_id:
                continue
            rows.append(
                {
                    "blog_id": blog_id,
                    "display_name": blog_id,
                    "blog_title": blog_title,
                    "group_name": current_group,
                    "relationship": current_relationship,
                    "enabled": "true",
                    "rss_url": "",
                    "notes": "" if re.fullmatch(r"[A-Za-z0-9_\\-]+", blog_id) else "실제 naver blog_id 확인 필요",
                }
            )
            continue
        if line in {"이웃", "서로이웃"}:
            current_relationship = line
            continue
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if next_line in {"이웃", "서로이웃"} and line != "dummy":
            current_group = line

    deduped: dict[str, dict[str, str]] = {}
    for row in rows:
        deduped[row["blog_id"]] = row
    return list(deduped.values())


def write_blogs_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)
