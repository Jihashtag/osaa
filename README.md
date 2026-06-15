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
- **`AIAnalyst`**: Provides local AI inference by auto-detecting `gemini` CLI, `LM Studio`, or `Ollama`.
- **`MasterIdentity`**: The unified data structure representing the investigated subject.

## Installation & Setup

1. **Environment Setup**:
   ```bash
   # From project root
   ./setup_all.sh
   ```

2. **Local AI Model**:
   - **Option A (Preferred)**: Ensure `gemini` CLI is installed and configured.
   - **Option B (Fallback)**: Ensure Ollama is running (`ollama serve`) and pull the model: `ollama pull llama3.2:1b`.

## Usage

```python
from orchestrator import Orchestrator

# Example usage
orch = Orchestrator()
targets = [{"type": "email", "value": "target@example.com"}, {"type": "username", "value": "target_user"}]
await orch.run_full_pipeline(targets)
```

### CLI Execution
```bash
python3 main.py --username target_user
```
Other flags: `--name`, `--email`, `--ratio`, `--proxy_list`, `--knowledge-file`,
`--ai-agent {lms,ollama,gemini}`, `--model`, `--debug`, `--dry-run`.

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
