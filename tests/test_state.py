from pathlib import Path

from blog_tracker.state import load_seen_guids


def test_load_seen_guids_accepts_utf8_bom(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text('{"seen_guids":["a","b"]}', encoding="utf-8-sig")
    assert load_seen_guids(path) == {"a", "b"}
