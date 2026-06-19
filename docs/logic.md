# System Logic & Hardening Mechanisms

This document outlines the core logic patterns, heuristic validation steps, and performance optimizations implemented within the `osaa` engine.

---

## Core Logic Flow

1. **Orchestration Loop ([orchestrator.py](../orchestrator.py))**:
   Coordinates the execution timeline. It handles state transitions inside [MasterIdentity](../models.py#L41) and controls concurrency throttling (limiting parallel executions to 5 concurrent workers via semaphores).

2. **Heuristic Normalization ([identity_expander.py](../identity_expander.py))**:
   Performs token permutations and regex categorization to increase search coverage.

3. **Discovery Dispatch ([connectors/](../connectors))**:
   Runs queries across CLI utilities, HTTP connections, or Chromium automation. Results are normalized into [DiscoveryResult](../connectors/base.py#L7) tuples.

4. **Probabilistic Identity Fusion ([fusion_engine.py](../fusion_engine.py))**:
   Compares newly found elements against established parameters using the logic:
   $$P_{\text{link}} = (\text{FuzzScore} \times 0.6) + (\text{SourceTrust} \times 0.3) + (\text{ContextBonus} \times 0.1)$$
   - **FuzzScore**: Fuzzy token ratio calculations via `rapidfuzz`.
   - **SourceTrust**: Reliability parameters loaded from [reliability.yaml](../config/reliability.yaml).
   - **ContextBonus**: Elevated weighting (+0.1) when emails share privacy-focused domains (e.g. ProtonMail, Tutanota).
   - If $P_{\text{link}} \ge 0.80$, the link is merged. Warnings are issued for potential links ($0.60 \le P < 0.80$).

5. **AI Extraction & Report Generation ([reporters/ai_report_writer.py](../reporters/ai_report_writer.py))**:
   Collates evidence, clusters references by registered domains, assesses corroboration, and produces the finalized markdown analysis.

---

## Pipeline Hardening, Relevance & Cost Optimization

To limit API/network overhead and prevent analysis pollution, `osaa` enforces several filters:

### 1. Relevance Gating & URL Filtering
- **SERP Filtering ([url_filter.py](../utils/url_filter.py#L86))**:
  Identifies and discards URLs of known search engines (e.g. Google, Bing, Yandex). These are Search Engine Result Pages (SERPs) containing the query by construction, and do not represent target evidence.
- **SERP Body Detection ([url_filter.py](../utils/url_filter.py#L99))**:
  Scans pages for co-occurring search-related tokens ("safe search", "did you mean", "images", "videos"). If 3 or more co-occur, the page is flagged as a SERP and omitted.
- **Empty Echo Validation ([result_validation.py](../utils/result_validation.py#L15))**:
  onion directories often return the search query on an empty error page. [is_meaningful_result](../utils/result_validation.py#L15) rejects documents if they contain the query but lack external links or have insufficient surrounding characters.

### 2. Browser Budgeting & Performance Throttling
- **Domain Caps ([url_filter.py](../utils/url_filter.py#L120))**:
  Caps the crawled URLs from any single domain (default: 5). This prevents single sites (e.g. forums) from consuming the whole processing time.
- **Bot-Block Interstitial Handling ([url_filter.py](../utils/url_filter.py#L111))**:
  Detects captcha blocks and adds the domain to a per-run blacklist, preventing further attempts on that domain.
- **Chrome Driver Reuse ([browser.py](../connectors/browser.py#L308))**:
  [run_many](../connectors/browser.py#L308) queries a batch of targets on a single Chrome instance, removing the high cost of launching a new driver process for each link.

### 3. Speculative Verification
- **Email derivation ([identity_expander.py](../identity_expander.py#L78))**:
  If only a username is known, it generates hypothetical emails (e.g., `user@gmail.com`, `user@proton.me`) to run through Holehe and Breach checks.
- **Down-weighting ([orchestrator.py](../orchestrator.py#L182))**:
  Speculative hits are tagged as `speculative` and capped at 0.5 confidence, ensuring they do not pollute official findings.

### 4. Knowledge Corroboration
- **Fact Checking ([corroboration.py](../reporters/corroboration.py#L33))**:
  [assess](../reporters/corroboration.py#L33) compares biographical facts against extracted texts. It tags facts as `corroborated`, `partial`, or `unconfirmed` based on exact or fuzzy token matches.
