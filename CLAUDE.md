# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Architecture Analyzer — an LLM-powered platform for automated architecture discovery and analysis of distributed systems. It collects application metadata via MCP (Model Context Protocol), analyzes architecture using LLM, and generates structured reports.

**Language**: Python 3.8+ | **Framework**: FastAPI | **Status**: Early development (MCP collector uses mock data)

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
# Or editable install
pip install -e .

# Run the API server (port 8000, requires .env with ARCHI_MCP__ENDPOINT set)
python -m src.main
# Alternative
python start.py

# Tests
pytest                                    # all tests
pytest tests/test_pipeline.py             # single file
pytest tests/test_pipeline.py::TestPipelineOrchestrator::test_analyze_architecture_success  # single test
pytest --cov=src --cov-report=html        # with coverage

# Linting / formatting
black src/                                # format
isort src/                                # sort imports
mypy src/                                 # type check (strict mode configured)
```

## Architecture

### Pipeline Flow (4 stages)

The core processing follows a sequential pipeline orchestrated by `PipelineOrchestrator` (`src/core/pipeline.py`):

```
POST /api/analyze → TaskStore.create_task() → asyncio.Task(background)
  1. COLLECTING    — MCPCollector batch-fetches app metadata (semaphore concurrency)
  2. PROCESSING    — DataTransformer (clean/normalize/dedup/enrich) → DataValidator (structural + circular dep detection) → filter valid
  3. ANALYZING     — LLMAnalyzer sends structured prompt to OpenAI/Anthropic, parses JSON → ArchitectureAnalysis
  4. GENERATING    — ReportGenerator outputs Markdown/JSON/HTML (Jinja2 templates with builtin fallback)
  → TaskStore.complete_task() stores result
```

Each stage saves a checkpoint (`CheckpointManager`) and updates progress via `TaskStore`. The API polls task status/result from TaskStore.

### Key Layers

- **`src/api/`** — FastAPI routes and Pydantic request/response models. Orchestrator is lazily initialized (to avoid import-time config validation). Routes delegate to `TaskStore` for status/results.
- **`src/core/`** — `PipelineOrchestrator` (pipeline orchestration with progress callback), `LLMAnalyzer` (OpenAI/Anthropic), `ReportGenerator` (multi-format), `TaskStore` (task lifecycle + result persistence), `CheckpointManager` (stage-level file-based checkpoints for recovery)
- **`src/collectors/`** — `BaseDataCollector` ABC; `MCPCollector` (currently mock via `_mock_mcp_call`, real MCP integration is TODO)
- **`src/processors/`** — `DataTransformer` (cleaning, normalization, dedup, cross-reference enrichment, aggregation), `DataValidator` (structural + semantic validation with severity levels, circular dependency DFS detection), `ErrorHandler` (circuit breaker, retry decorators, resource limiter)
- **`src/config/`** — Layered pydantic-settings config; single `settings` singleton

### Task Lifecycle

```
POST /api/analyze → create TaskRecord(INITIALIZED) → launch asyncio.Task
GET  /api/tasks/{id}/status → read TaskRecord from TaskStore
GET  /api/tasks/{id}/result → read PipelineResult from TaskRecord (404 if not yet complete)
GET  /api/reports/{id}      → FileResponse from report_path in PipelineResult
DELETE /api/tasks/{id}      → cancel running task
```

### Configuration System

All config uses `ARCHI_` env prefix with `__` as nested delimiter (via pydantic-settings):
- `ARCHI_LLM__PROVIDER` → `settings.llm.provider` (openai | anthropic | azure | local)
- `ARCHI_MCP__ENDPOINT` → `settings.mcp.endpoint`
- `ARCHI_PROCESSING__BATCH_SIZE` → `settings.processing.batch_size`

Copy `env.example` to `.env` for local development. The `Settings` class in `src/config/settings.py` is instantiated as a module-level singleton.

### Extension Points

- **New collector**: Subclass `BaseDataCollector` (in `src/collectors/base.py`), implement `collect_app_info`, `collect_batch_info`, `health_check`
- **New LLM provider**: Add branch in `LLMAnalyzer._create_llm_client()` and `_call_llm()`
- **New report format**: Add to `ReportFormat` and implement `_generate_<format>_report()` in `ReportGenerator`

## Conventions

- All code comments, docstrings, log messages, and error messages are in **Chinese (中文)**
- Data models use **Pydantic v2** (`BaseModel` with `Field`, `field_validator`, `model_dump()`)
- Async throughout: routes are `async def`, collectors use `httpx.AsyncClient`, pipeline uses `asyncio.gather`
- Logging via **loguru** (configured in `settings.setup_logging()`)
- HTTP retries use **tenacity** (`@retry` decorator with exponential backoff)
- Tests use **pytest-asyncio** with `@pytest.mark.asyncio` for async tests; mocking via `unittest.mock`
- Test env vars are set in `tests/conftest.py` (avoids needing a `.env` for testing)
- Black line length: 88, isort profile: "black", mypy: strict mode
