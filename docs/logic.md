# Logic Documentation

The osaaator follows a modular, extensible design pattern.

## Core Logic Flow

1. **Orchestrator (`orchestrator.py`)**: 
   The central loop. It manages the investigation lifecycle. It coordinates the different `Connectors` to run against investigation targets, osaaates results into a `MasterIdentity` object, and manages the browser-based discovery phase.

2. **Connectors (`connectors/*.py`)**: 
   All connectors inherit from `BaseConnector`. They execute the discovery tools (CLI wrappers or direct API calls) and normalize output into a list of `DiscoveryResult` objects.

3. **Identity Expansion (`identity_expander.py`)**:
   Contains pure functions to generate username and email variants. This is purely heuristic-based and does not involve network calls.

4. **Reporter (`reporters/ai_report_writer.py`)**:
   Responsible for processing collected artifacts and leveraging the `AIAnalyst` (LLM) to generate final reports.

