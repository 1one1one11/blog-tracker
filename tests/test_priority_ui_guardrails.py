from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _block(text: str, start: str, end: str) -> str:
    assert start in text, f"Missing start marker: {start}"
    assert end in text, f"Missing end marker: {end}"
    return text.split(start, 1)[1].split(end, 1)[0]


def test_site_builder_priority_board_is_not_truncated():
    text = (ROOT / "src" / "blog_tracker" / "site_builder.py").read_text(encoding="utf-8")
    block = _block(text, "function renderPriorityBoard()", "function renderPriorityRoster()")
    assert ".slice(" not in block


def test_docs_priority_posts_are_not_truncated():
    text = (ROOT / "docs" / "app.js").read_text(encoding="utf-8")
    block = _block(text, "function renderPriorityPosts()", "function renderAllPosts()")
    assert ".slice(" not in block
