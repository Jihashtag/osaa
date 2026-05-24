from logger import get_logger
import os

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List
from profiles import DiscoveryProfile


@dataclass
class DiscoveryResult:
    source_tool: str
    target_type: str
    value: str
    metadata: Dict[str, Any]
    confidence: float = 1.0
    meta: Dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    @property
    @abstractmethod
    def supported_types(self) -> List[str]:
        """Returns the list of artifact types this connector can process."""
        pass

    @property
    def requires_hashing(self) -> bool:
        """Indicates if the connector requires targets to be hashed for privacy."""
        return False
