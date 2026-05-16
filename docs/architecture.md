# Aggregator Internal Documentation

This folder contains exhaustive documentation for the internal modules of the `osaa` OSINT engine.

## Core Modules

### `orchestrator.py`
The `Orchestrator` class is the central engine responsible for managing the OSINT investigation lifecycle. It coordinates the discovery phases:
- **`run_full_pipeline(targets)`**: Executes the investigation pipeline. It manages `BrowserConnector`, `SearchConnector`, `TookieConnector`, `HoleheConnector`, and `HolmesConnector`. It uses `MasterIdentity` as the central repository for artifacts discovered.

### `models.py`
Defines the `MasterIdentity` dataclass, which is the unified data structure for storing investigation results, including emails, usernames, full names, discovered URLs, and raw artifacts collected by the connectors.

### `identity_expander.py`
This module expands on initial identifiers to increase the discovery surface area:
- **`ArtifactClassifier`**: Uses regex to identify raw strings as emails, usernames, IPs, or URLs.
- **`IdentityExpander`**:
    - **`generate_username_permutations`**: Generates variants of a base username.
    - **`generate_name_permutations`**: Generates potential usernames and email addresses from full names.

## Utilities

### `blocklist.py`
Contains logic for filtering out "noisy" artifacts that are unlikely to be useful in an investigation.

### `logger.py`
Standardized logging interface for the entire project.

### `path_utils.py`
Helper for resolving file paths across different components.
