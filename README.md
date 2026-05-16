# Osint Scraper AI Assisted (osaa)

The `osaa` tool is a recursive, modular OSINT fusion engine designed for local identity resolution. It triggers multiple OSINT tools in parallel, aggregates discovered artifacts, and leverages local LLMs to identify identities and generate investigation leads.

## Architecture

- **`Orchestrator`**: Central controller (`osaa/orchestrator.py`). Manages input ingestion, connector dispatch, identity fusion, and the recursive discovery loop.
- **`Connectors`**: Normalized interfaces (`osaa/connectors/base.py`) for heterogeneous OSINT tools.
    - **`HoleheConnector`**: Wraps the Holehe email OSINT tool, parsing structured JSON output.
    - **`HolmesConnector`**: Interfaces with the `python_holmes` framework via library imports.
    - **`TookieConnector`**: Executes the Tookie-OSINT CLI and handles output redirection.
- **`FusionEngine`**: Analyzes raw discovery data and maps tool-specific outputs to the `MasterIdentity` model.
- **`LLMAnalyst`**: Provides local AI inference by auto-detecting `gemini` CLI or falling back to `Ollama`.
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
python3 -m osaa.main --user target_user
```

## Testing

The project uses `unittest`. Tests are located in the `osaa/` directory.

### Running Tests
Execute the following to run the full test suite:
```bash
PYTHONPATH=. python3 -m unittest discover osaa/ -p 'test_*.py'
```

### Adding New Tools
To add a new tool, inherit from `BaseConnector` in `osaa/connectors/` and implement the `run` method to return a list of `DiscoveryResult` objects.

## Local-Only Enforcement
This tool is strictly local-only. No external cloud APIs are used. It defaults to detected local LLM runners (Gemini CLI or Ollama).

## Disclaimer
This project is intended **only for educational purposes**. Users are responsible for ensuring their usage of this tool complies with all applicable laws, terms of service, and ethical guidelines.
