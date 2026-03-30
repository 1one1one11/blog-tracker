from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_post(post: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(post)
    normalized["classification"] = normalized.get("classification") or normalized.get("group_name") or "미분류"
    normalized["group_name"] = normalized.get("group_name") or "미분류"
    normalized["display_name"] = normalized.get("display_name") or normalized.get("blog_id") or "알 수 없음"
    normalized["blog_title"] = normalized.get("blog_title") or normalized["display_name"]
    normalized["tags"] = list(normalized.get("tags") or [])
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


def merge_archive(existing_posts: list[dict[str, Any]], payloads: list[dict[str, Any]], max_posts: int = 2000) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for post in existing_posts:
        normalized = _normalize_post(post)
        merged[normalized["guid"]] = normalized

    for payload in payloads:
        for post in payload.get("posts", []):
            normalized = _normalize_post(post)
            merged[normalized["guid"]] = normalized

    posts = sorted(merged.values(), key=lambda item: item["published_at"], reverse=True)
    return posts[:max_posts]


def build_archive_payload(posts: list[dict[str, Any]], generated_at: datetime) -> dict[str, Any]:
    classifications = Counter(post["classification"] for post in posts)
    authors = Counter(post["display_name"] for post in posts)
    groups = Counter(post["group_name"] for post in posts)
    return {
        "generated_at": generated_at.isoformat(),
        "post_count": len(posts),
        "classifications": dict(classifications.most_common()),
        "authors": dict(authors.most_common(50)),
        "groups": dict(groups.most_common()),
        "posts": posts,
    }


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
      width: min(1180px, calc(100% - 32px));
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
    .metric, .panel, .post {
      border: 1px solid var(--line);
      background: var(--surface);
      border-radius: 22px;
      box-shadow: var(--shadow);
    }
    .metric {
      padding: 18px 20px;
    }
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
    .field {
      margin-bottom: 14px;
    }
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
    .results-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: end;
      padding: 8px 4px;
    }
    .results-meta {
      color: var(--muted);
      font-size: 0.92rem;
    }
    .posts {
      display: grid;
      gap: 14px;
    }
    .post {
      padding: 20px;
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
      font-size: 1.14rem;
      line-height: 1.45;
      letter-spacing: -0.02em;
    }
    .post p {
      margin: 0;
      line-height: 1.65;
      color: #374151;
    }
    .meta {
      margin-top: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px 14px;
      color: var(--muted);
      font-size: 0.86rem;
    }
    .post a {
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }
    .empty {
      padding: 28px;
      text-align: center;
      color: var(--muted);
    }
    @media (max-width: 920px) {
      .layout { grid-template-columns: 1fr; }
      .panel { position: static; }
      .shell { width: min(100% - 20px, 1180px); padding-top: 20px; }
      .hero { padding: 22px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Research Briefing Archive</h1>
      <p class="lede">네이버 블로그 트래커의 누적 브리핑 아카이브입니다. 분류, 작성자, 소스 그룹 필터와 전체 텍스트 검색으로 필요한 신호만 빠르게 추릴 수 있습니다.</p>
      <div class="metrics">
        <article class="metric"><label>누적 포스트</label><strong id="metric-posts">-</strong></article>
        <article class="metric"><label>활성 분류 수</label><strong id="metric-classes">-</strong></article>
        <article class="metric"><label>작성자 수</label><strong id="metric-authors">-</strong></article>
        <article class="metric"><label>마지막 갱신</label><strong id="metric-updated" style="font-size:1rem">-</strong></article>
      </div>
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
        <div class="chips" id="top-classes"></div>
      </aside>

      <main class="results">
        <div class="results-head">
          <div>
            <h2>결과</h2>
            <div class="results-meta" id="results-meta">불러오는 중...</div>
          </div>
        </div>
        <div class="posts" id="posts"></div>
      </main>
    </section>
  </div>

  <script>
    const state = {
      archive: null,
      filtered: [],
    };

    const els = {
      posts: document.getElementById("posts"),
      resultsMeta: document.getElementById("results-meta"),
      classification: document.getElementById("classification"),
      group: document.getElementById("group"),
      author: document.getElementById("author"),
      search: document.getElementById("search"),
      hasContent: document.getElementById("has-content"),
      topClasses: document.getElementById("top-classes"),
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
      return new Intl.DateTimeFormat("ko-KR", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
    }

    function escapeHtml(value) {
      return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function renderTopClasses() {
      const items = Object.entries(state.archive.classifications || {}).slice(0, 8);
      els.topClasses.innerHTML = items
        .map(([name, count]) => `<span class="chip">${escapeHtml(name)} <strong>${count}</strong></span>`)
        .join("");
    }

    function renderPosts() {
      const posts = state.filtered;
      els.resultsMeta.textContent = `${posts.length}건 표시 / 누적 ${state.archive.posts.length}건`;
      if (!posts.length) {
        els.posts.innerHTML = '<div class="post empty">조건에 맞는 결과가 없습니다.</div>';
        return;
      }

      els.posts.innerHTML = posts.map((post) => `
        <article class="post">
          <div class="post-top">
            <span class="badge">${escapeHtml(post.classification)}</span>
            <span class="chip">${escapeHtml(post.group_name)}</span>
            ${post.has_content ? '<span class="chip">본문 추출</span>' : '<span class="chip">RSS 요약 fallback</span>'}
          </div>
          <h3><a href="${post.link}" target="_blank" rel="noreferrer">${escapeHtml(post.title || "(제목 없음)")}</a></h3>
          <p>${escapeHtml(post.summary || "요약 없음")}</p>
          <div class="meta">
            <span>작성자: ${escapeHtml(post.display_name)}</span>
            <span>블로그: ${escapeHtml(post.blog_title)}</span>
            <span>발행: ${escapeHtml(formatDate(post.published_at))}</span>
            ${post.category ? `<span>카테고리: ${escapeHtml(post.category)}</span>` : ""}
            ${post.tags?.length ? `<span>태그: ${escapeHtml(post.tags.join(", "))}</span>` : ""}
          </div>
        </article>
      `).join("");
    }

    function applyFilters() {
      const search = els.search.value.trim().toLowerCase();
      const classification = els.classification.value;
      const group = els.group.value;
      const author = els.author.value;
      const hasContent = els.hasContent.value;

      state.filtered = state.archive.posts.filter((post) => {
        if (classification && post.classification !== classification) return false;
        if (group && post.group_name !== group) return false;
        if (author && post.display_name !== author) return false;
        if (hasContent && String(post.has_content) !== hasContent) return false;
        if (search && !post.search_text.includes(search)) return false;
        return true;
      });
      renderPosts();
    }

    async function boot() {
      const response = await fetch("./data/archive.json");
      state.archive = await response.json();

      fillSelect(els.classification, uniqueSorted(state.archive.posts.map((post) => post.classification)));
      fillSelect(els.group, uniqueSorted(state.archive.posts.map((post) => post.group_name)));
      fillSelect(els.author, uniqueSorted(state.archive.posts.map((post) => post.display_name)));

      els.metricPosts.textContent = state.archive.post_count.toLocaleString("ko-KR");
      els.metricClasses.textContent = Object.keys(state.archive.classifications || {}).length.toLocaleString("ko-KR");
      els.metricAuthors.textContent = Object.keys(state.archive.authors || {}).length.toLocaleString("ko-KR");
      els.metricUpdated.textContent = formatDate(state.archive.generated_at);

      renderTopClasses();
      state.filtered = [...state.archive.posts];
      renderPosts();

      [els.classification, els.group, els.author, els.hasContent].forEach((el) => el.addEventListener("change", applyFilters));
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

    archive_path = archive_dir / "archive.json"
    existing_posts = _load_json(archive_path).get("posts", []) if archive_path.exists() else []
    payloads = load_digest_payloads(output_dir)
    generated_at = datetime.now().astimezone()
    merged_posts = merge_archive(existing_posts, payloads, max_posts=max_posts)
    archive_payload = build_archive_payload(merged_posts, generated_at=generated_at)

    archive_path.write_text(json.dumps(archive_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (site_data_dir / "archive.json").write_text(json.dumps(archive_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (site_dir / "index.html").write_text(render_index_html(), encoding="utf-8")
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")
    return archive_payload
