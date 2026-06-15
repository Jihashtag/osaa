# Step-by-Step Guide: Building a Multi-Engine Tor Search Connector

This document outlines the detailed steps required to implement a robust, multi-engine Tor-based search connector.

## Step 1: Environment Setup
Ensure you have the necessary system packages and Python libraries.

1. **System Dependencies**:
   Install Tor, `torsocks`, and `tor` controller interface.
   ```bash
   sudo apt update
   sudo apt install -y tor torsocks
   sudo systemctl enable --now tor
   ```

2. **Python Dependencies**:
   Install `PySocks`, `requests`, and `stem` (for circuit management).
   ```bash
   pip install PySocks requests stem
   ```

## Step 2: Advanced Implementation
Create a new file at `osaa/connectors/tor_search.py`. This implementation includes circuit management and robust error handling.

```python
import socks
import socket
import requests
import time
import random
from stem import Signal
from stem.control import Controller
from connectors.base import BaseConnector, DiscoveryResult

class TorMultiSearchConnector(BaseConnector):
    """
    Connector that rotates through multiple onion search engines 
    and handles circuit rotation for anonymity.
    """
    
    SEARCH_ENGINES = [
        ("Ahmia", "http://juhanurmihxlp77detqtr6chb2k6f6j2q25q5aodq75u2nrl73r2n5ad.onion/search?q={}"),
        ("Torch", "http://torchdeedp3i2jigzjdmfpn5wkgi4q5vspg4g5yosnylp4nup6p6w5tqd.onion/search?q={}"),
    ]

    def _apply_proxy(self):
        socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
        socket.socket = socks.socksocket

    def renew_circuit(self):
        """Forces Tor to switch the exit node."""
        try:
            with Controller.from_port(port=9051) as controller:
                controller.authenticate(password='your_password') # Ensure ControlPort/CookieAuth is set
                controller.signal(Signal.NEWNYM)
        except Exception as e:
            print(f"Failed to renew circuit: {e}")

    def run(self, target: str):
        self._apply_proxy()
        
        all_results = []
        for name, template in self.SEARCH_ENGINES:
            # Randomize sleep to avoid fingerprinting
            time.sleep(random.uniform(3, 7))
            
            try:
                url = template.format(target)
                response = requests.get(url, timeout=45)
                
                if response.status_code == 200:
                    all_results.append(DiscoveryResult(
                        source_tool=name,
                        target_type="search",
                        value=target,
                        metadata={"snippet": response.text[:200]}
                    ))
                # Rotate circuit periodically for improved anonymity
                if random.random() < 0.2:
                    self.renew_circuit()
            except Exception as e:
                # Log error and continue to the next engine
                continue
                
        return all_results
```

## Step 3: Integration
1. Import `TorMultiSearchConnector` in `osaa/orchestrator.py`.
2. Add an instance of this connector to your pipeline configuration in `orchestrator.py`.

## Step 4: Verification and Configuration
1. **Tor Controller Access**:
   To enable `stem` (circuit renewal), ensure `ControlPort 9051` is enabled in your `/etc/tor/torrc` file.
   
2. **Connectivity Test**:
   ```bash
   torsocks curl https://check.torproject.org
   ```

3. **Circuit Verification**:
   Check logs to confirm your IP changes after a `renew_circuit()` call.

## Best Practices
- **Rate Limiting**: Always use randomized sleep delays to avoid detection.
- **Circuit Maintenance**: Periodically renew the Tor circuit using `stem` to ensure different exit nodes are used for different engines.
- **Robustness**: Always wrap engine-calls in `try/except` blocks so one engine's downtime does not crash the entire search pipeline.
- **Configuration**: Avoid hardcoding search engine URLs if possible. Move them to a separate configuration file in `osaa/config/` for easier maintenance as `.onion` links change.

## Result validation
Onion search front-ends often render the query back on an otherwise-empty page.
The connector gates every captured page through
`utils.result_validation.is_meaningful_result(query, content, links)`, which
rejects bare query echoes (content ≈ query with no surrounding text or links) so
they never enter the evidence set.
