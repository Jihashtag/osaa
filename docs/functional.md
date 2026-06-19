# Functional Documentation: CLI & Pipeline Workflow

This document explains how to configure, execute, and analyze the results of the `osaa` OSINT tool.

## Installation & Setup

All required modules, tools (Holehe, Holmes, Tookie), Tor dependencies, and virtual environment pip packages are installed using the unified setup script:
```bash
./[setup_all.sh](../setup_all.sh)
```

Ensure the Tor service daemon is running locally on your system to enable the [TorConnector](../connectors/tor.py#L28) or proxy-routed operations:
```bash
sudo systemctl start tor
```

---

## CLI Usage

The tool is executed using [main.py](../main.py):

```bash
python3 [main.py](../main.py) --username target_handle --name "Jane Doe" --ai-agent lms-server
```

### Command Line Arguments

- `--username`: Primary username of the target.
- `--name`: Primary full name of the target.
- `--email`: Primary email address of the target.
- `--ratio`: Proportion of targets and discovered URLs to process (defaults to `0.33`).
- `--debug`: Enable verbose logging output.
- `--ai-agent`: Choose the AI backend for report synthesis (`lms`, `ollama`, `gemini`, `ollama-http`, `lms-server`). The `*-http` or `*-server` options are persistent HTTP connection options and run significantly faster.
- `--model`: Specific LLM model to query. Defaults to `google/gemma-3n-e4b` for LMS and `llama3.2:1b` for Ollama.
- `--ai-endpoint`: Endpoint URL overrides for persistent LLM servers.
- `--proxy_list`: Path to a file containing newline-separated SOCKS5 or HTTP proxies formatted as `ip:port`.
- `--dry-run`: Parses inputs and prints the target execution plan without making any network calls.
- `--knowledge-file`: Path to a structured JSON file containing certified target details.
- `--knowledge`: Raw text metadata describing context about the target.

---

## Pipeline Execution Workflow

The orchestrator executes the investigation through the following steps:

1. **Ingestion & Instantiation**: The target values are loaded. Basic known information is stored as ground-truth [Knowledge](../models.py#L61).
2. **Identity Expansion**: [IdentityExpander](../identity_expander.py#L61) runs permutations on the target names and usernames to create additional target aliases.
3. **Execution Plan**: If `--dry-run` is active, it outputs which connectors are mapped to run against each target value and terminates.
4. **Proxy Check**: Working proxies are verified, caching active results with a 5-minute TTL to reduce connection overhead.
5. **Phase 1 Connectors**: Runs Holehe, Tookie, Holmes, Breach, and Searcher in parallel. Output links are mapped to standard fields in [MasterIdentity](../models.py#L41).
6. **Phase 2 Chrome Crawl**:
   - Gathers urls discovered in Phase 1.
   - Filters out known Search Engine Result Pages (SERPs) and enforces domain caps.
   - Batches URL requests to reuse Chrome instances, capturing raw body text, profile images, and screenshots.
7. **Phase 2.5 Speculative Checks**: If a username has no associated email, candidates (e.g. `<username>@gmail.com`) are derived and checked using Holehe/Breach.
8. **Phase 3 Targeted Crawl**: Crawls major search engines to look for newly found usernames.
9. **Report Compilation**:
   - [AIReportWriter](../reporters/ai_report_writer.py#L13) filters results and batches raw page text into LLM prompts.
   - Corroborates certified ground truth facts against collected documents.
   - Cleans the evidence log, removing duplicate SERPs and listing source reliability weights.
   - Generates the final Markdown report file inside the target's output directory.
