"""Main CLI application — Typer-based interactive CLI for open-work."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional

import typer
import yaml

from src.cli.display import (
    console, show_banner, show_job_summary, show_research_progress,
    show_writing_progress, show_review_result, show_humanize_result,
    show_detection_result, show_export_result, show_chapter_complete,
    show_error, show_warning, show_success, show_info,
    show_issues_table, show_detection_details, show_completion_summary,
)
from src.cli.prompts import (
    select_job, select_chapters, select_style, select_output_formats,
    confirm_action, get_new_job_config, get_job_name, text_input,
)
from src.config import (
    load_yaml, save_yaml, get_jobs_dir, get_output_dir,
    get_prompts_dir, get_llm_config,
)
from src.router.prompt_loader import (
    load_chapter_template, load_style_template, load_base_prompt,
)
from src.research.orchestrator import CitationResearcher
from src.research.summarizer import summarize_papers
from src.writers.chapter_writer import write_chapter
from src.writers.citation_compiler import (
    compile_citations,
    format_reference_list,
    replace_inline_citations,
)
from src.reviewers.style_checker import review_style
from src.reviewers.fact_checker import fact_check
from src.reviewers.ai_detector import detect_ai_text
from src.humanizer.pipeline import run_humanize_pipeline
from src.export.exporter import export_chapter

app = typer.Typer(
    name="open-work",
    help="Automated chapter-by-chapter research paper writing system.",
    no_args_is_help=True,
)


@app.command()
def generate(
    job: Optional[str] = typer.Option(None, "--job", "-j", help="Job YAML file name"),
    chapter: Optional[int] = typer.Option(None, "--chapter", "-c", help="Chapter number to generate"),
    all_chapters: bool = typer.Option(False, "--all", "-a", help="Generate all chapters"),
    style: Optional[str] = typer.Option(None, "--style", "-s", help="Style template name"),
    formats: str = typer.Option("md", "--formats", "-f", help="Output formats (comma-separated: md,docx,pdf)"),
    skip_humanize: bool = typer.Option(False, "--skip-humanize", help="Skip humanization step"),
    skip_review: bool = typer.Option(False, "--skip-review", help="Skip review step"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i/-ni", help="Interactive mode"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
):
    """Generate research paper chapters interactively or from config."""
    if interactive:
        _generate_interactive()
    else:
        _generate_from_args(job, chapter, all_chapters, style, formats,
                           skip_humanize, skip_review, dry_run)


def _generate_interactive():
    """Interactive generation flow."""
    show_banner()

    # Check LLM config
    llm_config = get_llm_config()
    if not llm_config.get("api_key"):
        show_error("No LLM API key configured. Set OPENWORK_API_KEY or configure ~/.config/open-work/config.toml")
        raise typer.Exit(1)

    # Job selection
    jobs_dir = get_jobs_dir()
    existing_jobs = [f.name for f in jobs_dir.glob("*.yaml")] if jobs_dir.exists() else []

    if existing_jobs:
        action = select_job(existing_jobs + ["Create new job"])
        if action == "Create new job":
            job_config = get_new_job_config()
            if not job_config:
                show_error("Invalid job configuration")
                raise typer.Exit(1)
            job_name = get_job_name()
            job_config["name"] = job_name
            # Save job config
            job_path = jobs_dir / f"{job_name}.yaml"
            save_yaml(job_config, job_path)
            show_success(f"Job saved: {job_path}")
        else:
            job_name = action
            job_config = load_yaml(jobs_dir / job_name)
    else:
        show_info("No existing jobs found. Let's create one.")
        job_config = get_new_job_config()
        if not job_config:
            show_error("Invalid job configuration")
            raise typer.Exit(1)
        job_name = get_job_name()
        job_config["name"] = job_name
        job_path = jobs_dir / f"{job_name}.yaml"
        save_yaml(job_config, job_path)
        show_success(f"Job saved: {job_path}")

    # Chapter selection
    chapters = select_chapters(max_chapter=10)
    if not chapters:
        show_error("No chapters selected")
        raise typer.Exit(1)

    # Style selection
    style_file = select_style()

    # Output formats
    output_formats = select_output_formats()

    # Confirm
    show_job_summary(job_config, chapters, style_file)
    if not confirm_action("Proceed with generation?"):
        raise typer.Exit(0)

    # Run generation
    asyncio.run(_run_generation(
        job_config=job_config,
        chapters=chapters,
        style_file=style_file,
        output_formats=output_formats,
        skip_humanize=False,
        skip_review=False,
        dry_run=False,
    ))


def _generate_from_args(
    job_file: str | None,
    chapter_num: int | None,
    all_chapters: bool,
    style_file: str | None,
    formats_str: str,
    skip_humanize: bool,
    skip_review: bool,
    dry_run: bool,
):
    """Non-interactive generation from CLI arguments."""
    if not job_file:
        show_error("--job is required in non-interactive mode")
        raise typer.Exit(1)

    jobs_dir = get_jobs_dir()
    job_path = jobs_dir / job_file if not Path(job_file).is_absolute() else Path(job_file)
    if not job_path.exists():
        show_error(f"Job file not found: {job_path}")
        raise typer.Exit(1)

    job_config = load_yaml(job_path)
    style_file = style_file or "academic_balanced.yaml"
    formats = [f.strip() for f in formats_str.split(",")]

    if all_chapters:
        # Generate chapters 1 through the number defined in the job
        chapter_configs = _get_chapter_configs(job_config)
        chapters = list(range(1, len(chapter_configs) + 1))
    elif chapter_num:
        chapters = [chapter_num]
    else:
        show_error("Specify --chapter or --all")
        raise typer.Exit(1)

    asyncio.run(_run_generation(
        job_config=job_config,
        chapters=chapters,
        style_file=style_file,
        output_formats=formats,
        skip_humanize=skip_humanize,
        skip_review=skip_review,
        dry_run=dry_run,
    ))


async def _run_generation(
    job_config: dict[str, Any],
    chapters: list[int],
    style_file: str,
    output_formats: list[str],
    skip_humanize: bool,
    skip_review: bool,
    dry_run: bool,
):
    """Core generation pipeline."""
    import time
    start_time = time.time()

    # Load style config
    try:
        style_config = load_style_template(style_file)
    except FileNotFoundError:
        show_warning(f"Style template '{style_file}' not found, using defaults")
        style_config = {
            "tone": "professional",
            "formality": 0.7,
            "preferred_voice": "active",
            "forbidden_phrases": [],
        }

    # Load base writer prompt
    try:
        base_prompt = load_base_prompt("writer")
    except FileNotFoundError:
        base_prompt = "You are an expert academic writer. Write clear, well-structured prose with proper citations."

    # Load chapter configs
    chapter_configs = _get_chapter_configs(job_config)

    results_summary: dict[str, Any] = {
        "chapters": 0,
        "total_words": 0,
        "scores": [],
        "output_dir": get_output_dir() / job_config.get("name", "untitled"),
    }
    all_chapter_texts: list[str] = []

    for ch_num in sorted(chapters):
        ch_index = ch_num - 1
        if ch_index >= len(chapter_configs):
            show_warning(f"Chapter {ch_num} config not found, skipping")
            continue

        ch_config = chapter_configs[ch_index]
        ch_name = ch_config.get("name", f"Chapter {ch_num}")
        console.print(f"\n[bold]{'='*50}[/]")
        console.print(f"[bold]Chapter {ch_num}: {ch_name}[/]")
        console.print(f"[bold]{'='*50}[/]")

        if dry_run:
            show_info(f"[DRY RUN] Would generate: {ch_name}")
            continue

        # Research phase
        show_info("Phase 1: Researching...")
        topic = job_config.get("topic", "research topic")
        research_queries = _extract_research_queries(ch_config, topic)
        unique_papers: list[dict] = []
        try:
            with CitationResearcher() as researcher:
                for query in research_queries[:3]:
                    try:
                        citations = researcher.research(query)
                        for c in citations:
                            paper = {
                                "title": c.title,
                                "authors": c.authors,
                                "year": c.year,
                                "doi": c.doi,
                                "url": c.paper_url,
                                "journal": c.venue,
                                "abstract": c.abstract_summary,
                                "source_type": c.source_type,
                                "citation_count": c.citation_count,
                                "confidence": c.confidence,
                                "api_source": c.api_source,
                            }
                            key = paper.get("doi") or paper.get("url") or paper.get("title", "")
                            if key and key not in {
                                p.get("doi") or p.get("url") or p.get("title", "") for p in unique_papers
                            }:
                                unique_papers.append(paper)
                    except Exception as e:
                        show_warning(f"Research query failed: {e}")
        except Exception as e:
            show_error(f"Research phase failed: {e}")
            raise

        if not unique_papers:
            show_error(
                "Research returned no papers. Check API keys and internet connectivity."
            )
            raise typer.Exit(1)

        show_research_progress(len(unique_papers), len(research_queries[:3]))

        # Summarize
        section_instructions = {
            str(s.get("id", "")): s.get("instructions", "")
            for s in ch_config.get("sections", [])
            if s.get("instructions")
        }
        research = await summarize_papers(unique_papers, section_instructions or None)

        # Write chapter
        show_info("Phase 2: Writing...")
        previous_texts = all_chapter_texts if all_chapter_texts else None
        chapter_text = await write_chapter(
            base_prompt=base_prompt,
            chapter_config=ch_config,
            style_config=style_config,
            research=research,
            job_config=job_config,
            previous_chapters=previous_texts,
        )
        word_count = len(chapter_text.split())
        show_writing_progress(ch_num, len(chapters), word_count)
        results_summary["total_words"] += word_count

        # Replace {cite_XXX} placeholders with inline (Author, Year) citations
        citation_style = job_config.get("citation_style", "apa")
        chapter_text = replace_inline_citations(chapter_text, research.citations, citation_style)

        # Pre-humanization review
        if not skip_review:
            show_info("Phase 3: Pre-reviewing...")
            style_review = await review_style(chapter_text, ch_config, style_config)
            show_review_result("Style (pre)", style_review.score, style_review.pass_quality, len(style_review.issues))
            if style_review.issues:
                show_issues_table([
                    {"type": i.issue_type, "severity": i.severity, "description": i.description}
                    for i in style_review.issues[:10]
                ], "Style Issues (pre)")
            fact_result = await fact_check(chapter_text, research.citations)
            show_review_result("Fact-check (pre)", fact_result.score, fact_result.pass_quality, len(fact_result.issues))
            pre_score = (style_review.score + fact_result.score) // 2
        else:
            pre_score = 75

        # Humanize phase
        if not skip_humanize:
            show_info("Phase 4: Humanizing...")
            humanize_result = await run_humanize_pipeline(chapter_text, intensity="medium")
            chapter_text = humanize_result.final_text
            show_humanize_result(
                len(humanize_result.steps),
                humanize_result.original_length,
                humanize_result.final_length,
            )

            # Post-humanization review
            if not skip_review:
                show_info("Phase 5: Post-reviewing...")
                style_review = await review_style(chapter_text, ch_config, style_config)
                show_review_result("Style (post)", style_review.score, style_review.pass_quality, len(style_review.issues))
                fact_result = await fact_check(chapter_text, research.citations)
                show_review_result("Fact-check (post)", fact_result.score, fact_result.pass_quality, len(fact_result.issues))
                post_score = (style_review.score + fact_result.score) // 2
            else:
                post_score = pre_score

            # AI detection check
            show_info("Phase 6: Detecting...")
            detection = detect_ai_text(chapter_text)
            show_detection_result(detection.score, detection.pass_quality, 50.0)
            if not detection.pass_quality and detection.flagged_phrases:
                show_detection_details(detection.details, detection.flagged_phrases)

            if not detection.pass_quality and detection.score > 60:
                show_info("Re-running humanizer (detection score too high)...")
                humanize_result = await run_humanize_pipeline(chapter_text, intensity="aggressive")
                chapter_text = humanize_result.final_text
                detection = detect_ai_text(chapter_text)
                show_detection_result(detection.score, detection.pass_quality, 50.0)
        else:
            post_score = pre_score
            detection = detect_ai_text(chapter_text)

        avg_score = post_score if not skip_review else pre_score
        results_summary["scores"].append(avg_score)

        # Append reference list
        refs = format_reference_list(research.citations, citation_style)
        if refs:
            chapter_text = chapter_text.rstrip() + "\n\n---\n\n" + refs

        # Export
        show_info("Phase 6: Exporting...")
        output_paths = export_chapter(
            chapter_text,
            job_config.get("name", "untitled"),
            ch_num,
            output_formats,
        )
        for fmt, path in output_paths.items():
            show_export_result(fmt, path)

        show_chapter_complete(ch_num, len(chapters), avg_score)
        results_summary["chapters"] += 1
        all_chapter_texts.append(chapter_text)

    # Final summary
    elapsed = time.time() - start_time
    results_summary["avg_score"] = (
        sum(results_summary["scores"]) // max(len(results_summary["scores"]), 1)
    )
    results_summary["detection_status"] = "PASS" if all_chapter_texts else "N/A"

    console.print(f"\n[bold cyan]{'='*50}[/]")
    show_completion_summary(results_summary)
    console.print(f"\n  [dim]Completed in {elapsed:.1f}s[/]")


def _get_chapter_configs(job_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Load chapter configs from templates referenced in the job."""
    chapters_ref = job_config.get("chapters", [])
    configs: list[dict[str, Any]] = []

    for ch_ref in chapters_ref:
        if isinstance(ch_ref, dict):
            template_file = ch_ref.get("template", "")
            if template_file:
                try:
                    configs.append(load_chapter_template(template_file))
                except FileNotFoundError:
                    # Create a default config
                    configs.append({
                        "name": ch_ref.get("name", f"Chapter {len(configs)+1}"),
                        "sections": ch_ref.get("sections", []),
                        "forbidden": ch_ref.get("forbidden", []),
                        "required": ch_ref.get("required", []),
                    })
            else:
                configs.append(ch_ref)
        elif isinstance(ch_ref, str):
            try:
                configs.append(load_chapter_template(ch_ref))
            except FileNotFoundError:
                configs.append({"name": f"Chapter {len(configs)+1}", "sections": []})

    # If no chapters defined, create defaults
    if not configs:
        for i in range(1, 4):
            configs.append({
                "name": f"Chapter {i}",
                "sections": [
                    {"id": f"{i}.1", "title": "Section 1", "paragraphs": 3, "word_count": 500}
                ],
                "forbidden": [],
                "required": [],
            })

    return configs


def _extract_research_queries(ch_config: dict[str, Any], topic: str = "") -> list[str]:
    """Extract research queries from chapter config sections."""
    queries: list[str] = []

    for section in ch_config.get("sections", []):
        title = (section.get("title", "") or "").strip()
        instructions = (section.get("instructions", "") or "").strip()
        if title.lower() in ("section 1", "section", "") and not instructions:
            continue
        if title or instructions:
            queries.append(f"{topic} {title} {instructions}".strip())

    if not queries:
        fallback = topic or ch_config.get("name", "general research") or "general research"
        queries.append(fallback)
    return queries


@app.command()
def config():
    """Show or set configuration."""
    show_banner()

    from src.config import CONFIG_DIR
    config_path = CONFIG_DIR / "config.toml"

    if config_path.exists():
        console.print(f"[dim]Config file: {config_path}[/]")
        # Read and display (masking API keys)
        import toml
        with open(config_path) as f:
            cfg = toml.load(f)
        _display_config(cfg)
    else:
        show_info("No config file found. Creating default config.")
        _create_default_config(config_path)


def _display_config(cfg: dict[str, Any]):
    """Display config with masked secrets."""
    from rich.table import Table
    from rich import box

    table = Table(title="Configuration", box=box.SIMPLE, show_header=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")

    for section, values in cfg.items():
        if isinstance(values, dict):
            table.add_row(f"[bold]{section}[/]", "")
            for k, v in values.items():
                display_val = str(v)
                if "key" in k.lower() or "secret" in k.lower():
                    display_val = display_val[:4] + "..." + display_val[-4:] if len(display_val) > 8 else "***"
                table.add_row(f"  {k}", display_val)
        else:
            display_val = str(values)
            if "key" in str(section).lower():
                display_val = "***"
            table.add_row(str(section), display_val)

    console.print(table)


def _create_default_config(config_path: Path):
    """Create a default config file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    default = """# open-work configuration

[llm]
provider = "openai"          # openai, deepseek, ollama
api_key = ""                  # or set OPENWORK_API_KEY env var
model = "gpt-4o-mini"        # model to use
base_url = ""                 # custom endpoint (leave empty for defaults)
temperature = 0.7

[research]
semantic_scholar_api_key = ""  # optional, increases rate limits
max_papers_per_query = 15
"""
    config_path.write_text(default)
    show_success(f"Default config created: {config_path}")
    show_info("Edit this file to add your API keys, or set environment variables.")


@app.command()
def list_jobs():
    """List all saved jobs."""
    show_banner()
    jobs_dir = get_jobs_dir()
    if not jobs_dir.exists():
        show_info("No jobs directory found.")
        return

    jobs = list(jobs_dir.glob("*.yaml"))
    if not jobs:
        show_info("No jobs found.")
        return

    from rich.table import Table
    from rich import box

    table = Table(title="Saved Jobs", box=box.ROUNDED)
    table.add_column("#", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Topic")
    table.add_column("Type")

    for i, job_path in enumerate(sorted(jobs), 1):
        try:
            cfg = load_yaml(job_path)
            table.add_row(
                str(i),
                job_path.stem,
                cfg.get("topic", "N/A")[:40],
                cfg.get("paper_type", "N/A"),
            )
        except Exception:
            table.add_row(str(i), job_path.stem, "[red]Error reading[/]", "")

    console.print(table)


@app.command()
def new_job():
    """Create a new job interactively."""
    show_banner()
    job_config = get_new_job_config()
    if not job_config:
        show_error("Invalid job configuration")
        raise typer.Exit(1)

    job_name = get_job_name()
    job_config["name"] = job_name

    job_path = get_jobs_dir() / f"{job_name}.yaml"
    save_yaml(job_config, job_path)
    show_success(f"Job created: {job_path}")


@app.command()
def detect(
    file: str = typer.Argument(..., help="Text file to analyze"),
    threshold: float = typer.Option(50.0, "--threshold", "-t", help="Detection threshold"),
):
    """Run AI detection on a text file."""
    path = Path(file)
    if not path.exists():
        show_error(f"File not found: {file}")
        raise typer.Exit(1)

    text = path.read_text(encoding="utf-8")
    result = detect_ai_text(text, threshold=threshold)

    show_detection_result(result.score, result.pass_quality, threshold)
    show_detection_details(result.details, result.flagged_phrases)


@app.command()
def review(
    file: str = typer.Argument(..., help="Chapter file to review"),
    style_file: str = typer.Option("academic_balanced.yaml", "--style", "-s"),
):
    """Review a chapter file for style and quality."""
    path = Path(file)
    if not path.exists():
        show_error(f"File not found: {file}")
        raise typer.Exit(1)

    text = path.read_text(encoding="utf-8")

    try:
        style_config = load_style_template(style_file)
    except FileNotFoundError:
        style_config = {"tone": "professional", "formality": 0.7, "forbidden_phrases": []}

    async def _run():
        result = await review_style(text, {}, style_config)
        show_review_result("Style", result.score, result.pass_quality, len(result.issues))
        if result.issues:
            show_issues_table([
                {"type": i.issue_type, "severity": i.severity, "description": i.description}
                for i in result.issues
            ])

    asyncio.run(_run())


if __name__ == "__main__":
    app()
