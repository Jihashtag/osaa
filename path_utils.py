import os
import re

BASE_PATH = None
BASE_TARGET = None
# Set via --output; when present it short-circuits the target-name-derived
# directory so every caller (connectors, report writer) lands in the same
# user-chosen place instead of "Report_<target>_resources".
OUTPUT_OVERRIDE = None


def set_output_override(path: str | None) -> None:
    global OUTPUT_OVERRIDE
    OUTPUT_OVERRIDE = path


def get_report_dir(target_name: str | None = None, base_path: str | None = None) -> str:
    global BASE_PATH, BASE_TARGET

    if OUTPUT_OVERRIDE is not None:
        os.makedirs(OUTPUT_OVERRIDE, exist_ok=True)
        return OUTPUT_OVERRIDE

    # Slugify completely
    if base_path is not None:
        BASE_PATH = base_path
    if BASE_TARGET is None:
        BASE_TARGET = target_name
    else:
        target_name = BASE_TARGET
    if BASE_PATH is None:
        raise Exception("Did not initialize BASE_PATH")
    safe_name = re.sub(r"[^a-zA-Z0-9]", "_", target_name)
    path = os.path.join(BASE_PATH, f"Report_{safe_name}_resources")
    os.makedirs(path, exist_ok=True)
    return path
