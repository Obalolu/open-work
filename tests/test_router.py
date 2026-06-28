"""Tests for the prompt router (prompt_loader and prompt_merger)."""

import pytest
from pathlib import Path

from src.router.prompt_loader import (
    load_chapter_template,
    load_style_template,
    load_base_prompt,
    list_chapter_templates,
    list_style_templates,
)
from src.router.prompt_merger import (
    build_system_prompt,
    build_research_prompt,
    build_review_prompt,
    _format_style,
    _format_chapter,
    _format_job,
)


class TestPromptLoader:
    def test_load_chapter_template(self):
        config = load_chapter_template("chapter_1.yaml")
        assert config["name"] == "Introduction"
        assert len(config["sections"]) > 0

    def test_load_style_template(self):
        config = load_style_template("academic_balanced.yaml")
        assert "tone" in config
        assert "formality" in config

    def test_load_base_prompt(self):
        prompt = load_base_prompt("writer")
        assert "ACADEMIC WRITER" in prompt
        assert len(prompt) > 100

    def test_load_nonexistent_chapter(self):
        with pytest.raises(FileNotFoundError):
            load_chapter_template("nonexistent.yaml")

    def test_list_chapter_templates(self):
        templates = list_chapter_templates()
        assert "chapter_1.yaml" in templates
        assert "chapter_2.yaml" in templates

    def test_list_style_templates(self):
        templates = list_style_templates()
        assert "academic_balanced.yaml" in templates


class TestPromptMerger:
    def test_build_system_prompt(self):
        base = "# Writer\nYou write academic papers."
        chapter = {
            "name": "Introduction",
            "sections": [{"id": "1.1", "title": "Background", "paragraphs": 3, "word_count": 500}],
            "forbidden": ["furthermore"],
            "required": ["Must cite sources"],
        }
        style = {
            "tone": "professional",
            "formality": 0.7,
            "preferred_voice": "active",
            "forbidden_phrases": ["delve into"],
        }
        job = {"topic": "AI in Healthcare", "citation_style": "apa"}

        result = build_system_prompt(base, chapter, style, job)

        assert "WRITING INSTRUCTIONS" in result
        assert "STYLE CONFIGURATION" in result
        assert "CHAPTER STRUCTURE" in result
        assert "JOB CONTEXT" in result
        assert "professional" in result
        assert "AI in Healthcare" in result
        assert "furthermore" in result
        assert "Background" in result

    def test_build_research_prompt(self):
        chapter = {
            "name": "Introduction",
            "sections": [
                {"id": "1.1", "title": "Background", "instructions": "Find papers on AI diagnostics"},
            ],
        }
        job = {"topic": "AI in Healthcare", "paper_type": "literature_review", "citation_style": "apa"}

        result = build_research_prompt(chapter, job)

        assert "AI in Healthcare" in result
        assert "Introduction" in result
        assert "Background" in result
        assert "cite_" in result

    def test_format_style(self):
        style = {
            "tone": "professional",
            "formality": 0.7,
            "preferred_voice": "active",
            "introduction_style": "narrative_hook",
            "max_bullet_points_per_section": 2,
            "forbidden_phrases": ["furthermore", "delve into"],
        }
        result = _format_style(style)
        assert "professional" in result
        assert "0.7" in result
        assert "furthermore" in result

    def test_format_chapter(self):
        chapter = {
            "name": "Introduction",
            "sections": [
                {"id": "1.1", "title": "Background", "paragraphs": 3, "word_count": 500, "instructions": "Be thorough"},
            ],
            "forbidden": ["furthermore"],
            "required": ["Must cite sources"],
        }
        result = _format_chapter(chapter)
        assert "Introduction" in result
        assert "Background" in result
        assert "3 paragraphs" in result or "Paragraphs: 3" in result
        assert "500" in result

    def test_format_job(self):
        job = {"topic": "AI in Healthcare", "paper_type": "literature_review", "citation_style": "apa"}
        result = _format_job(job)
        assert "AI in Healthcare" in result
        assert "literature_review" in result

    def test_build_review_prompt_style(self):
        result = build_review_prompt("Some chapter text.", {}, review_type="style")
        assert "style consistency" in result.lower() or "Style" in result
        assert "Some chapter text" in result

    def test_build_review_prompt_fact_check(self):
        result = build_review_prompt("Some chapter text.", {}, review_type="fact_check")
        assert "fact" in result.lower() or "Fact" in result
