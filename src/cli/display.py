"""Rich-based display utilities for the CLI."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.markdown import Markdown
from rich.text import Text
from rich.columns import Columns
from rich import box

console = Console()


def show_banner():
    """Display the application banner."""
    banner = Text("open-work", style="bold cyan")
    subtitle = Text("Automated Research Paper Writing System", style="dim")
    console.print(Panel(Columns([banner, subtitle], padding=(0, 2)), box=box.DOUBLE))


def show_job_summary(job_config: dict[str, Any], chapters: list[int], style: str):
    """Display job configuration summary."""
    table = Table(title="Job Configuration", box=box.ROUNDED, show_header=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")

    table.add_row("Topic", job_config.get("topic", "N/A"))
    table.add_row("Paper Type", job_config.get("paper_type", "N/A"))
    table.add_row("Citation Style", job_config.get("citation_style", "N/A"))
    table.add_row("Audience", job_config.get("target_audience", "N/A"))
    table.add_row("Chapters", ", ".join(str(c) for c in chapters))
    table.add_row("Style", style)

    console.print(table)


def show_research_progress(papers_found: int, queries: int):
    """Show research phase progress."""
    console.print(f"  [cyan]🔍[/] Researching... found [bold]{papers_found}[/] papers across [bold]{queries}[/] queries")


def show_writing_progress(chapter: int, total: int, word_count: int = 0, target: int = 0):
    """Show writing progress."""
    status = f"  [cyan]✍[/] Writing Chapter {chapter}/{total}"
    if word_count > 0:
        status += f"... {word_count}/{target} words"
    console.print(status)


def show_review_result(
    review_type: str,
    score: int,
    passed: bool,
    issues_count: int,
):
    """Show review result."""
    icon = "[green]✓[/]" if passed else "[red]✗[/]"
    console.print(
        f"  {icon} {review_type}: score [bold]{score}/100[/] — "
        f"[bold]{issues_count}[/] issues found"
    )


def show_humanize_result(steps: int, original_len: int, final_len: int):
    """Show humanization result."""
    change = final_len - original_len
    direction = "+" if change > 0 else ""
    console.print(
        f"  [magenta]🔄[/] Humanized: {steps} steps, "
        f"{original_len} → {final_len} chars ({direction}{change})"
    )


def show_detection_result(score: float, passed: bool, threshold: float):
    """Show AI detection result."""
    icon = "[green]✓ PASS[/]" if passed else "[red]✗ FAIL[/]"
    console.print(
        f"  [yellow]🔍[/] AI Detection: score [bold]{score:.1f}/100[/] "
        f"(threshold: {threshold}) {icon}"
    )


def show_export_result(format_name: str, path: Any):
    """Show export result."""
    console.print(f"  [blue]📄[/] Exported {format_name}: {path}")


def show_chapter_complete(chapter: int, total: int, score: int):
    """Show chapter completion."""
    console.print(
        f"\n[bold green]✓ Chapter {chapter}/{total} complete[/] "
        f"(quality score: {score}/100)\n"
    )


def show_error(message: str):
    """Show an error message."""
    console.print(f"[bold red]Error:[/] {message}")


def show_warning(message: str):
    """Show a warning message."""
    console.print(f"[yellow]Warning:[/] {message}")


def show_success(message: str):
    """Show a success message."""
    console.print(f"[bold green]✓[/] {message}")


def show_info(message: str):
    """Show an info message."""
    console.print(f"[cyan]ℹ[/] {message}")


def show_issues_table(issues: list[dict[str, Any]], title: str = "Issues"):
    """Display issues in a formatted table."""
    if not issues:
        console.print(f"  [green]No issues found![/]")
        return

    table = Table(title=title, box=box.SIMPLE)
    table.add_column("Type", style="bold")
    table.add_column("Severity")
    table.add_column("Description")

    severity_colors = {"high": "red", "medium": "yellow", "low": "dim"}

    for iss in issues:
        sev = iss.get("severity", "low")
        color = severity_colors.get(sev, "white")
        table.add_row(
            iss.get("type", "unknown"),
            f"[{color}]{sev}[/]",
            iss.get("description", "")[:80],
        )

    console.print(table)


def show_detection_details(details: dict[str, float], phrases: list[str]):
    """Show detailed detection analysis."""
    table = Table(title="Detection Analysis", box=box.SIMPLE, show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Score")

    for metric, score in details.items():
        bar_len = int(score / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        table.add_row(metric, f"{bar} {score:.1f}")

    console.print(table)

    if phrases:
        console.print("\n  [yellow]Flagged phrases:[/]")
        for p in phrases[:10]:
            console.print(f"    - \"{p}\"")


def show_completion_summary(results: dict[str, Any]):
    """Show final completion summary."""
    table = Table(title="Generation Complete", box=box.DOUBLE, show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Chapters Generated", str(results.get("chapters", 0)))
    table.add_row("Total Words", str(results.get("total_words", 0)))
    table.add_row("Avg Quality Score", str(results.get("avg_score", 0)))
    table.add_row("AI Detection", results.get("detection_status", "N/A"))
    table.add_row("Output Directory", str(results.get("output_dir", "")))

    console.print(table)
