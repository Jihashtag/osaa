"""
Models Module
-------------
Defines the core data structures used by the Orchestrator to represent
investigated subjects and clustered identity data.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


@dataclass
class IdentityCluster:
    """
    Represents a clustered group of identified artifacts related to a subject.

    Attributes:
        cluster_id (str): Unique identifier for the identity cluster.
        confidence (float): Probability score of the cluster match (0.0 to 1.0).
        nodes (List[Dict[str, Any]]): List of artifacts or nodes linked to this identity.
    """

    cluster_id: str
    confidence: float
    nodes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class IdentityAnchor:
    """
    Represents a core identity artifact with associated confidence.
    """

    value: str
    aggregate_confidence: float = 1.0


@dataclass
class MasterIdentity:
    """
    The central unified data structure representing the investigated subject.
    Contains all collected artifacts and potential identity anchors.

    Attributes:
        email (List[IdentityAnchor]): Discovered email addresses.
        username (List[IdentityAnchor]): Discovered usernames.
        fullname (List[str]): Potential full names identified.
        discovered_urls (List[str]): External links associated with the subject.
        raw_artifacts (List[Dict[str, Any]]): Unprocessed data points collected by tools.
    """

    email: List[IdentityAnchor] = field(default_factory=list)
    username: List[IdentityAnchor] = field(default_factory=list)
    fullname: List[str] = field(default_factory=list)
    discovered_urls: List[str] = field(default_factory=list)
    raw_artifacts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Knowledge:
    """
    Type-safe knowledge base for the profiling engine.

    Attributes:
        identity (Dict[str, Any]): Core identity attributes (e.g., email, fullname).
        behavioral_tags (List[str]): List of identified behavioral patterns.
        metadata (Dict[str, Any]): Additional context and source information.
    """

    identity: Dict[str, Any]
    behavioral_tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the knowledge instance to a dictionary representation.
        """
        return asdict(self)

    def to_json_string(self) -> str:
        """
        Serializes the knowledge instance to a JSON string.
        """
        return json.dumps(self.to_dict())

    def validate(self) -> None:
        """
        Validates the knowledge attributes.
        Raises:
            ValueError: If identity contains an invalid email format.
        """
        email = self.identity.get("email")
        if email:
            # Simple regex for email validation
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                raise ValueError(f"Invalid email format: {email}")
