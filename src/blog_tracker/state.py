from __future__ import annotations

import json
from pathlib import Path


def load_seen_guids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return set(payload.get("seen_guids", []))


def save_seen_guids(path: Path, guids: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"seen_guids": sorted(guids)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
