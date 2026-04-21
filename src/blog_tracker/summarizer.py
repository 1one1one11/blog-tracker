from __future__ import annotations

from typing import Iterable

import httpx
from openai import OpenAI

from blog_tracker.models import BlogPost


def _fallback_summary(post: BlogPost) -> str:
    text = (post.content_text or post.description_text).strip()
    if not text:
        return "RSS 설명이 비어 있어 원문 링크 확인이 필요합니다."
    return text[:220] + ("..." if len(text) > 220 else "")


class Summarizer:
    def __init__(self, openai_api_key: str, openai_model: str, gemini_api_key: str = "", gemini_model: str = "") -> None:
        self.provider = "none"
        self.model = ""
        self.client = None
        self.gemini_api_key = gemini_api_key
        if gemini_api_key and gemini_model:
            self.provider = "gemini"
            self.model = gemini_model
        elif openai_api_key and openai_model:
            self.provider = "openai"
            self.model = openai_model
            self.client = OpenAI(api_key=openai_api_key)

    def summarize_post(self, post: BlogPost) -> str:
        prompt = (
            "다음 네이버 블로그 글을 한국어로 2문장 이내로 요약해 주세요. "
            "투자자 판단에 필요한 핵심 주장, 데이터 포인트, 리스크를 우선 반영해 주세요.\n\n"
            f"블로그명: {post.blog_title or post.display_name}\n"
            f"작성자: {post.display_name}\n"
            f"카테고리: {post.category}\n"
            f"제목: {post.title}\n"
            f"태그: {', '.join(post.tags)}\n"
            f"본문 발췌: {(post.content_text or post.description_text)[:5000]}"
        )
        return self.summarize_text(prompt, _fallback_summary(post))

    def summarize_text(self, prompt: str, fallback_text: str) -> str:
        if self.provider == "none":
            return fallback_text

        try:
            if self.provider == "openai":
                response = self.client.responses.create(
                    model=self.model,
                    input=prompt,
                )
                text = getattr(response, "output_text", "").strip()
                return text or fallback_text

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            }
            with httpx.Client(timeout=40) as client:
                response = client.post(url, params={"key": self.gemini_api_key}, json=payload)
                response.raise_for_status()
                data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return fallback_text
            parts = candidates[0].get("content", {}).get("parts", [])
            text = " ".join(part.get("text", "") for part in parts).strip()
            return text or fallback_text
        except Exception:
            return fallback_text

    def summarize_all(self, posts: Iterable[BlogPost]) -> list[BlogPost]:
        enriched: list[BlogPost] = []
        for post in posts:
            post.summary = self.summarize_post(post)
            enriched.append(post)
        return enriched
