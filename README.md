# Osint Scraper AI Assisted (osaa)

The `osaa` tool is a recursive, modular OSINT fusion engine designed for local identity resolution. It triggers multiple OSINT tools in parallel, aggregates discovered artifacts, and leverages local LLMs to identify identities and generate investigation leads.

## Architecture

- **`Orchestrator`**: Central controller (`osaa/orchestrator.py`). Manages input ingestion, connector dispatch, identity fusion, and the recursive discovery loop.
- **`Connectors`**: Normalized interfaces (`osaa/connectors/base.py`) for heterogeneous OSINT tools.
    - **`HoleheConnector`**: Wraps the Holehe email OSINT tool, parsing structured JSON output.
    - **`HolmesConnector`**: Interfaces with the `python_holmes` framework via library imports.
    - **`TookieConnector`**: Executes the Tookie-OSINT CLI and handles output redirection.
    - **`TorConnector` & `BrowserConnector`**: Support for deep web scraping and headless browser automation.
- **`FusionEngine`**: Probabilistic Identity Fusion Engine (`osaa/fusion_engine.py`). Implements similarity-based linking using `rapidfuzz` and source reliability weighting.
- **`KnowledgeSystem`**: Certified Truth base (`osaa/knowledge_loader.py`). Anchors LLM analysis to verified target data to prevent hallucinations.
- **`BreachConnector`**: Checks Have I Been Pwned for known breaches on an email (`osaa/connectors/breach.py`). Requires `--breach-api-key` / `HIBP_API_KEY`; skips cleanly without one.
- **`ReviewEngine`**: Data-quality audit (`osaa/reporters/review_engine.py`). Flags unmerged distinct anchors and low-confidence findings in the "Data Quality Audit" report section.
- **`AIAnalyst`**: Provides local AI inference by auto-detecting `gemini` CLI, `LM Studio`, or `Ollama`.
- **`MasterIdentity`**: The unified data structure representing the investigated subject.

## Installation & Setup

1. **Environment Setup**:
   ```bash
   # From project root
   ./setup_all.sh
   ```

2. **Local AI Model**: pick a backend with `--ai-agent`.
   - **CLI backends** (spawn a process per call): `lms`, `ollama`, `gemini`.
   - **Persistent HTTP backends** (reuse a running server — *recommended*, far
     faster as a report makes several calls): `ollama-http` (Ollama HTTP API,
     default `http://localhost:11434`) and `lms-server` (LM Studio
     OpenAI-compatible server, default `http://localhost:1234`). Override the
     URL with `--ai-endpoint`.
   - **Model quality**: a 1B model is too weak for analysis. Defaults are now
     the ~4B Gemma 3n E4B model on both backends (`google/gemma-3n-e4b` for LM
     Studio, `gemma3n:e4b` for Ollama). Override with `--model`; use a smaller
     one if you need speed over depth.
   - Run `python3 main.py doctor` before a real investigation — it checks the
     configured AI backend, Tor, and tool paths are actually reachable, so a
     misconfiguration surfaces immediately instead of an hour into a run.

## Usage

```python
from orchestrator import Orchestrator

# Example usage
orch = Orchestrator()
targets = [{"type": "email", "value": "target@example.com"}, {"type": "username", "value": "target_user"}]
await orch.run_full_pipeline(targets)
```

### CLI Execution
The CLI is split into three subcommands: `run` (execute the pipeline and write
a report), `plan` (print the execution plan with no network I/O — replaces the
old `--dry-run` flag), and `doctor` (pre-flight check of backends/tool paths).
At least one of `--username`/`--name`/`--email` is required for `run`/`plan`.

```bash
python3 main.py doctor

python3 main.py plan --username target_user

# Free-text knowledge + a fast persistent backend:
python3 main.py run --username target_user --name "Jane Doe" \
  --knowledge "French medical student in Lille, ~20s" \
  --ai-agent ollama-http
```

Common flags: `--name`, `--email`, `--ratio` (must be within `(0, 1]`),
`--proxy-list`, `--knowledge-file` / `--knowledge "<text>"`,
`--tookie-dir` / `--holmes-dir` (or `TOOKIE_DIR` / `HOLMES_DIR` env vars),
`--breach-api-key` (or `HIBP_API_KEY` env var — without one, breach checks
are skipped rather than run),
`--max-results <n>` (results fetched per search query, default `10`),
`--max-pages <n>` (pages crawled per domain by the browser, and onion search
engines tried per target by Tor, default `5`), `--debug`.
`run`/`doctor`-only: `--ai-agent {lms,ollama,gemini,ollama-http,lms-server}`,
`--model`, `--ai-endpoint`.
`run`-only: `--output <dir>` (where to write the report + artifacts) and
`--force` (overwrite an existing report at that location).

## Testing

The project runs its tests with **pytest** (`pytest-asyncio` for the async
suite). Tests live both at the top level (`test_*.py`) and under `tests/`. A
`conftest.py` puts the package directory on `sys.path`, and `pytest.ini`
configures discovery and markers, so a bare invocation works from the project
directory:

### Running Tests
```bash
# Full offline suite (live-network tests are deselected by default):
python3 -m pytest

# Include the tests that hit the live internet (DuckDuckGo, proxies, Tor):
python3 -m pytest -m network
```
Tests that require network access are tagged with `@pytest.mark.network` and are
skipped by default to keep the suite fast and deterministic (this is also what
CI runs).

### Adding New Tools
To add a new tool, inherit from `BaseConnector` in `osaa/connectors/` and implement the `run` method to return a list of `DiscoveryResult` objects.

## Local-Only Enforcement
This tool is strictly local-only. No external cloud APIs are used. It defaults to detected local LLM runners (Gemini CLI or Ollama).

## Disclaimer
This project is intended **only for educational purposes**. Users are responsible for ensuring their usage of this tool complies with all applicable laws, terms of service, and ethical guidelines.
