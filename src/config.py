"""Global configuration loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import toml
import yaml


CONFIG_DIR = Path(os.environ.get("OPENWORK_CONFIG_DIR", Path.home() / ".config" / "open-work"))
DATA_DIR = Path(os.environ.get("OPENWORK_DATA_DIR", Path(__file__).resolve().parent.parent))


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file and return its contents."""
    with open(path, "r", encoding="utf-8") as f:
        return toml.load(f)


def save_yaml(data: dict[str, Any], path: Path) -> None:
    """Save data to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def get_llm_config() -> dict[str, Any]:
    """Get LLM configuration from environment or config file."""
    config_path = CONFIG_DIR / "config.toml"
    if config_path.exists():
        cfg = load_toml(config_path)
        return cfg.get("llm", {})

    return {
        "provider": os.environ.get("OPENWORK_LLM_PROVIDER", "openai"),
        "api_key": os.environ.get("OPENWORK_API_KEY") or os.environ.get("OPENAI_API_KEY", ""),
        "model": os.environ.get("OPENWORK_MODEL", "gpt-4o-mini"),
        "base_url": os.environ.get("OPENWORK_BASE_URL", ""),
        "temperature": float(os.environ.get("OPENWORK_TEMPERATURE", "0.7")),
    }


def get_research_config() -> dict[str, Any]:
    """Get research API configuration."""
    config_path = CONFIG_DIR / "config.toml"
    if config_path.exists():
        cfg = load_toml(config_path)
        research = cfg.get("research", {})
        # Proxy list: prefer env var, fall back to config file
        if not research.get("proxy_list"):
            research["proxy_list"] = os.environ.get("PROXY_LIST", "")
        return research

    return {
        "semantic_scholar_api_key": os.environ.get("SEMANTIC_SCHOLAR_API_KEY", ""),
        "openalex_api_key": os.environ.get("OPENALEX_API_KEY", ""),
        "openalex_email": os.environ.get("OPENALEX_EMAIL", ""),
        "proxy_list": os.environ.get("PROXY_LIST", ""),
        "max_papers_per_query": int(os.environ.get("OPENWORK_MAX_PAPERS", "15")),
        "enable_semantic_scholar": os.environ.get("ENABLE_SEMANTIC_SCHOLAR", "true").lower() != "false",
        "enable_openalex": os.environ.get("ENABLE_OPENALEX", "true").lower() != "false",
        "enable_crossref": os.environ.get("ENABLE_CROSSREF", "true").lower() != "false",
        "enable_arxiv": os.environ.get("ENABLE_ARXIV", "true").lower() != "false",
    }


def get_project_root() -> Path:
    """Get the project root directory."""
    return DATA_DIR


def get_prompts_dir() -> Path:
    """Get the prompts directory."""
    return get_project_root() / "prompts"


def get_jobs_dir() -> Path:
    """Get the jobs directory."""
    return get_project_root() / "jobs"


def get_output_dir() -> Path:
    """Get the output directory."""
    return get_project_root() / "output"
