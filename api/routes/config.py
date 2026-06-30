"""App config routes."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter

from api.schemas import AppConfig, LLMConfig, ResearchConfig
from src.config import CONFIG_DIR

router = APIRouter()


@router.get("/config", response_model=AppConfig)
def get_config():
    config_path = CONFIG_DIR / "config.toml"
    if not config_path.exists():
        return AppConfig(
            llm=LLMConfig(api_key_set=bool(os.environ.get("OPENWORK_API_KEY") or os.environ.get("OPENAI_API_KEY"))),
            research=ResearchConfig(
                semantic_scholar_api_key_set=bool(os.environ.get("SEMANTIC_SCHOLAR_API_KEY")),
                openalex_api_key_set=bool(os.environ.get("OPENALEX_API_KEY")),
            ),
        )

    try:
        import toml
        cfg = toml.load(config_path)
    except Exception:
        return AppConfig(
            llm=LLMConfig(api_key_set=bool(os.environ.get("OPENWORK_API_KEY") or os.environ.get("OPENAI_API_KEY"))),
            research=ResearchConfig(
                semantic_scholar_api_key_set=bool(os.environ.get("SEMANTIC_SCHOLAR_API_KEY")),
                openalex_api_key_set=bool(os.environ.get("OPENALEX_API_KEY")),
            ),
        )

    llm = cfg.get("llm", {})
    research = cfg.get("research", {})

    api_key = llm.get("api_key", "")
    if not api_key:
        api_key = os.environ.get("OPENWORK_API_KEY") or os.environ.get("OPENAI_API_KEY", "")

    return AppConfig(
        llm=LLMConfig(
            provider=llm.get("provider", "openai"),
            model=llm.get("model", "gpt-4o-mini"),
            base_url=llm.get("base_url", ""),
            temperature=llm.get("temperature", 0.7),
            api_key_set=bool(api_key),
        ),
        research=ResearchConfig(
            semantic_scholar_api_key_set=bool(
                research.get("semantic_scholar_api_key")
                or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
            ),
            openalex_api_key_set=bool(
                research.get("openalex_api_key")
                or os.environ.get("OPENALEX_API_KEY")
            ),
            max_papers_per_query=research.get("max_papers_per_query", 15),
        ),
    )


@router.put("/config")
def update_config(data: dict):
    config_path = CONFIG_DIR / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import toml
        existing = toml.load(config_path)
    except Exception:
        existing = {}

    for section, values in data.items():
        if isinstance(values, dict):
            existing.setdefault(section, {}).update(values)
        else:
            existing[section] = values

    with open(config_path, "w") as f:
        toml.dump(existing, f)

    return {"ok": True}
