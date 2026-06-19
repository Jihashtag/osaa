# Tor Connector Documentation & Usage Guide

This document describes the design, implementation, and configuration of the Tor-based OSINT discovery system.

Unlike typical script engines using simple raw sockets, the `osaa` Tor connector uses Selenium-based Chromium automation over a local SOCKS5 proxy, allowing it to navigate Javascript-heavy onion search engines, handle captcha checks, and take screenshots of evidence.

---

## Technical Design

The Tor connector is implemented in [connectors/tor.py](../connectors/tor.py) as the [TorConnector](../connectors/tor.py#L28) class.

### 1. Prerequisite Verification
- The connector executes a `pgrep tor` check via subprocess to verify that the local Tor daemon process is active. If the daemon is not running, the connector logs a warning and exits early to prevent browser connection timeouts.

### 2. Driver Configuration
- The Chromium driver is instantiated via `undetected_chromedriver` with headless flags, certificate validation bypasses, and proxy settings routed directly to the SOCKS5 proxy:
  ```
  --proxy-server=socks5://127.0.0.1:9050
  ```
- The session is wrapped using `selenium-stealth` (masking languages, browser vendor settings, and platform properties) to prevent detection by anti-bot monitors.

### 3. Dynamic Onion Search Engine Discovery
To avoid relying on hardcoded onion links (which change frequently), the connector retrieves active search endpoints dynamically:
- It visits directories:
  - `https://onion.live/?category=search%20engine`
  - `http://5n4qdkw2wavc55peppyrelmb2rgsx7ohcb2tkxhub2gyfurxulfyd3id.onion/index.php?cat=Search`
- It extracts elements matching onion patterns and returns a list of discovered onion search engines.

### 4. Search and Capture Lifecycle
- **Onion Engine Queries**: The connector selects the first 3 discovered search engines. It visits the engine URL, detects search text boxes using attributes (type/name matches), enters the target handle, and submits. If input boxes are not found, it falls back to a query parameter format:
  ```
  /search?q={target}
  ```
- **Global Queries**: To search anonymous search engines, the connector queries DuckDuckGo and Yandex using Tor.
- **Verification & Storage**:
  - The retrieved HTML body text is passed to [is_meaningful_result](../utils/result_validation.py#L15) to filter out empty search pages or bare query echoes.
  - Valid findings are saved as raw files (`tor_{hash}.raw`) and accompanied by a desktop PNG screenshot (`tor_{hash}_screen.png`) saved inside the target output directory.

---

## Installation & Configuration

### 1. Install System Dependencies
Install the tor service daemon on Linux:
```bash
sudo apt update
sudo apt install -y tor
sudo systemctl enable --now tor
```

### 2. Verify Port Routing
The Tor daemon by default exposes a SOCKS5 proxy at `127.0.0.1:9050`. You can verify connection routing using curl:
```bash
curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/
```

### 3. Webdriver Dependencies
Ensure Google Chrome/Chromium and compatible drivers are present on the host. These are managed automatically by `undetected_chromedriver` during initialization.
