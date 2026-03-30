from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from blog_tracker.site_builder import build_site


def main() -> int:
    archive = build_site(
        output_dir=ROOT / "output",
        archive_dir=ROOT / "data" / "site",
        site_dir=ROOT / "site",
    )
    print(f"사이트 아카이브 포스트 수: {archive['post_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
