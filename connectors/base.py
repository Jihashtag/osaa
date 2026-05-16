from logger import get_logger
import os

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List
from profiles import DiscoveryProfile


@dataclass
class DiscoveryResult:
    source_tool: str
    target_type: str
    value: str
    metadata: Dict[str, Any]


class BaseConnector(ABC):
    @property
    @abstractmethod
    def supported_types(self) -> List[str]:
        """Returns the list of artifact types this connector can process."""
        pass
