"""Export / file download routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.config import get_output_dir

router = APIRouter()


@router.get("/{job_id}/chapters/{chapter_number}/export")
def export_chapter(job_id: str, chapter_number: int, format: str = "md"):
    output_dir = get_output_dir() / job_id

    if format == "md":
        for suffix in ["_compiled.md", "_v2.md", ".md"]:
            path = output_dir / f"chapter_{chapter_number}{suffix}"
            if path.exists():
                return FileResponse(
                    path,
                    media_type="text/markdown",
                    filename=f"chapter_{chapter_number}.md",
                )
    elif format == "docx":
        path = output_dir / f"chapter_{chapter_number}.docx"
        if path.exists():
            return FileResponse(
                path,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                filename=f"chapter_{chapter_number}.docx",
            )
        md_path = output_dir / f"chapter_{chapter_number}.docx.md"
        if md_path.exists():
            return FileResponse(
                md_path,
                media_type="text/markdown",
                filename=f"chapter_{chapter_number}.docx.md",
            )
    elif format == "pdf":
        path = output_dir / f"chapter_{chapter_number}.pdf"
        if path.exists():
            return FileResponse(
                path,
                media_type="application/pdf",
                filename=f"chapter_{chapter_number}.pdf",
            )
        md_path = output_dir / f"chapter_{chapter_number}.pdf.md"
        if md_path.exists():
            return FileResponse(
                md_path,
                media_type="text/markdown",
                filename=f"chapter_{chapter_number}.pdf.md",
            )
    elif format == "references":
        refs_path = output_dir / "references.md"
        if refs_path.exists():
            return FileResponse(
                refs_path,
                media_type="text/markdown",
                filename="references.md",
            )

    raise HTTPException(status_code=404, detail=f"Export not found for format '{format}'")
