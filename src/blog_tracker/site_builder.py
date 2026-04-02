from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from blog_tracker.analysis_dashboard import build_analysis_files
from blog_tracker.config import load_priority_bloggers
from blog_tracker.dc_gallery import LIST_URL as DC_LIST_URL, fetch_dc_semiconductor_posts

ROOT = Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_post(post: dict[str, Any], priority_bloggers: set[str]) -> dict[str, Any]:
    normalized = dict(post)
    normalized["blog_id"] = normalized.get("blog_id") or normalized.get("display_name") or normalized.get("guid") or ""
    normalized["classification"] = normalized.get("classification") or normalized.get("group_name") or "미분류"
    normalized["group_name"] = normalized.get("group_name") or "미분류"
    normalized["display_name"] = normalized.get("display_name") or normalized.get("blog_id") or "알 수 없음"
    normalized["blog_title"] = normalized.get("blog_title") or normalized["display_name"]
    normalized["tags"] = list(normalized.get("tags") or [])
    normalized["is_priority"] = normalized.get("blog_id") in priority_bloggers or bool(normalized.get("is_priority"))
    normalized["summary"] = (normalized.get("summary") or "").strip()
    normalized["title"] = (normalized.get("title") or "").strip()
    normalized["search_text"] = " ".join(
        [
            normalized["classification"],
            normalized["group_name"],
            normalized["display_name"],
            normalized["blog_title"],
            normalized["title"],
            normalized["summary"],
            normalized.get("category") or "",
            " ".join(normalized["tags"]),
        ]
    ).lower()
    return normalized


def load_digest_payloads(output_dir: Path) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    if not output_dir.exists():
        return payloads
    for path in sorted(output_dir.glob("digest_*.json")):
        payloads.append(_load_json(path))
    return payloads


def merge_archive(
    existing_posts: list[dict[str, Any]],
    payloads: list[dict[str, Any]],
    priority_bloggers: set[str],
    max_posts: int = 2000,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for post in existing_posts:
        normalized = _normalize_post(post, priority_bloggers=priority_bloggers)
        merged[normalized["guid"]] = normalized

    for payload in payloads:
        for post in payload.get("posts", []):
            normalized = _normalize_post(post, priority_bloggers=priority_bloggers)
            merged[normalized["guid"]] = normalized

    posts = sorted(merged.values(), key=lambda item: item["published_at"], reverse=True)
    return posts[:max_posts]


def build_archive_payload(posts: list[dict[str, Any]], generated_at: datetime, priority_bloggers: set[str]) -> dict[str, Any]:
    classifications = Counter(post["classification"] for post in posts)
    authors = Counter(post["display_name"] for post in posts)
    groups = Counter(post["group_name"] for post in posts)
    priority_index = []
    for blog_id in sorted(priority_bloggers):
        sample = next((post for post in posts if post["blog_id"] == blog_id), None)
        priority_index.append(
            {
                "blog_id": blog_id,
                "display_name": sample["display_name"] if sample else blog_id,
                "blog_title": sample["blog_title"] if sample else "",
                "post_count": sum(1 for post in posts if post["blog_id"] == blog_id),
            }
        )
    return {
        "generated_at": generated_at.isoformat(),
        "post_count": len(posts),
        "priority_post_count": sum(1 for post in posts if post["is_priority"]),
        "priority_bloggers": priority_index,
        "classifications": dict(classifications.most_common()),
        "authors": dict(authors.most_common(50)),
        "groups": dict(groups.most_common()),
        "posts": posts,
    }


def load_dc_payload(output_dir: Path, generated_at: datetime) -> dict[str, Any]:
    dc_path = output_dir / "dc_semiconductor.json"
    if dc_path.exists():
        return _load_json(dc_path)

    posts = fetch_dc_semiconductor_posts(limit=30)
    return {
        "generated_at": generated_at.isoformat(),
        "source_title": "디시인사이드 반도체산업 마이너 갤러리",
        "source_link": DC_LIST_URL,
        "total_posts": len(posts),
        "posts": [
            {
                "title": post.title,
                "link": post.link,
                "author": post.author,
                "published_at": post.published_at,
                "views": post.views,
                "recommends": post.recommends,
                "comments": post.comments,
                "excerpt": post.excerpt,
                "summary": post.summary,
            }
            for post in posts
        ],
    }


def render_dc_gallery_html() -> str:
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>반도체 산업 갤러리 링크 모음</title>
  <style>
    :root {
      --bg: #f4efe6;
      --surface: rgba(255, 250, 243, 0.9);
      --surface-strong: #fffaf2;
      --text: #1f2937;
      --muted: #6b7280;
      --line: rgba(31, 41, 55, 0.12);
      --accent: #9a3412;
      --chip: #f2e5d5;
      --shadow: 0 22px 50px rgba(68, 39, 12, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Pretendard Variable", "Noto Sans KR", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(154, 52, 18, 0.16), transparent 24rem),
        radial-gradient(circle at top right, rgba(14, 116, 144, 0.12), transparent 22rem),
        linear-gradient(180deg, #f7f2ea 0%, var(--bg) 100%);
      min-height: 100vh;
    }
    .shell {
      width: min(1280px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 56px;
    }
    .hero, .post {
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(135deg, rgba(255,255,255,0.74), rgba(255,250,243,0.96));
      box-shadow: var(--shadow);
    }
    .hero {
      padding: 28px;
      margin-bottom: 18px;
    }
    h1 {
      margin: 0 0 12px;
      font-size: clamp(2rem, 4vw, 3.3rem);
      line-height: 1.02;
      letter-spacing: -0.04em;
    }
    .lede, .meta-line {
      color: var(--muted);
      line-height: 1.6;
    }
    .hero-links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }
    .link-btn {
      display: inline-flex;
      align-items: center;
      padding: 10px 14px;
      border-radius: 999px;
      text-decoration: none;
      background: rgba(255,255,255,0.75);
      border: 1px solid var(--line);
      color: var(--text);
      font-weight: 700;
      font-size: 0.9rem;
    }
    .link-btn:hover {
      border-color: rgba(154, 52, 18, 0.28);
      color: var(--accent);
    }
    .posts {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }
    .post {
      padding: 18px;
    }
    .badges {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--chip);
      color: var(--muted);
      font-size: 0.8rem;
      font-weight: 700;
    }
    .post h2 {
      margin: 0 0 10px;
      font-size: 1.05rem;
      line-height: 1.45;
      letter-spacing: -0.02em;
    }
    .post h2 a {
      color: var(--accent);
      text-decoration: none;
    }
    .post p {
      margin: 0;
      line-height: 1.6;
      color: #374151;
      display: -webkit-box;
      -webkit-line-clamp: 6;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .meta {
      margin-top: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px 14px;
      color: var(--muted);
      font-size: 0.82rem;
    }
    .empty {
      padding: 28px;
      text-align: center;
      color: var(--muted);
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }
    @media (max-width: 1100px) {
      .posts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 760px) {
      .shell { width: min(100% - 20px, 1280px); padding-top: 20px; }
      .hero { padding: 22px; }
      .posts { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>반도체 산업 갤러리 링크 모음</h1>
      <p class="lede">디시인사이드 반도체산업 마이너 갤러리의 최신 글을 링크와 함께 모아둔 페이지입니다. 요약이 있으면 같이 보여주고, 없으면 본문 발췌를 보여줍니다.</p>
      <div class="meta-line" id="summary-meta">불러오는 중...</div>
      <div class="hero-links">
        <a class="link-btn" href="./">브리핑 메인으로</a>
        <a class="link-btn" href="https://gall.dcinside.com/mgallery/board/lists/?id=tsmcsamsungskhynix" target="_blank" rel="noreferrer">갤러리 원문 보기</a>
      </div>
    </section>
    <section class="posts" id="posts"></section>
  </div>
  <script>
    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function formatDate(value) {
      if (!value) return "-";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(date);
    }

    function renderPost(post) {
      const summary = post.summary || post.excerpt || "본문을 불러오지 못했습니다.";
      return `
        <article class="post">
          <div class="badges">
            <span class="badge">댓글 ${escapeHtml(post.comments || "0")}</span>
            <span class="badge">추천 ${escapeHtml(post.recommends || "0")}</span>
            <span class="badge">조회 ${escapeHtml(post.views || "0")}</span>
          </div>
          <h2><a href="${escapeHtml(post.link)}" target="_blank" rel="noreferrer">${escapeHtml(post.title || "(제목 없음)")}</a></h2>
          <p>${escapeHtml(summary)}</p>
          <div class="meta">
            <span>작성자: ${escapeHtml(post.author || "익명")}</span>
            <span>게시: ${escapeHtml(formatDate(post.published_at))}</span>
          </div>
        </article>
      `;
    }

    async function boot() {
      const response = await fetch("./data/dc_semiconductor.json");
      const payload = await response.json();
      document.getElementById("summary-meta").textContent =
        `최신 ${payload.total_posts || 0}건 · 마지막 갱신 ${formatDate(payload.generated_at)}`;
      const postsEl = document.getElementById("posts");
      const posts = payload.posts || [];
      postsEl.innerHTML = posts.length
        ? posts.map(renderPost).join("")
        : '<div class="empty">아직 갤러리 데이터가 없습니다.</div>';
    }

    boot().catch((error) => {
      console.error(error);
      document.getElementById("summary-meta").textContent = "갤러리 데이터를 불러오지 못했습니다.";
      document.getElementById("posts").innerHTML = '<div class="empty">배포 데이터가 준비되지 않았습니다.</div>';
    });
  </script>
</body>
</html>
"""


def render_index_html() -> str:
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Blog Tracker Briefing</title>
  <style>
    :root {
      --bg: #f4efe6;
      --surface: rgba(255, 250, 243, 0.86);
      --surface-strong: #fffaf2;
      --text: #1f2937;
      --muted: #6b7280;
      --line: rgba(31, 41, 55, 0.12);
      --accent: #9a3412;
      --accent-soft: rgba(154, 52, 18, 0.1);
      --chip: #f2e5d5;
      --shadow: 0 22px 50px rgba(68, 39, 12, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Pretendard Variable", "Noto Sans KR", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(154, 52, 18, 0.16), transparent 24rem),
        radial-gradient(circle at top right, rgba(14, 116, 144, 0.12), transparent 22rem),
        linear-gradient(180deg, #f7f2ea 0%, var(--bg) 100%);
      min-height: 100vh;
    }
    .shell {
      width: min(1280px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 56px;
    }
    .hero {
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(135deg, rgba(255,255,255,0.7), rgba(255,250,243,0.94));
      backdrop-filter: blur(12px);
      box-shadow: var(--shadow);
    }
    h1 {
      margin: 0 0 12px;
      font-size: clamp(2rem, 4vw, 3.5rem);
      line-height: 1.02;
      letter-spacing: -0.04em;
    }
    .lede {
      margin: 0;
      color: var(--muted);
      font-size: 1rem;
      max-width: 60rem;
      line-height: 1.6;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }
    .quick-links {
      margin-top: 18px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .metric, .panel, .post, .section-card {
      border: 1px solid var(--line);
      background: var(--surface);
      border-radius: 22px;
      box-shadow: var(--shadow);
    }
    .metric { padding: 18px 20px; }
    .metric label {
      display: block;
      color: var(--muted);
      font-size: 0.82rem;
      margin-bottom: 8px;
    }
    .metric strong {
      font-size: 1.7rem;
      letter-spacing: -0.03em;
    }
    .layout {
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 18px;
      margin-top: 18px;
    }
    .panel {
      padding: 18px;
      position: sticky;
      top: 18px;
      height: fit-content;
    }
    .panel h2, .results h2 {
      margin: 0 0 14px;
      font-size: 1rem;
      letter-spacing: -0.02em;
    }
    .field { margin-bottom: 14px; }
    .field label {
      display: block;
      margin-bottom: 6px;
      font-size: 0.82rem;
      color: var(--muted);
    }
    .field input, .field select {
      width: 100%;
      border: 1px solid rgba(31, 41, 55, 0.15);
      border-radius: 14px;
      padding: 12px 14px;
      background: var(--surface-strong);
      color: var(--text);
      font: inherit;
    }
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 10px;
      background: var(--chip);
      border-radius: 999px;
      font-size: 0.8rem;
      color: var(--muted);
    }
    .results {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .section-card { padding: 18px; }
    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 12px;
      margin-bottom: 14px;
    }
    .section-head h2, .section-head h3 {
      margin: 0;
      font-size: 1rem;
      letter-spacing: -0.02em;
    }
    .section-meta, .results-meta {
      color: var(--muted);
      font-size: 0.9rem;
    }
    .tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
    }
    .tab-btn {
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.75);
      color: var(--text);
      padding: 10px 14px;
      border-radius: 999px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    .tab-btn.active {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }
    .results-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: end;
      padding: 8px 4px;
    }
    .posts {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }
    .post {
      padding: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,0.76), rgba(255,250,243,0.98));
    }
    .post-top {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 700;
      font-size: 0.8rem;
    }
    .post h3 {
      margin: 0 0 10px;
      font-size: 1.05rem;
      line-height: 1.45;
      letter-spacing: -0.02em;
    }
    .post p {
      margin: 0;
      line-height: 1.6;
      color: #374151;
      display: -webkit-box;
      -webkit-line-clamp: 5;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .meta {
      margin-top: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px 14px;
      color: var(--muted);
      font-size: 0.82rem;
    }
    .author-meta {
      color: var(--text);
      font-weight: 800;
    }
    .published-at {
      margin: 0 0 10px;
      color: var(--accent);
      font-size: 0.88rem;
      font-weight: 700;
      letter-spacing: -0.01em;
    }
    .post a {
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }
    .quick-link {
      display: inline-flex;
      align-items: center;
      padding: 10px 14px;
      border-radius: 999px;
      text-decoration: none;
      background: rgba(255,255,255,0.75);
      border: 1px solid var(--line);
      color: var(--text);
      font-weight: 700;
      font-size: 0.88rem;
    }
    .quick-link:hover {
      border-color: rgba(154, 52, 18, 0.28);
      color: var(--accent);
    }
    .priority-badge {
      background: rgba(14, 116, 144, 0.12);
      color: #0f5f73;
    }
    .priority-board {
      border: 1px solid rgba(14, 116, 144, 0.16);
      background: linear-gradient(180deg, rgba(240, 249, 255, 0.88), rgba(255,250,243,0.96));
    }
    .dc-post {
      position: relative;
      overflow: hidden;
      border-color: rgba(154, 52, 18, 0.14);
    }
    .dc-post::before {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: linear-gradient(135deg, rgba(154, 52, 18, var(--heat-alpha, 0.08)), rgba(245, 158, 11, calc(var(--heat-alpha, 0.08) * 0.65)), rgba(255,255,255,0));
    }
    .dc-post > * {
      position: relative;
      z-index: 1;
    }
    .dc-badge {
      background: rgba(154, 52, 18, 0.14);
      color: #8a2d10;
    }
    .dc-chip {
      background: rgba(245, 158, 11, 0.12);
      color: #9a3412;
    }
    .empty {
      padding: 28px;
      text-align: center;
      color: var(--muted);
    }
    @media (max-width: 1180px) {
      .posts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 920px) {
      .layout { grid-template-columns: 1fr; }
      .panel { position: static; }
      .shell { width: min(100% - 20px, 1280px); padding-top: 20px; }
      .hero { padding: 22px; }
      .posts { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Research Briefing Archive</h1>
      <p class="lede">네이버 블로그 트래커의 누적 브리핑 아카이브입니다. 우선 블로거, 날짜별 새 글, 전체 탐색을 각각 분리해 바로 볼 수 있게 구성했습니다.</p>
      <div class="metrics">
        <article class="metric"><label>누적 포스트</label><strong id="metric-posts">-</strong></article>
        <article class="metric"><label>활성 분류 수</label><strong id="metric-classes">-</strong></article>
        <article class="metric"><label>작성자 수</label><strong id="metric-authors">-</strong></article>
        <article class="metric"><label>마지막 갱신</label><strong id="metric-updated" style="font-size:1rem">-</strong></article>
      </div>
      <div class="quick-links" id="quick-links"></div>
    </section>

    <section class="layout">
      <aside class="panel">
        <h2>필터</h2>
        <div class="field">
          <label for="search">검색</label>
          <input id="search" type="search" placeholder="제목, 요약, 작성자, 태그 검색">
        </div>
        <div class="field">
          <label for="classification">분류</label>
          <select id="classification"><option value="">전체</option></select>
        </div>
        <div class="field">
          <label for="group">소스 그룹</label>
          <select id="group"><option value="">전체</option></select>
        </div>
        <div class="field">
          <label for="author">작성자</label>
          <select id="author"><option value="">전체</option></select>
        </div>
        <div class="field">
          <label for="has-content">본문 추출</label>
          <select id="has-content">
            <option value="">전체</option>
            <option value="true">본문 추출 성공</option>
            <option value="false">본문 추출 실패</option>
          </select>
        </div>
        <div class="field">
          <label for="priority-only">우선 블로거</label>
          <select id="priority-only">
            <option value="">전체</option>
            <option value="true">우선 블로거만</option>
          </select>
        </div>
        <div class="chips" id="top-classes"></div>
      </aside>

      <main class="results">
        <section class="section-card priority-board" id="priority-board">
          <div class="section-head">
            <div>
              <h2>우선 블로거 전용 보드</h2>
              <div class="section-meta" id="priority-meta">불러오는 중...</div>
            </div>
          </div>
          <div class="posts" id="priority-posts"></div>
        </section>

        <section class="section-card" id="priority-roster-section">
          <div class="section-head">
            <div>
              <h2>우선 블로거 목록</h2>
              <div class="section-meta" id="priority-roster-meta">불러오는 중...</div>
            </div>
          </div>
          <div class="chips" id="priority-roster"></div>
        </section>

        <section class="section-card" id="dc-board">
          <div class="section-head">
            <div>
              <h2>디시 커뮤니티 픽</h2>
              <div class="section-meta" id="dc-meta">불러오는 중...</div>
            </div>
            <a class="quick-link" href="./semiconductor-gallery.html">갤러리 링크 페이지</a>
          </div>
          <div class="posts" id="dc-posts"></div>
        </section>

        <section class="section-card" id="date-board">
          <div class="section-head">
            <div>
              <h2>날짜별 새 글</h2>
              <div class="section-meta" id="tab-meta">불러오는 중...</div>
            </div>
          </div>
          <div class="tabs" id="date-tabs"></div>
          <div class="posts" id="tab-posts"></div>
        </section>

        <div class="results-head">
          <div>
            <h2>전체 탐색</h2>
            <div class="results-meta" id="results-meta">불러오는 중...</div>
          </div>
        </div>
        <div class="posts" id="posts"></div>
      </main>
    </section>
  </div>

  <script>
    const state = { archive: null, filtered: [] };
    const ui = { activeDateKey: "" };
    const els = {
      posts: document.getElementById("posts"),
      priorityPosts: document.getElementById("priority-posts"),
      priorityMeta: document.getElementById("priority-meta"),
      priorityRoster: document.getElementById("priority-roster"),
      priorityRosterMeta: document.getElementById("priority-roster-meta"),
      dcPosts: document.getElementById("dc-posts"),
      dcMeta: document.getElementById("dc-meta"),
      tabPosts: document.getElementById("tab-posts"),
      tabMeta: document.getElementById("tab-meta"),
      dateTabs: document.getElementById("date-tabs"),
      resultsMeta: document.getElementById("results-meta"),
      classification: document.getElementById("classification"),
      group: document.getElementById("group"),
      author: document.getElementById("author"),
      search: document.getElementById("search"),
      hasContent: document.getElementById("has-content"),
      priorityOnly: document.getElementById("priority-only"),
      topClasses: document.getElementById("top-classes"),
      quickLinks: document.getElementById("quick-links"),
      metricPosts: document.getElementById("metric-posts"),
      metricClasses: document.getElementById("metric-classes"),
      metricAuthors: document.getElementById("metric-authors"),
      metricUpdated: document.getElementById("metric-updated"),
    };

    function uniqueSorted(values) {
      return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b, "ko"));
    }

    function fillSelect(select, values) {
      for (const value of values) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      }
    }

    function formatDate(value) {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(date);
    }

    function formatPublishedAt(value) {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      const weekday = new Intl.DateTimeFormat("ko-KR", { weekday: "short" }).format(date);
      const datePart = new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "long", day: "numeric" }).format(date);
      const timePart = new Intl.DateTimeFormat("ko-KR", { hour: "numeric", minute: "2-digit", hour12: true }).format(date);
      return `${datePart} (${weekday}) ${timePart}`;
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function localDateKey(value) {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "";
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    }

    function parseViewCount(value) {
      const numeric = Number(String(value || "").replace(/[^\\d]/g, ""));
      return Number.isFinite(numeric) ? numeric : 0;
    }

    function getDcHeatAlpha(post) {
      const views = parseViewCount(post.views);
      const maxViews = Math.max(...((state.dc?.featured_posts || state.dc?.posts || []).map((item) => parseViewCount(item.views))), 1);
      const normalized = Math.log10(views + 1) / Math.log10(maxViews + 1);
      return Math.max(0.08, Math.min(0.28, 0.08 + normalized * 0.2));
    }

    function renderTopClasses() {
      const items = Object.entries(state.archive.classifications || {}).slice(0, 8);
      els.topClasses.innerHTML = items
        .map(([name, count]) => `<span class="chip">${escapeHtml(name)} <strong>${count}</strong></span>`)
        .join("");
    }

    function buildQuickLink(label, params, hash = "") {
      const url = new URL(window.location.href);
      url.search = "";
      Object.entries(params).forEach(([key, value]) => {
        if (value) url.searchParams.set(key, value);
      });
      return `<a class="quick-link" href="${escapeHtml(url.pathname + url.search + hash)}">${escapeHtml(label)}</a>`;
    }

    function getDateBuckets() {
      const generatedAt = new Date(state.archive.generated_at);
      return [
        { label: "오늘", offset: 0 },
        { label: "어제", offset: 1 },
        { label: "그제", offset: 2 },
        { label: "나흘 전", offset: 4 },
      ].map((item) => {
        const date = new Date(generatedAt);
        date.setDate(date.getDate() - item.offset);
        return { ...item, key: localDateKey(date) };
      });
    }

    function renderQuickLinks() {
      const links = getDateBuckets().map((bucket) => {
        return buildQuickLink(`${bucket.label} 새 글`, { date: bucket.key, section: "date" }, "#date-board");
      });
      links.push(buildQuickLink("우선 블로거 모아보기", { priority: "true", section: "priority" }, "#priority-board"));
      links.push(buildQuickLink("우선 블로거 목록", { section: "priority-roster" }, "#priority-roster-section"));
      links.push(buildQuickLink("디시 커뮤니티 픽", { section: "dc" }, "#dc-board"));
      links.push('<a class="quick-link" href="./semiconductor-gallery.html">디시 갤러리 모음</a>');
      links.push('<a class="quick-link" href="./analysis.html">흐름 분석 보드</a>');
      els.quickLinks.innerHTML = links.join("");
    }

    function renderPostCard(post) {
      return `
        <article class="post">
          <div class="post-top">
            <span class="badge">${escapeHtml(post.classification)}</span>
            <span class="chip">${escapeHtml(post.group_name)}</span>
            ${post.is_priority ? '<span class="chip priority-badge">우선 블로거</span>' : ""}
            ${post.has_content ? '<span class="chip">본문 추출</span>' : '<span class="chip">RSS 요약 fallback</span>'}
          </div>
          <div class="published-at">게시 시각: ${escapeHtml(formatPublishedAt(post.published_at))}</div>
          <h3><a href="${post.link}" target="_blank" rel="noreferrer">${escapeHtml(post.title || "(제목 없음)")}</a></h3>
          <p>${escapeHtml(post.summary || "요약 없음")}</p>
          <div class="meta">
            <span class="author-meta">작성자: ${escapeHtml(post.display_name)}</span>
            <span>블로그: ${escapeHtml(post.blog_title)}</span>
            <span>발행: ${escapeHtml(formatDate(post.published_at))}</span>
            ${post.category ? `<span>카테고리: ${escapeHtml(post.category)}</span>` : ""}
            ${post.tags?.length ? `<span>태그: ${escapeHtml(post.tags.join(", "))}</span>` : ""}
          </div>
        </article>
      `;
    }

    function renderPostGrid(target, posts, emptyText) {
      if (!posts.length) {
        target.innerHTML = `<div class="post empty">${emptyText}</div>`;
        return;
      }
      target.innerHTML = posts.map((post) => renderPostCard(post)).join("");
    }

    function renderPriorityBoard() {
      const priorityPosts = state.archive.posts.filter((post) => post.is_priority).slice(0, 12);
      els.priorityMeta.textContent = `우선 블로거 글 ${priorityPosts.length}건`;
      renderPostGrid(els.priorityPosts, priorityPosts, "우선 블로거 글이 없습니다.");
    }

    function renderPriorityRoster() {
      const bloggers = state.archive.priority_bloggers || [];
      els.priorityRosterMeta.textContent = `우선 블로거 ${bloggers.length}명`;
      if (!bloggers.length) {
        els.priorityRoster.innerHTML = '<span class="chip">우선 블로거가 없습니다.</span>';
        return;
      }
      els.priorityRoster.innerHTML = bloggers.map((blogger) => {
        const label = blogger.display_name && blogger.display_name !== blogger.blog_id
          ? `${blogger.display_name} (${blogger.blog_id})`
          : blogger.blog_id;
        return `<span class="chip">${escapeHtml(label)} <strong>${blogger.post_count}</strong></span>`;
      }).join("");
    }

    function renderDcPostCard(post) {
      const summary = post.summary || post.excerpt || "본문을 불러오지 못했습니다.";
      const heatAlpha = getDcHeatAlpha(post).toFixed(3);
      return `
        <article class="post dc-post" style="--heat-alpha:${heatAlpha}">
          <div class="post-top">
            <span class="badge dc-badge">디시</span>
            <span class="chip dc-chip">반도체 산업 갤러리</span>
          </div>
          <div class="published-at">게시 시각: ${escapeHtml(formatDate(post.published_at))}</div>
          <h3><a href="${post.link}" target="_blank" rel="noreferrer">${escapeHtml(post.title || "(제목 없음)")}</a></h3>
          <p>${escapeHtml(summary)}</p>
          <div class="meta">
            <span class="author-meta">작성자: ${escapeHtml(post.author || "익명")}</span>
            <span>댓글: ${escapeHtml(post.comments || "0")}</span>
            <span>추천: ${escapeHtml(post.recommends || "0")}</span>
            <span>조회: ${escapeHtml(post.views || "0")}</span>
          </div>
        </article>
      `;
    }

    function renderDcBoard() {
      const posts = (state.dc?.featured_posts || state.dc?.posts || []).slice(0, 6);
      els.dcMeta.textContent = `최신 ${posts.length}건`;
      if (!posts.length) {
        els.dcPosts.innerHTML = '<div class="post empty">아직 갤러리 데이터가 없습니다.</div>';
        return;
      }
      els.dcPosts.innerHTML = posts.map((post) => renderDcPostCard(post)).join("");
    }

    function renderDateTabs() {
      const buckets = getDateBuckets();
      if (!ui.activeDateKey && buckets.length) ui.activeDateKey = buckets[0].key;
      const selected = buckets.find((bucket) => bucket.key === ui.activeDateKey) || buckets[0];
      els.dateTabs.innerHTML = buckets.map((bucket) => {
        const count = state.archive.posts.filter((post) => localDateKey(post.published_at) === bucket.key).length;
        const active = bucket.key === selected.key ? " active" : "";
        return `<button class="tab-btn${active}" type="button" data-date-key="${bucket.key}">${bucket.label} ${count}</button>`;
      }).join("");
      const tabPosts = state.archive.posts.filter((post) => localDateKey(post.published_at) === selected.key);
      els.tabMeta.textContent = `${selected.label} 기준 ${tabPosts.length}건`;
      renderPostGrid(els.tabPosts, tabPosts, `${selected.label} 글이 없습니다.`);
      els.dateTabs.querySelectorAll("[data-date-key]").forEach((button) => {
        button.addEventListener("click", () => {
          ui.activeDateKey = button.getAttribute("data-date-key") || "";
          renderDateTabs();
        });
      });
    }

    function applyUrlFilters() {
      const params = new URLSearchParams(window.location.search);
      const date = params.get("date") || "";
      const priority = params.get("priority") || "";
      const section = params.get("section") || "";
      if (date) {
        ui.activeDateKey = date;
        els.search.value = date;
      }
      if (priority === "true" || section === "priority") {
        els.priorityOnly.value = "true";
      }
    }

    function applyFilters() {
      const search = els.search.value.trim().toLowerCase();
      const classification = els.classification.value;
      const group = els.group.value;
      const author = els.author.value;
      const hasContent = els.hasContent.value;
      const priorityOnly = els.priorityOnly.value;
      state.filtered = state.archive.posts.filter((post) => {
        if (classification && post.classification !== classification) return false;
        if (group && post.group_name !== group) return false;
        if (author && post.display_name !== author) return false;
        if (hasContent && String(post.has_content) !== hasContent) return false;
        if (priorityOnly === "true" && !post.is_priority) return false;
        if (search) {
          const dateKey = localDateKey(post.published_at);
          if (!post.search_text.includes(search) && dateKey !== search) return false;
        }
        return true;
      });
      els.resultsMeta.textContent = `${state.filtered.length}건 표시 / 누적 ${state.archive.posts.length}건`;
      renderPostGrid(els.posts, state.filtered, "조건에 맞는 결과가 없습니다.");
    }

    async function boot() {
      const [archiveResponse, dcResponse] = await Promise.all([
        fetch("./data/archive.json"),
        fetch("./data/dc_semiconductor.json"),
      ]);
      state.archive = await archiveResponse.json();
      state.dc = await dcResponse.json();
      fillSelect(els.classification, uniqueSorted(state.archive.posts.map((post) => post.classification)));
      fillSelect(els.group, uniqueSorted(state.archive.posts.map((post) => post.group_name)));
      fillSelect(els.author, uniqueSorted(state.archive.posts.map((post) => post.display_name)));
      els.metricPosts.textContent = state.archive.post_count.toLocaleString("ko-KR");
      els.metricClasses.textContent = Object.keys(state.archive.classifications || {}).length.toLocaleString("ko-KR");
      els.metricAuthors.textContent = Object.keys(state.archive.authors || {}).length.toLocaleString("ko-KR");
      els.metricUpdated.textContent = formatDate(state.archive.generated_at);
      renderTopClasses();
      renderQuickLinks();
      renderPriorityBoard();
      renderPriorityRoster();
      renderDcBoard();
      applyUrlFilters();
      renderDateTabs();
      applyFilters();
      [els.classification, els.group, els.author, els.hasContent, els.priorityOnly].forEach((el) => el.addEventListener("change", applyFilters));
      els.search.addEventListener("input", applyFilters);
    }

    boot().catch((error) => {
      console.error(error);
      els.resultsMeta.textContent = "데이터를 불러오지 못했습니다.";
      els.posts.innerHTML = '<div class="post empty">배포 데이터가 아직 준비되지 않았습니다.</div>';
    });
  </script>
</body>
</html>
"""


def build_site(output_dir: Path, archive_dir: Path, site_dir: Path, max_posts: int = 2000) -> dict[str, Any]:
    archive_dir.mkdir(parents=True, exist_ok=True)
    site_dir.mkdir(parents=True, exist_ok=True)
    site_data_dir = site_dir / "data"
    site_data_dir.mkdir(parents=True, exist_ok=True)

    priority_bloggers = load_priority_bloggers(ROOT / "config" / "priority_bloggers.txt")
    archive_path = archive_dir / "archive.json"
    existing_posts = _load_json(archive_path).get("posts", []) if archive_path.exists() else []
    payloads = load_digest_payloads(output_dir)
    generated_at = datetime.now().astimezone()
    merged_posts = merge_archive(existing_posts, payloads, priority_bloggers=priority_bloggers, max_posts=max_posts)
    archive_payload = build_archive_payload(merged_posts, generated_at=generated_at, priority_bloggers=priority_bloggers)
    dc_payload = load_dc_payload(output_dir, generated_at=generated_at)

    archive_path.write_text(json.dumps(archive_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (site_data_dir / "archive.json").write_text(json.dumps(archive_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (site_data_dir / "dc_semiconductor.json").write_text(json.dumps(dc_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (site_dir / "index.html").write_text(render_index_html(), encoding="utf-8")
    (site_dir / "semiconductor-gallery.html").write_text(render_dc_gallery_html(), encoding="utf-8")
    build_analysis_files(output_dir=output_dir, site_data_dir=site_data_dir, site_dir=site_dir, archive_payload=archive_payload, generated_at=generated_at)
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")
    return archive_payload
