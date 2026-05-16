"""
Models Module
-------------
Defines the core data structures used by the osaaator to represent
investigated subjects and clustered identity data.
"""

from dataclasses import dataclass, field
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
class MasterIdentity:
    """
    The central unified data structure representing the investigated subject.
    Contains all collected artifacts and potential identity anchors.

    Attributes:
        email (List[str]): Discovered email addresses.
        username (List[str]): Discovered usernames.
        fullname (List[str]): Potential full names identified.
        discovered_urls (List[str]): External links associated with the subject.
        raw_artifacts (List[Dict[str, Any]]): Unprocessed data points collected by tools.
    """

    email: List[str] = field(default_factory=list)
    username: List[str] = field(default_factory=list)
    fullname: List[str] = field(default_factory=list)
    discovered_urls: List[str] = field(default_factory=list)
    raw_artifacts: List[Dict[str, Any]] = field(default_factory=list)
