"""Unified LLM client supporting OpenAI-compatible APIs."""

from __future__ import annotations

import json
from typing import Any

import httpx

from src.config import get_llm_config


async def call_llm(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> str:
    """Call an LLM via OpenAI-compatible API.

    Works with OpenAI, Anthropic (via proxy), DeepSeek, Ollama, and any
    OpenAI-compatible endpoint.
    """
    config = get_llm_config()
    provider = config.get("provider", "openai")
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "")
    used_model = model or config.get("model", "gpt-4o-mini")
    used_temp = temperature if temperature is not None else config.get("temperature", 0.7)

    if not base_url:
        if provider == "openai":
            base_url = "https://api.openai.com/v1"
        elif provider == "deepseek":
            base_url = "https://api.deepseek.com/v1"
        elif provider == "ollama":
            base_url = "http://localhost:11434/v1"
        else:
            base_url = "https://api.openai.com/v1"

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload: dict[str, Any] = {
        "model": used_model,
        "messages": messages,
        "temperature": used_temp,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"]


async def call_llm_json(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Call an LLM and parse the response as JSON."""
    json_system = (
        (system_prompt or "")
        + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, just JSON."
    )
    raw = await call_llm(
        prompt=prompt,
        system_prompt=json_system,
        temperature=temperature,
        model=model,
    )
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])
    return json.loads(cleaned)
