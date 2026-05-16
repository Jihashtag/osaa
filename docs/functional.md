# Functional Documentation: Tool Usage

The `osaa` tool provides a modular OSINT pipeline for local identity resolution.

## Getting Started

Ensure all sub-projects are cloned and dependencies are installed using `setup.sh`.

## CLI Usage

The tool is primarily executed via `main.py`.

```bash
python3 main.py --email target@example.com --username target_user
```

### Options
- `--email`: Specify the primary email address of the target.
- `--username`: Specify the primary username of the target.
- `--fullname`: (Optional) Specify the full name for identity expansion.
- `--proxy_list`: (Optional) Path to a file containing a list of proxies (format: `ip:port`).
- `--debug`: Enable verbose debug logging.

## Pipeline Workflow

1. **Ingestion**: Input artifacts (email, username) are ingested into the `MasterIdentity` model.
2. **Expansion**: `IdentityExpander` generates permutations of the input identifiers.
3. **Discovery**: Registered `Connectors` (Holehe, Holmes, Tookie, BrowserConnector, etc.) are executed by the `Orchestrator`.
4. **Processing**: Discovered artifacts are normalized and stored in `MasterIdentity`.
5. **Report**: The `AIAnalyst` (LLM) generates a final investigation report based on collected artifacts.
