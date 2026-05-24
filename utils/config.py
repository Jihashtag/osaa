import os
import yaml
from typing import Dict


def load_reliability_weights() -> Dict[str, float]:
    """Loads source reliability weights from reliability.yaml."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "reliability.yaml")

    if not os.path.exists(config_path):
        # Default fallback weights
        return {"holehe": 0.95, "tookie": 0.85, "holmes": 0.80, "searcher": 0.55}

    with open(config_path, "r") as f:
        return yaml.safe_load(f)
