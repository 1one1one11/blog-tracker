import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from blog_tracker.followings import scrape_followings, write_blogs_csv


def load_manual_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", default=str(ROOT / "config" / "blogs.csv"))
    args = parser.parse_args()

    rows = scrape_followings(args.url)
    manual_path = ROOT / "config" / "manual_blogs.csv"
    rows.extend(load_manual_rows(manual_path))
    rows = list({row["blog_id"]: row for row in rows}.values())
    write_blogs_csv(rows, Path(args.output))
    print(f"{len(rows)}개 블로그를 동기화했습니다: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
