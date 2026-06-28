"""Tests for the export module."""

import pytest
from pathlib import Path

from src.export.exporter import export_markdown, export_docx, export_chapter


class TestExportMarkdown:
    def test_creates_file(self, tmp_path):
        content = "# Test\n\nHello world."
        result = export_markdown(content, tmp_path, "test.md")
        assert result.exists()
        assert result.read_text() == content

    def test_creates_directories(self, tmp_path):
        content = "test"
        result = export_markdown(content, tmp_path / "sub" / "dir", "test.md")
        assert result.exists()


class TestExportDocx:
    def test_creates_file_or_fallback(self, tmp_path):
        content = "# Test\n\nHello world."
        result = export_docx(content, tmp_path, "test.docx")
        assert result.exists()


class TestExportChapter:
    def test_exports_markdown(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.export.exporter.get_output_dir", lambda: tmp_path)
        content = "# Chapter 1\n\nContent here."
        result = export_chapter(content, "test_job", 1, ["md"])
        assert "md" in result
        assert result["md"].exists()

    def test_exports_multiple_formats(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.export.exporter.get_output_dir", lambda: tmp_path)
        content = "# Chapter 1\n\nContent here."
        result = export_chapter(content, "test_job", 2, ["md", "docx"])
        assert "md" in result
        assert "docx" in result
