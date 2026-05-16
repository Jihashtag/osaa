import os
import re

BASE_PATH = None
BASE_TARGET = None


def get_report_dir(target_name: str | None = None, base_path: str | None = None) -> str:
    global BASE_PATH, BASE_TARGET

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
