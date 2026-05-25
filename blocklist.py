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

    # Check for common local path markers (more specific)
    path_markers = {".py", ".pyc", "__pycache__", "node_modules", ".git/"}
    if any(marker in val_lower for marker in path_markers):
        return True

    return False
