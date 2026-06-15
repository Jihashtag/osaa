# Logic Documentation

The Orchestrator follows a modular, extensible design pattern.

## Core Logic Flow

1. **Orchestrator (`orchestrator.py`)**: 
   The central loop. It manages the investigation lifecycle. It coordinates the different `Connectors` to run against investigation targets, osaaates results into a `MasterIdentity` object, and manages the browser-based discovery phase.

2. **Connectors (`connectors/*.py`)**: 
   All connectors inherit from `BaseConnector`. They execute the discovery tools (CLI wrappers or direct API calls) and normalize output into a list of `DiscoveryResult` objects.

3. **Identity Expansion (`identity_expander.py`)**:
   Contains pure functions to generate username and email variants. This is purely heuristic-based and does not involve network calls.

4. **Reporter (`reporters/ai_report_writer.py`)**:
   Responsible for processing collected artifacts and leveraging the `AIAnalyst` (LLM) to generate final reports.


## Pipeline hardening — search quality & performance

These behaviours keep the evidence set relevant and bound a run's cost. The
URL/relevance heuristics live as pure, unit-tested helpers in
`utils/url_filter.py` and `utils/result_validation.py`.

- **URL filtering** (`utils/url_filter.py`): `is_search_engine_url()` identifies
  pages served by the seed search engines — these are SERPs, never evidence.
  The browser skips such *discovered* URLs before launching Chrome, and the
  report's Evidence Log omits them.
- **Relevance gating**: `looks_like_serp()` rejects captured pages that are
  themselves search-results listings (the target appears on them by
  construction); the browser content gate also requires the target to appear in
  page text rather than accepting any incidental mention.
- **Result validation** (`utils/result_validation.py`): `is_meaningful_result()`
  rejects pages that merely echo the query (the Tor onion front-ends do this).
- **Browser budgeting**: discovered URLs are de-duplicated, SERP-filtered and
  capped to `Orchestrator.max_urls_per_domain` per domain. A page-load timeout
  (`BROWSER_PAGELOAD_TIMEOUT`, default 20s) prevents stalls, and bot-block
  pages (e.g. Google `/sorry`) record the domain in a per-run backoff set so it
  is not hit again.
- **Driver reuse**: `BrowserConnector.run_many()` visits a batch of URLs on a
  single Chrome instance (per proxy chunk) instead of relaunching+patching a
  driver per URL — the dominant cost of a run.
- **Speculative account checks**: for a username with no known email, the
  orchestrator derives `<user>@<provider>` candidates
  (`IdentityExpander.derive_candidate_emails`) and runs the email connectors on
  them, flagging results `speculative` and capping their confidence.
- **Knowledge corroboration** (`reporters/corroboration.py`): each biographical
  knowledge fact is marked `corroborated` / `partial` / `unconfirmed` against
  the collected evidence and rendered in report section 2.1.
