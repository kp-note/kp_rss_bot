from __future__ import annotations

from dataclasses import dataclass

import google.generativeai as genai
from openai import OpenAI


@dataclass
class SummaryConfig:
    provider: str
    gemini_api_key: str
    gemini_model: str
    openai_api_key: str
    openai_model: str


class Summarizer:
    def __init__(self, config: SummaryConfig):
        self.config = config
        self.provider = config.provider
        self._openai: OpenAI | None = None
        if config.openai_api_key:
            self._openai = OpenAI(api_key=config.openai_api_key)
        if config.gemini_api_key:
            genai.configure(api_key=config.gemini_api_key)

    def summarize_ko(self, title: str, url: str, content: str) -> str | None:
        prompt = (
            "다음 글을 한국어로 요약하세요.\n"
            "출력 형식:\n"
            "1) 핵심 요약 (4~6줄)\n"
            "2) 주요 논거 3~4개\n"
            "3) 투자 관점 체크포인트 2개\n\n"
            f"제목: {title}\n"
            f"링크: {url}\n"
            f"본문:\n{content[:12000]}"
        )

        if self.provider == "gemini":
            result = self._summarize_gemini(prompt)
            if result:
                return result
            result = self._summarize_openai(prompt)
            if result:
                return result
        else:
            result = self._summarize_openai(prompt)
            if result:
                return result
            result = self._summarize_gemini(prompt)
            if result:
                return result

        return None

    def _summarize_gemini(self, prompt: str) -> str | None:
        if not self.config.gemini_api_key:
            return None
        try:
            model = genai.GenerativeModel(self.config.gemini_model)
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()
            return text or None
        except Exception:
            return None

    def _summarize_openai(self, prompt: str) -> str | None:
        if not self._openai:
            return None
        try:
            resp = self._openai.responses.create(
                model=self.config.openai_model,
                input=prompt,
            )
            text = (resp.output_text or "").strip()
            return text or None
        except Exception:
            return None

