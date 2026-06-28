# open-work

Automated chapter-by-chapter research paper writing system with a web UI. Uses multi-source academic research, LLM-powered writing, humanization, and AI detection — all orchestrated through an interactive dashboard.

## Features

- **Multi-source research** — Semantic Scholar, OpenAlex, Crossref, arXiv with proxy rotation and caching
- **Chapter-by-chapter generation** — Per-chapter YAML configs with section structure, word counts, and format types
- **Humanization pipeline** — LLM entropy rewrite + polish pass to bypass AI detection
- **AI detection** — Statistical heuristics (sentence uniformity, TTR, transition density)
- **Web UI** — Dashboard, job management, TipTap read-only editor, export to MD/DOCX/PDF
- **Proxy management** — 19+ free proxy sources with validation and health tracking
- **CLI** — Full-featured interactive CLI as an alternative to the web UI

## Architecture

```
open-work/
├── src/                    # Python pipeline engine
│   ├── cli/                # Typer + Rich + InquirerPy CLI
│   ├── research/           # Multi-source orchestrator (S2, OpenAlex, Crossref, arXiv)
│   ├── writers/            # Chapter writer + citation compiler
│   ├── reviewers/          # Style checker, fact checker, AI detector
│   ├── humanizer/          # Anti-detection rewrite pipeline
│   ├── proxy/              # Proxy fetcher, validator, manager
│   ├── export/             # MD/DOCX/PDF export (Pandoc)
│   └── utils/              # LLM client, text analysis
├── api/                    # FastAPI REST API
│   ├── routes/             # Jobs, chapters, generation, export, config, proxy
│   ├── services/           # Business logic layer
│   ├── models.py           # SQLAlchemy ORM models
│   └── schemas.py          # Pydantic request/response schemas
├── web/                    # Next.js 15 frontend
│   └── src/
│       ├── app/            # Pages: dashboard, jobs, editor, config
│       ├── components/     # Sidebar, header, layout
│       ├── lib/            # API client, TypeScript types
│       ├── stores/         # Zustand state management
│       └── hooks/          # Polling hook
├── prompts/                # YAML/Markdown prompt templates
│   ├── base/               # Writer, researcher, reviewer prompts
│   ├── chapters/           # Per-chapter configs (sections, word counts)
│   ├── styles/             # Tone, formality, forbidden phrases
│   └── humanizer/          # Entropy rewrite + polish prompts
├── jobs/                   # Job definitions (YAML)
├── output/                 # Generated chapters + references
├── tests/                  # 137 passing tests
├── docker-compose.yml      # Docker deployment
└── pyproject.toml          # Python package config
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key (or compatible provider)
- Optional: Pandoc (for DOCX/PDF export)

### Install Python dependencies

```bash
pip install -e ".[dev]"
```

### Install frontend dependencies

```bash
cd web && npm install
```

### Configure API keys

```bash
mkdir -p ~/.config/open-work
cat > ~/.config/open-work/config.toml << 'EOF'
[llm]
provider = "openai"
api_key = "sk-your-key-here"
model = "gpt-4o-mini"

[research]
openalex_api_key = "your-key"
EOF
```

### Run the web UI

```bash
# Terminal 1: API server
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd web && npm run dev
```

Open http://localhost:3000

### Run the CLI

```bash
open-work generate --interactive
```

## Docker

```bash
docker-compose up --build
```

Frontend: http://localhost:3000 | API: http://localhost:8000

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | List all jobs |
| POST | `/api/jobs` | Create a new job |
| GET | `/api/jobs/{id}` | Get job detail + chapters |
| GET | `/api/jobs/{id}/chapters/{num}` | Get chapter content |
| POST | `/api/jobs/{id}/generate` | Start generation |
| GET | `/api/jobs/{id}/generate/status` | Poll generation status |
| GET | `/api/jobs/{id}/chapters/{num}/export?format=md` | Download chapter |
| GET | `/api/config` | Get app configuration |
| GET | `/api/proxy/pool` | Proxy pool status |

## CLI Commands

```bash
open-work generate --job my_job --all          # Generate all chapters
open-work generate --job my_job --chapter 1    # Generate single chapter
open-work list-jobs                            # List saved jobs
open-work new-job                              # Create job interactively
open-work detect paper.txt                     # Run AI detection
open-work review chapter_1.md                  # Review for style
```

## Configuration

### Job YAML format

```yaml
name: my_research
topic: "Impact of AI on Healthcare"
paper_type: literature_review
citation_style: apa
target_audience: graduate_students
research_queries:
  - "artificial intelligence diagnostic accuracy"
chapters:
  - template: chapters/chapter_1.yaml
    name: Introduction
```

### Chapter YAML format

```yaml
name: Introduction
sections:
  - id: "1.1"
    title: "Introduction"
    paragraphs: 5
    word_count: 800
    format: prose
    instructions: "Define the research problem and state the purpose"
forbidden:
  - "furthermore"
  - "in conclusion"
required:
  - "Include the research gap"
```

### Config file

Located at `~/.config/open-work/config.toml`:

```toml
[llm]
provider = "openai"       # openai, deepseek, ollama
api_key = "sk-..."
model = "gpt-4o-mini"
temperature = 0.7

[research]
semantic_scholar_api_key = ""
openalex_api_key = ""
max_papers_per_query = 15
```

## Testing

```bash
pytest tests/ -v
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Pipeline | Python 3.12, httpx, PyYAML, OpenAI API |
| API | FastAPI, SQLAlchemy, SQLite |
| Frontend | Next.js 15, React 19, TypeScript |
| Editor | TipTap (headless ProseMirror) |
| Styling | Tailwind CSS |
| State | Zustand |
| Export | Pandoc (MD/DOCX/PDF) |
| Deployment | Docker Compose |

## License

MIT
