"""
llm.py — one small door to whichever chat model is configured.

    from arqa.llm import chat
    text = chat([{"role": "user", "content": "..."}], json_mode=True)

Configuration is by environment variables (put them in .env):

    GROQ_API_KEY       Groq (free tier) — https://console.groq.com. Default provider.
    OPENAI_API_KEY     OpenAI, or any OpenAI-compatible server with LLM_BASE_URL.
    LLM_PROVIDER       "groq" | "openai"   (default: groq if GROQ_API_KEY is set)
    LLM_MODEL          the answering model (default: openai/gpt-oss-120b on Groq)
    LLM_JUDGE_MODEL    a cheaper model for the eval judge (default: openai/gpt-oss-20b)

Why a wrapper at all: the answerer and the judge should not care which vendor
is behind them, and the retry/backoff for rate limits (Groq's free tier is
30 requests/min and has a daily token cap) belongs in exactly one place.
Groq and OpenAI share the chat-completions wire format, so one client does both.
"""

from __future__ import annotations

import os
import time
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULTS = {
    # Groq retired its Llama 3.x models on 2026-08-16; these are the replacements it names.
    "groq":   {"model": "openai/gpt-oss-120b", "judge": "openai/gpt-oss-20b"},
    "openai": {"model": "gpt-4o-mini", "judge": "gpt-4o-mini"},
}


def provider() -> str:
    """LLM_PROVIDER if it is set AND its key exists; otherwise whichever key exists.
    (A stale LLM_PROVIDER=openai in .env next to a fresh GROQ_API_KEY should
    not send anyone on a hunt for an OpenAI key.)"""
    p = os.getenv("LLM_PROVIDER", "").strip().lower()
    keys = {"groq": bool(os.getenv("GROQ_API_KEY")), "openai": bool(os.getenv("OPENAI_API_KEY"))}
    if p in keys and keys[p]:
        return p
    if keys["groq"]:
        return "groq"
    if keys["openai"]:
        return "openai"
    return p or "groq"


class ConfigError(RuntimeError):
    """Missing key or similar — not worth retrying."""


def model_name(role: str = "model") -> str:
    env = "LLM_MODEL" if role == "model" else "LLM_JUDGE_MODEL"
    return os.getenv(env) or DEFAULTS[provider()][role]


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI  # imported lazily so tests can run without it

    p = provider()
    if p == "groq":
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ConfigError("GROQ_API_KEY is not set — put it in .env (see .env.example)")
        return OpenAI(api_key=key, base_url=GROQ_BASE_URL)
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ConfigError("No API key found — put GROQ_API_KEY (or OPENAI_API_KEY) in .env (see .env.example)")
    return OpenAI(api_key=key, base_url=os.getenv("LLM_BASE_URL") or None)


def chat(messages: list[dict], *, model: str | None = None, json_mode: bool = False,
         temperature: float = 0.0, max_tokens: int = 1200, retries: int = 5) -> str:
    """Return the assistant's text. Retries on rate limits / transient errors
    with exponential backoff (2, 4, 8, 16, 32 s)."""
    model = model or model_name("model")
    kwargs: dict = {"model": model, "messages": messages,
                    "temperature": temperature, "max_tokens": max_tokens}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if "gpt-oss" in model:
        # Reasoning models spend output tokens thinking before the JSON; keep
        # that short — this is extraction, not a puzzle — and leave room for it.
        kwargs["extra_body"] = {"reasoning_effort": "low"}
        kwargs["max_tokens"] = max(max_tokens, 2500)
    delay = 2.0
    last: Exception | None = None
    for attempt in range(retries):
        try:
            resp = _client().chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except ConfigError:
            raise
        except Exception as e:  # noqa: BLE001 — vendor exception classes vary
            last = e
            status = getattr(e, "status_code", None)
            transient = status in (408, 409, 429, 500, 502, 503, 504) or status is None
            if not transient or attempt == retries - 1:
                raise
            # Groq's 429 says how long to wait; honour it when present.
            wait = delay
            try:
                hdr = e.response.headers.get("retry-after")  # type: ignore[attr-defined]
                if hdr:
                    wait = max(wait, float(hdr))
            except Exception:  # noqa: BLE001
                pass
            time.sleep(wait)
            delay *= 2
    raise RuntimeError(f"LLM call failed after {retries} attempts: {last}")
