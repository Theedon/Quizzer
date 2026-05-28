# Quizzer: Async Map-Reduce AI Agent ⚡

An entirely asynchronous, Map-Reduce LangGraph architecture that ingests heavy textbooks and parallelizes LLM quiz generation without context loss.

## Try it live

> **Hosted on Railway:** [quizzer-production-e21f.up.railway.app](https://quizzer-production-e21f.up.railway.app)
>
> Select your LLM provider, enter your own API key, upload a PDF, and generate quiz questions — no local setup needed.

### Graph Architecture

![Architecture Diagram](docs/architecture.png)

## Why I Built This

**The Product Problem:** In Nigeria, secondary school teachers and EdTech platforms (like the one I co-founded at [JAMB Prep](https://jambprepacademy.com)) spend countless hours manually reading through massive, 300+ page textbooks just to extract and format exam questions. I needed a way to completely automate this process and export it directly into a format ready for a Learning Management System (LMS).

**The Engineering Problem:** Standard LLM chunking strategies throw away context boundaries. A chunk that ends mid-paragraph gives the model an incomplete picture, resulting in lower-quality questions and hallucinated answers. On top of that, running generation sequentially (chunk 1 → chunk 2 → …) on a heavy textbook takes hours.

**The Solution:** I built an architecture that solves both bottlenecks at once:

- **Context-aware processing:** Text formatting and layout elements like page-number metadata are preserved so the LLM always knows where it is in the source material.
- **Parallel generation with quality gates:** A Map-Reduce subgraph fans out quiz generation across every chunk simultaneously. Each branch has its own LLM Reviewer that scores and retries outputs up to 3 times before merging.

The result is a pipeline that processes a massive textbook in roughly the same wall-clock time it takes to process a single chunk, exporting perfectly structured CSVs ready for database ingestion.

## Performance Benchmark:

Using Gemini 2.5 Flash Lite and max_concurrency=5, the Map-Reduce pipeline successfully ingested a 119-page PDF, fanned out the generation/review nodes, and aggregated 2,589 validated quiz questions in 31 seconds. (A ~15x speedup over sequential processing).

## Architecture

**Pipeline at a glance:**

| Stage                      | Node Name                          | What happens                                                                                                              |
| -------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Ingest**                 | `page_ingestor`                    | Extracts text page-by-page from a PDF file.                                                                               |
| **Chunk**                  | `chunking`                         | Breaks pages into overlapping chunks, preserving page metadata.                                                           |
| **Map (fan-out)**          | `subgraph_generator`               | Each chunk is dispatched to its own generator/reviewer subgraph in parallel via LangGraph's Send API.                     |
| **Generate & Review loop** | `quiz_generator` & `quiz_reviewer` | A generator LLM drafts a quiz, and a reviewer LLM scores it for relevance. If it fails, the generator retries (up to 3×). |
| **Reduce**                 | `aggregator`                       | Merges every approved quiz set back into a single main state.                                                             |
| **Export**                 | `utils.export`                     | Automatically structures the final dataset and exports it as an LMS-ready CSV file.                                       |

## Tech Stack

| Layer             | Technology                                 |
| ----------------- | ------------------------------------------ |
| **Orchestration** | LangGraph (async state graphs + subgraphs) |
| **Validation**    | Pydantic                                   |
| **Logging**       | Loguru                                     |
| **GUI**           | NiceGUI (async, Quasar-based)              |
| **Package Mgmt**  | uv                                         |

## Quickstart

### 1. Clone & install

```bash
git clone https://github.com/Theedon/Quizzer.git
cd Quizzer

uv sync

```

### 2. Configure

```bash
cp .env.example .env
```

### 3. Run the CLI Pipeline

```bash
# Basic run (will output to an auto-timestamped CSV in the outputs/ directory)
uv run -m src.main --input docs/sample_textbook.pdf

# Run with custom output path
uv run -m src.main --input docs/sample_textbook.pdf --output my_custom_quizzes.csv

# Run directly with uvx without cloning repo
OPENAI_API_KEY=sk-*** uvx https://github.com/Theedon/Quizzer.git --input docs/sample_textbook.pdf --output my_custom_quizzes.csv

```

### 4. Or run the GUI

A small, async NiceGUI frontend that exposes the same pipeline: drop a PDF, watch live progress, edit the generated questions inline, and download the CSV. Dark mode is on by default with a one-click toggle, and the LLM provider/model can be switched from the sidebar.

```bash
uv run -m src.ui.app
# then open http://localhost:8080
```

> **Or skip the local setup** — try the hosted version at [quizzer-production-e21f.up.railway.app](https://quizzer-production-e21f.up.railway.app)

![Quizzer GUI](docs/ui_dark.png)

## Project Structure

```text
src/
├── main.py                  # Async CLI entry point
├── utils/
│   └── export.py            # CSV generation & data formatting
├── core/
│   ├── settings.py          # Pydantic-based config (reads .env)
│   └── logger.py            # Loguru setup
├── ui/
│   ├── app.py               # NiceGUI page (theme, sidebar, upload, cards, download)
│   └── runner.py            # Bridges graph_ainvoke updates → live UI progress
└── agent/
    ├── graph.py             # Main graph + Map-Reduce subgraph
    ├── state.py             # TypedDict state definitions
    ├── schemas.py           # Pydantic models for structured LLM output
    ├── prompts.py           # Generation & review prompt templates
    ├── llm.py               # Multi-provider LLM factory
    └── utils/
        ├── ingest_pdf.py         # PDF → page-level text extraction
        └── chunk_pdf_content.py  # Page text → overlapping chunks
```

## Running Tests

```bash
uv run pytest
```

## License

MIT
