"""``osaa doctor`` — pre-flight checks for the configured AI backend and
external tool locations.

Failures here used to only surface an hour into a run (an unreachable LM
Studio server, a missing Tookie-OSINT checkout) as a silently empty section
or a buried exception. This lets a user check *before* committing to a run.
"""

import os
import shutil
import subprocess


def _check_cli_binary(name: str) -> tuple:
    path = shutil.which(name)
    return (bool(path), path or "not found on PATH")


def _check_http_endpoint(url: str, timeout: float = 3.0) -> tuple:
    try:
        import requests

        resp = requests.get(url, timeout=timeout)
        return True, f"reachable ({url}, HTTP {resp.status_code})"
    except Exception as e:
        return False, f"unreachable ({url}): {e}"


def _check_dir(path: str, label: str) -> tuple:
    if not os.path.isdir(path):
        return False, f"{label} checkout not found: {path}"
    return True, path


def _check_tor() -> tuple:
    try:
        subprocess.check_output(["pgrep", "tor"], stderr=subprocess.DEVNULL)
        return True, "daemon running"
    except FileNotFoundError:
        return False, "'pgrep' not available, cannot check"
    except subprocess.CalledProcessError:
        return False, "daemon not running — the Tor connector will skip and return no results"


_AI_BACKENDS = {
    "lms": ("cli", "lms"),
    "ollama": ("cli", "ollama"),
    "gemini": ("cli", "gemini"),
    "ollama-http": ("http", "http://localhost:11434", "/api/tags"),
    "lms-server": ("http", "http://localhost:1234", "/v1/models"),
}


def run(args) -> int:
    """Print an OK/MISSING table for the configured backend and tool paths.

    Returns a process exit code: 0 if every check passed, 1 otherwise.
    """
    rows = []  # (label, ok, detail)

    kind, *rest = _AI_BACKENDS[args.ai_agent]
    if kind == "cli":
        (binary,) = rest
        ok, detail = _check_cli_binary(binary)
    else:
        default_endpoint, path = rest
        endpoint = (args.ai_endpoint or default_endpoint).rstrip("/")
        ok, detail = _check_http_endpoint(endpoint + path)
    rows.append((f"AI backend ({args.ai_agent})", ok, detail))

    rows.append(("Tor daemon", *_check_tor()))

    ok, detail = _check_cli_binary("holehe")
    rows.append(("holehe CLI", ok, detail))

    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(base_dir)
    for label, cli_val, env_name, default_subdir in (
        ("Tookie-OSINT dir", args.tookie_dir, "TOOKIE_DIR", "python_toolkie"),
        ("MrHolmes dir", args.holmes_dir, "HOLMES_DIR", "python_holmes"),
    ):
        resolved = cli_val or os.environ.get(env_name) or os.path.join(
            repo_root, default_subdir
        )
        rows.append((label, *_check_dir(resolved, label)))

    if args.proxy_list:
        ok = os.path.isfile(args.proxy_list)
        detail = args.proxy_list if ok else f"file not found: {args.proxy_list}"
        rows.append(("Proxy list", ok, detail))

    # With backend="auto" there's always a usable backend (leakcheck.io needs
    # no key), so that case is informational rather than a pass/fail check.
    # An explicit --breach-backend hibp without a key is a real
    # misconfiguration though (every call will 401), so that IS a failure.
    breach_key = args.breach_api_key or os.environ.get("HIBP_API_KEY")
    backend = args.breach_backend
    if backend == "hibp" and not breach_key:
        rows.append(
            (
                "Breach lookup",
                False,
                "--breach-backend hibp requested but no --breach-api-key / "
                "HIBP_API_KEY configured — every call will fail",
            )
        )
    else:
        if backend == "auto":
            backend = "hibp" if breach_key else "leakcheck"
        detail = (
            "hibp (key configured)"
            if backend == "hibp"
            else "leakcheck.io (free, no key required)"
        )
        rows.append(("Breach lookup", True, detail))

    width = max(len(label) for label, _, _ in rows)
    for label, ok, detail in rows:
        status = "OK" if ok else "MISSING"
        print(f"[{status:>7}] {label.ljust(width)}  {detail}")

    all_ok = all(ok for _, ok, _ in rows)
    print()
    print("All checks passed." if all_ok else "Some checks failed — see above.")
    return 0 if all_ok else 1
