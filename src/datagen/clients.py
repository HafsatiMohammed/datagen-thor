from __future__ import annotations

import os
import requests
from openai import OpenAI


class OllamaClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")

    def generate(self, *, model: str, prompt: str, system: str, temperature: float, max_tokens: int) -> str:
        resp = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
            timeout=600,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")


class OpenAICompatibleClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.client = OpenAI(
            base_url=base_url or os.getenv("OPENAI_BASE_URL") or "http://localhost:8000/v1",
            api_key=api_key or os.getenv("OPENAI_API_KEY") or "EMPTY",
        )

    def generate(self, *, model: str, prompt: str, system: str, temperature: float, max_tokens: int) -> str:
        resp = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""
