from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

WORD_PATTERN = re.compile(r"[A-Za-z]{2,}|[가-힣]{2,}")

STOPWORDS = {
    "그리고",
    "하지만",
    "이렇게",
    "저렇게",
    "이번",
    "최근",
    "오늘",
    "내일",
    "정리",
    "브리핑",
    "요약",
    "원문",
    "보기",
    "주식",
    "투자",
    "시장",
    "갤러리",
    "디시",
    "커뮤니티",
    "블로그",
    "콘텐츠",
    "포스트",
    "분석",
    "생각",
    "이야기",
    "관련",
    "현재",
    "대한",
    "에서",
    "으로",
    "대한",
    "그냥",
    "정도",
    "때문",
    "대한",
}

TICKER_KEYWORDS = {
    "삼성전자": ("삼성전자", "삼성", "엑시노스"),
    "SK하이닉스": ("sk하이닉스", "하이닉스", "hbm"),
    "엔비디아": ("엔비디아", "nvidia"),
    "테슬라": ("테슬라", "tsla"),
    "애플": ("애플", "aapl"),
    "메타": ("메타", "meta"),
    "마이크로소프트": ("마이크로소프트", "msft"),
    "비트코인": ("비트코인", "btc"),
    "이더리움": ("이더리움", "eth"),
    "리플": ("리플", "xrp"),
    "솔라나": ("솔라나", "sol"),
    "TSMC": ("tsmc",),
    "마이크론": ("마이크론", "micron"),
}

SECTOR_KEYWORDS = {
    "반도체": ("반도체", "hbm", "파운드리", "메모리"),
    "AI": ("ai", "인공지능", "llm"),
    "자동차": ("자동차", "전기차", "ev"),
    "2차전지": ("2차전지", "배터리", "양극재", "음극재"),
    "바이오": ("바이오", "제약", "임상"),
    "플랫폼": ("플랫폼", "광고", "메타", "sns"),
    "크립토": ("비트코인", "이더리움", "코인", "알트", "etf"),
    "매크로": ("금리", "환율", "관세", "연준", "fomc", "경기"),
}

BULLISH_WORDS = ("강세", "상승", "반등", "돌파", "좋다", "개선", "매수", "호재", "낙관", "랠리")
BEARISH_WORDS = ("약세", "하락", "폭락", "부진", "매도", "악재", "우려", "경고", "부담", "침체")
FEAR_WORDS = ("불안", "공포", "리스크", "걱정", "패닉", "변동성")
GREED_WORDS = ("탐욕", "몰빵", "레버리지", "추격", "광기", "과열")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_texts(archive_payload: dict[str, Any], dc_payload: dict[str, Any]) -> list[dict[str, str]]:
    texts: list[dict[str, str]] = []
    for post in archive_payload.get("posts", []):
        texts.append(
            {
                "source": "blog",
                "title": post.get("title", ""),
                "summary": post.get("summary", ""),
                "classification": post.get("classification", ""),
                "author": post.get("display_name", ""),
            }
        )
    for post in dc_payload.get("featured_posts", dc_payload.get("posts", [])):
        texts.append(
            {
                "source": "dc",
                "title": post.get("title", ""),
                "summary": post.get("summary", "") or post.get("excerpt", ""),
                "classification": post.get("source_title", ""),
                "author": post.get("author", ""),
            }
        )
    return texts


def _tokenize(text: str) -> list[str]:
    tokens = [match.group(0).lower() for match in WORD_PATTERN.finditer(text)]
    return [token for token in tokens if token not in STOPWORDS and len(token) >= 2]


def _count_keywords(texts: list[dict[str, str]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in texts:
        combined = " ".join([item["title"], item["summary"], item["classification"]])
        counter.update(_tokenize(combined))
    return counter


def _count_named_entities(texts: list[dict[str, str]], mapping: dict[str, tuple[str, ...]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in texts:
        combined = f"{item['title']} {item['summary']}".lower()
        for label, keywords in mapping.items():
            if any(keyword.lower() in combined for keyword in keywords):
                counter[label] += 1
    return counter


def _sentiment_counts(texts: list[dict[str, str]]) -> dict[str, int]:
    counts = {"bullish": 0, "bearish": 0, "fear": 0, "greed": 0}
    for item in texts:
        combined = f"{item['title']} {item['summary']}".lower()
        if any(word in combined for word in BULLISH_WORDS):
            counts["bullish"] += 1
        if any(word in combined for word in BEARISH_WORDS):
            counts["bearish"] += 1
        if any(word in combined for word in FEAR_WORDS):
            counts["fear"] += 1
        if any(word in combined for word in GREED_WORDS):
            counts["greed"] += 1
    return counts


def build_analysis_payload(archive_payload: dict[str, Any], dc_payload: dict[str, Any], generated_at: datetime) -> dict[str, Any]:
    texts = _iter_texts(archive_payload, dc_payload)
    keyword_counts = _count_keywords(texts)
    ticker_counts = _count_named_entities(texts, TICKER_KEYWORDS)
    sector_counts = _count_named_entities(texts, SECTOR_KEYWORDS)
    sentiment = _sentiment_counts(texts)

    top_keywords = [{"label": key, "count": value} for key, value in keyword_counts.most_common(20)]
    top_tickers = [{"label": key, "count": value} for key, value in ticker_counts.most_common(12)]
    top_sectors = [{"label": key, "count": value} for key, value in sector_counts.most_common(12)]
    source_mix = {
        "blog_posts": len(archive_payload.get("posts", [])),
        "dc_featured_posts": len(dc_payload.get("featured_posts", dc_payload.get("posts", []))),
    }

    return {
        "generated_at": generated_at.isoformat(),
        "source_mix": source_mix,
        "top_keywords": top_keywords,
        "top_tickers": top_tickers,
        "top_sectors": top_sectors,
        "sentiment": sentiment,
    }


def render_analysis_html() -> str:
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Keyword Analysis Dashboard</title>
  <style>
    :root {
      --bg: #f4efe6;
      --surface: rgba(255,250,243,0.9);
      --line: rgba(31,41,55,0.12);
      --text: #1f2937;
      --muted: #6b7280;
      --accent: #9a3412;
      --shadow: 0 22px 50px rgba(68,39,12,0.12);
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
    .hero, .panel, .list-card {
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(135deg, rgba(255,255,255,0.74), rgba(255,250,243,0.96));
      box-shadow: var(--shadow);
    }
    .hero, .panel, .list-card { padding: 22px; }
    .hero { margin-bottom: 18px; }
    h1 { margin: 0 0 10px; font-size: clamp(2rem, 4vw, 3.2rem); letter-spacing: -0.04em; }
    .lede, .meta { color: var(--muted); line-height: 1.6; }
    .hero-links { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; }
    .link-btn {
      display: inline-flex; align-items: center; padding: 10px 14px; border-radius: 999px;
      text-decoration: none; background: rgba(255,255,255,0.75); border: 1px solid var(--line);
      color: var(--text); font-weight: 700; font-size: 0.9rem;
    }
    .metrics, .grid { display: grid; gap: 14px; }
    .metrics { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-bottom: 18px; }
    .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .metric-label { display:block; color: var(--muted); font-size: 0.82rem; margin-bottom: 8px; }
    .metric-value { font-size: 1.7rem; font-weight: 800; }
    .list-card h2 { margin: 0 0 14px; font-size: 1rem; }
    .row { display: grid; grid-template-columns: 1fr auto; gap: 12px; padding: 10px 0; border-top: 1px solid rgba(31,41,55,0.08); }
    .row:first-of-type { border-top: 0; padding-top: 0; }
    .row strong { font-size: 0.96rem; }
    .badge {
      display: inline-flex; align-items: center; justify-content: center; min-width: 42px;
      padding: 6px 10px; border-radius: 999px; background: rgba(154,52,18,0.1); color: var(--accent); font-weight: 800;
    }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } .shell { width: min(100% - 20px, 1280px); padding-top: 20px; } }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Market Signal Dashboard</h1>
      <p class="lede">반복적으로 등장하는 키워드, 종목, 섹터, 심리 단어를 모아서 지금 대화가 어디로 쏠리는지 빠르게 보는 보드입니다.</p>
      <div class="meta" id="generated-at">불러오는 중...</div>
      <div class="hero-links">
        <a class="link-btn" href="./">브리핑 메인으로</a>
        <a class="link-btn" href="./semiconductor-gallery.html">디시 갤러리 모음</a>
      </div>
    </section>
    <section class="metrics">
      <article class="panel"><span class="metric-label">블로그 분석 대상</span><div class="metric-value" id="blog-count">-</div></article>
      <article class="panel"><span class="metric-label">디시 픽 분석 대상</span><div class="metric-value" id="dc-count">-</div></article>
      <article class="panel"><span class="metric-label">강세 언급</span><div class="metric-value" id="bullish-count">-</div></article>
      <article class="panel"><span class="metric-label">약세 언급</span><div class="metric-value" id="bearish-count">-</div></article>
    </section>
    <section class="grid">
      <article class="list-card">
        <h2>Top Keywords</h2>
        <div id="keywords"></div>
      </article>
      <article class="list-card">
        <h2>Top Tickers</h2>
        <div id="tickers"></div>
      </article>
      <article class="list-card">
        <h2>Top Sectors</h2>
        <div id="sectors"></div>
      </article>
      <article class="list-card">
        <h2>Sentiment Map</h2>
        <div id="sentiment"></div>
      </article>
    </section>
  </div>
  <script>
    function formatDate(value) {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(date);
    }
    function renderRows(targetId, items) {
      const target = document.getElementById(targetId);
      if (!items.length) {
        target.innerHTML = '<div class="meta">아직 집계 데이터가 없습니다.</div>';
        return;
      }
      target.innerHTML = items.map((item) => `<div class="row"><strong>${item.label}</strong><span class="badge">${item.count}</span></div>`).join("");
    }
    async function boot() {
      const response = await fetch("./data/analysis.json");
      const payload = await response.json();
      document.getElementById("generated-at").textContent = `마지막 분석: ${formatDate(payload.generated_at)}`;
      document.getElementById("blog-count").textContent = payload.source_mix.blog_posts;
      document.getElementById("dc-count").textContent = payload.source_mix.dc_featured_posts;
      document.getElementById("bullish-count").textContent = payload.sentiment.bullish;
      document.getElementById("bearish-count").textContent = payload.sentiment.bearish;
      renderRows("keywords", payload.top_keywords);
      renderRows("tickers", payload.top_tickers);
      renderRows("sectors", payload.top_sectors);
      renderRows("sentiment", [
        { label: "강세", count: payload.sentiment.bullish },
        { label: "약세", count: payload.sentiment.bearish },
        { label: "공포", count: payload.sentiment.fear },
        { label: "탐욕", count: payload.sentiment.greed },
      ]);
    }
    boot().catch((error) => {
      console.error(error);
      document.getElementById("generated-at").textContent = "분석 데이터를 불러오지 못했습니다.";
    });
  </script>
</body>
</html>
"""


def build_analysis_files(output_dir: Path, site_data_dir: Path, site_dir: Path, archive_payload: dict[str, Any], generated_at: datetime) -> None:
    dc_payload = _read_json(output_dir / "dc_community.json")
    analysis_payload = build_analysis_payload(archive_payload, dc_payload, generated_at)
    (site_data_dir / "analysis.json").write_text(json.dumps(analysis_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (site_dir / "analysis.html").write_text(render_analysis_html(), encoding="utf-8")
