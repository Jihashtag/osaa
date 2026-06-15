"""
Blocklist Module
----------------
This module provides utilities for filtering out noisy or irrelevant artifacts
from OSINT discovery results, such as local project paths or system noise.
"""

import os

# Known local project paths and noise to exclude from discovery
BLOCKLIST = {
    "python_holmes",
    "python_toolkie",
    "docker_mail_used",
    "osaa",
    "venv",
    ".git",
    "osint",
    "tests",
}


def is_local_noise(value: str) -> bool:
    """
    Checks if a given artifact is likely local project noise.

    Args:
        value (str): The artifact string (e.g., path, username, etc.) to check.

    Returns:
        bool: True if the artifact is considered noise/local file, False otherwise.
    """
    # Use exact matching or word-based matching for blocklist to avoid partial hits on valid names
    val_lower = value.lower()

    # Check for exact matches in blocklist (common noise)
    if val_lower in BLOCKLIST:
        return True

    # Source-file artifacts: match only when the value *ends* with a code
    # extension (a real filename) rather than any substring, so URLs like
    # "blog.python.org" or "site.py.dev" are not wrongly dropped.
    if val_lower.endswith((".py", ".pyc", ".pyo")):
        return True

    # Local directory markers, matched as path segments (with separators) to
    # avoid clobbering legitimate identifiers that merely contain the word.
    segment_markers = ("__pycache__", "node_modules", "/.git/", "/.git")
    if any(marker in val_lower for marker in segment_markers):
        return True

    return False
