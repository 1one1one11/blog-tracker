import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from blog_tracker.followings import scrape_followings, write_blogs_csv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", default=str(ROOT / "config" / "blogs.csv"))
    args = parser.parse_args()

    rows = scrape_followings(args.url)
    write_blogs_csv(rows, Path(args.output))
    print(f"{len(rows)}개 블로그를 동기화했습니다: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
