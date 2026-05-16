# Library Usage Documentation

The `osaa` engine can be embedded directly into other Python applications.

## Quickstart

```python
from orchestrator import Orchestrator
from models import MasterIdentity

# Initialize the orchestrator
orch = Orchestrator()

# Define investigation targets
targets = {
    "email": "target@example.com",
    "username": "target_user"
}

# Run the full pipeline
# This triggers the expansion, discovery, and fusion phases
report = orch.run_full_pipeline(targets)

# Access the report
print(f"Summary: {report.get('summary')}")
```

## Extending the Engine

### Adding a Custom Connector
1. Create a new file in `connectors/`.
2. Inherit from `BaseConnector`.
3. Implement `run(target: str)`.
4. Return a list of `DiscoveryResult` instances.

### Custom Reporters
Custom reporters can be added by implementing a similar interface to `reporters/ai_report_writer.py`.
