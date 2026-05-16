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
    # Check if any blacklisted project keywords are present in the value
    if any(item in value.lower() for item in BLOCKLIST):
        return True

    # Check if the value resolves to an existing file/directory path
    if os.path.exists(value):
        return True

    return False
