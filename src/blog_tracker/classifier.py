from __future__ import annotations

from blog_tracker.models import BlogPost

RULES: list[tuple[str, tuple[str, ...]]] = [
    ("반도체", ("반도체", "semiconductor", "hbm", "파운드리", "메모리")),
    ("부동산", ("부동산", "재개발", "청약", "전세", "아파트")),
    ("매크로", ("금리", "환율", "경제", "채권", "cpi", "거시", "경기")),
    ("기업분석", ("실적", "밸류에이션", "per", "pbr", "기업", "사업", "분석")),
    ("포트폴리오", ("포트", "리밸런싱", "보유", "매수", "매도", "비중")),
]


def classify_post(post: BlogPost) -> str:
    haystack = " ".join(
        [
            post.group_name,
            post.category,
            post.title,
            " ".join(post.tags),
            post.content_text[:1000],
            post.description_text[:500],
        ]
    ).lower()
    for label, keywords in RULES:
        if any(keyword.lower() in haystack for keyword in keywords):
            return label
    return post.group_name or "미분류"
