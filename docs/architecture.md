# Osaa Architecture Documentation

This document describes the internal modules and architectural components of the `osaa` OSINT fusion engine.

## Core Modules & Controller

### [orchestrator.py](../orchestrator.py)
The [Orchestrator](../orchestrator.py#L27) class is the central engine managing the recursive investigation loop:
- **[run_full_pipeline](../orchestrator.py#L214)**: Dispatches all configured connectors, processes raw artifacts, filters and deduplicates URLs, runs Chrome-based web crawls, and executes speculative email validation checks.
- **[plan](../orchestrator.py#L92)**: Generates the list of target-connector associations for dry runs without executing network I/O.
- **[_run_speculative_account_checks](../orchestrator.py#L145)**: Validates hypothetical accounts when no email is known.

### [models.py](../models.py)
Defines the data entities representing investigation states:
- [MasterIdentity](../models.py#L41): Unified record storing confirmed/unconfirmed usernames, emails, full names, discovered URLs, and raw artifacts.
- [IdentityAnchor](../models.py#L30): Represents a core identity piece with confidence values.
- [IdentityCluster](../models.py#L14): Grouping of related identity nodes.
- [Knowledge](../models.py#L61): Type-safe certified ground truth base used to ground analysis.

### [identity_expander.py](../identity_expander.py)
Provides heuristic-based expansion functions:
- [ArtifactClassifier](../identity_expander.py#L29): Uses regular expressions to classify raw strings.
- [IdentityExpander](../identity_expander.py#L61): Derives username variants ([generate_username_permutations](../identity_expander.py#L92)), fullname email patterns ([generate_name_permutations](../identity_expander.py#L140)), and potential provider domains ([derive_candidate_emails](../identity_expander.py#L77)).

### [fusion_engine.py](../fusion_engine.py)
Implements the [FusionEngine](../fusion_engine.py#L12) (Probabilistic Identity Fusion Engine):
- Calculates linking probability combining fuzzy similarity scores, source trust values loaded from [reliability.yaml](../config/reliability.yaml), and high-signal domain bonuses (e.g. ProtonMail).

---

## Connectors

Connectors reside in [connectors/](../connectors) and inherit from [BaseConnector](../connectors/base.py). They query APIs, wrap CLIs, or automate web views.

1. **[HoleheConnector](../connectors/holehe.py#L11)**: Runs the Holehe tool to verify registered accounts from emails.
2. **[HolmesConnector](../connectors/holmes.py#L42)**: Interfaces with Python-Holmes to discover username registrations and email usages.
3. **[TookieConnector](../connectors/tookie.py#L12)**: Triggers the Tookie-OSINT CLI to check username existence.
4. **[SearchConnector](../connectors/searcher.py#L14)**: Queries DuckDuckGo Search asynchronously using dorks, distributing dork queries across configured proxies.
5. **[BrowserConnector](../connectors/browser.py#L65)**: Coordinates Chrome automation using undetected-chromedriver, selenium-stealth, and HTML content rules to extract text/media elements.
6. **[TorConnector](../connectors/tor.py#L28)**: Drives Tor-routed searches, dynamically listing onion search engines and executing global queries (DuckDuckGo, Yandex) anonymously.
7. **[BreachConnector](../connectors/breach.py#L11)**: Performs lookup of SHA256 hashed identifiers against breach databases.

---

## Reporting & Analysis Modules

Located under [reporters/](../reporters):

- **[AIReportWriter](../reporters/ai_report_writer.py#L13)**: Organizes final intelligence reports. Sanitizes and groups artifacts in batches to limit LLM calls, building evidence matrices and corroboration sections.
- **[ai_analyst.py](../ai_analyst.py)**: Provides the [AIAnalyst](../ai_analyst.py#L13) backend. Integrates local backends (Ollama CLI/HTTP, LM Studio CLI/HTTP) and Gemini APIs.
- **[corroboration.py](../reporters/corroboration.py)**: Matches collected textual evidence against target certified facts using token comparison and fuzzy ratios.
- **[graph.py](../reporters/graph.py)**: Generates structured graph topologies using networkx, applying centrality metrics and Louvain community grouping.
- **[review_engine.py](../reporters/review_engine.py)**: Validates findings, flagging inconsistencies and auditing result attributes.

---

## Utilities

- **[blocklist.py](../blocklist.py)**: Filters system paths, local assets, and framework strings from active evidence.
- **[url_filter.py](../utils/url_filter.py)**: Heuristics to identify search engine pages, captcha walls, and domain crawl caps.
- **[result_validation.py](../utils/result_validation.py)**: Screens empty query-echoing search pages.
