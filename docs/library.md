# Programmatic Library Usage

You can embed the `osaa` engine directly into other Python applications.

## Quickstart Example

The following code illustrates how to run the pipeline, invoke the local AI analyst, and compile an intelligence report. Because the pipeline relies on async I/O, it must run inside an asyncio event loop.

```python
import asyncio
from [orchestrator](../orchestrator.py) import [Orchestrator](../orchestrator.py#L27)
from [models](../models.py) import [Knowledge](../models.py#L61)
from [ai_analyst](../ai_analyst.py) import [AIAnalyst](../ai_analyst.py#L13)
from [reporters.ai_report_writer](../reporters/ai_report_writer.py) import [AIReportWriter](../reporters/ai_report_writer.py#L13)

async def run_investigation():
    # 1. Define targets using the list-of-dicts schema
    targets = [
        {"type": "username", "value": "target_user"},
        {"type": "email", "value": "target_email@example.com"}
    ]

    # 2. Define optional certified ground-truth knowledge
    knowledge = Knowledge(
        identity={
            "fullname": "John Doe",
            "phone": "+123456789",
            "address": "Lille, France"
        }
    )

    # 3. Instantiate the orchestrator
    orchestrator = Orchestrator(
        proxies=["127.0.0.1:8080"], # Optional list of proxy addresses
        knowledge=knowledge,
        ratio=0.33                  # Sampling ratio
    )

    # 4. Execute the pipeline (async)
    print("[*] Running discovery connectors and browser crawls...")
    await orchestrator.run_full_pipeline(targets)

    # 5. Initialize the AI Analyst and generate the report
    # Reuse a local running server for faster processing (e.g. LM Studio server)
    analyst = AIAnalyst(agent_type="lms-server", model_name="google/gemma-3n-e4b")
    writer = AIReportWriter(analyst)

    print("[*] Performing AI analysis and generating report...")
    report_markdown = await writer.generate_report(
        target="target_user",
        identity=orchestrator.identity,
        knowledge=knowledge
    )

    print(report_markdown)

if __name__ == "__main__":
    asyncio.run(run_investigation())
```

---

## Extending the Engine

### Adding a Custom Connector

To integrate a new lookup tool:
1. Create a Python file inside [connectors/](../connectors).
2. Inherit from [BaseConnector](../connectors/base.py#L28) (defined in [connectors/base.py](../connectors/base.py)).
3. Override the [supported_types](../connectors/base.py#L34) property to list target types (e.g., `["email", "username"]`).
4. Implement [run](../connectors/base.py#L38) as an async method, returning a list of [DiscoveryResult](../connectors/base.py#L7) instances.

```python
from typing import List
from connectors.base import BaseConnector, DiscoveryResult

class CustomDatabaseConnector(BaseConnector):
    @property
    def supported_types(self) -> List[str]:
        return ["username"]

    async def run(self, target: str, proxies: List[str] = None, **kwargs) -> List[DiscoveryResult]:
        # Implement custom query logic here
        results = []
        # results.append(DiscoveryResult(source_tool="custom_tool", target_type="url", value="https://example.com/profile"))
        return results
```

5. Register your new connector in [orchestrator.py](../orchestrator.py) by adding it to the [self.connectors](../orchestrator.py#L29) dictionary in [__init__](../orchestrator.py#L28).
