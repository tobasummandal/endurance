"""Thin Gemini wrapper. All prompts live in prompts/ as text files."""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from .config import settings

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def generate(model: str, prompt: str, *, json_mode: bool = False, max_output_tokens: int = 8192) -> str:
    client = _get_client()
    config = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=max_output_tokens,
        response_mime_type="application/json" if json_mode else None,
    )
    resp = client.models.generate_content(model=model, contents=prompt, config=config)
    return resp.text or ""


_FENCE_RE = re.compile(r"^```(?:json|python)?\s*\n(.*?)\n```\s*$", re.DOTALL)


def strip_fence(text: str) -> str:
    text = text.strip()
    m = _FENCE_RE.match(text)
    return m.group(1) if m else text


def parse_json(text: str) -> Any:
    return json.loads(strip_fence(text))
