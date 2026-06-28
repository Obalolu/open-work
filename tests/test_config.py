"""Tests for the config module."""

import os
from pathlib import Path

import pytest
import yaml
import toml

from src.config import (
    load_yaml,
    save_yaml,
    load_toml,
    get_llm_config,
    get_research_config,
    get_project_root,
    get_prompts_dir,
    get_jobs_dir,
    get_output_dir,
)


class TestLoadYaml:
    def test_load_valid_yaml(self, tmp_path):
        data = {"key": "value", "nested": {"a": 1}}
        f = tmp_path / "test.yaml"
        f.write_text(yaml.dump(data))
        result = load_yaml(f)
        assert result == data

    def test_load_empty_yaml(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        result = load_yaml(f)
        assert result == {}

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_yaml(Path("/nonexistent/file.yaml"))


class TestSaveYaml:
    def test_save_and_load(self, tmp_path):
        data = {"topic": "AI", "chapters": [1, 2, 3]}
        path = tmp_path / "job.yaml"
        save_yaml(data, path)
        loaded = load_yaml(path)
        assert loaded["topic"] == "AI"
        assert loaded["chapters"] == [1, 2, 3]

    def test_save_creates_directories(self, tmp_path):
        data = {"test": True}
        path = tmp_path / "sub" / "dir" / "file.yaml"
        save_yaml(data, path)
        assert path.exists()


class TestLoadToml:
    def test_load_valid_toml(self, tmp_path):
        content = '[llm]\nprovider = "openai"\napi_key = "test123"\n'
        f = tmp_path / "config.toml"
        f.write_text(content)
        result = load_toml(f)
        assert result["llm"]["provider"] == "openai"
        assert result["llm"]["api_key"] == "test123"


class TestGetLlmConfig:
    def test_returns_dict(self):
        config = get_llm_config()
        assert isinstance(config, dict)
        assert "provider" in config
        assert "model" in config

    def test_has_default_values(self):
        config = get_llm_config()
        assert config["temperature"] == 0.7


class TestGetResearchConfig:
    def test_returns_dict(self):
        config = get_research_config()
        assert isinstance(config, dict)
        assert "max_papers_per_query" in config


class TestGetDirectories:
    def test_project_root(self):
        root = get_project_root()
        assert root.exists()
        assert root.is_dir()

    def test_prompts_dir(self):
        d = get_prompts_dir()
        assert "prompts" in str(d)

    def test_jobs_dir(self):
        d = get_jobs_dir()
        assert "jobs" in str(d)

    def test_output_dir(self):
        d = get_output_dir()
        assert "output" in str(d)
