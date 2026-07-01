import argparse
import asyncio
import logging
import os
import sys
from random import shuffle

import doctor
import path_utils
from orchestrator import Orchestrator
from identity_expander import IdentityExpander
from ai_analyst import AIAnalyst
from path_utils import get_report_dir
from reporters.ai_report_writer import AIReportWriter
from proxy_utils import load_proxies
from models import IdentityAnchor
from knowledge_loader import KnowledgeLoader

AI_AGENT_CHOICES = ["lms", "ollama", "gemini", "ollama-http", "lms-server"]


def _ratio_type(value: str) -> float:
    try:
        f = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a number, got {value!r}")
    if not (0.0 < f <= 1.0):
        raise argparse.ArgumentTypeError(f"must be within (0, 1], got {f}")
    return f


def _existing_file(value: str) -> str:
    if not os.path.isfile(value):
        raise argparse.ArgumentTypeError(f"file not found: {value}")
    return value


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="osaa",
        description="Recursive, modular OSINT fusion engine for local identity resolution.",
    )
    parser.add_argument("--version", action="version", version="osaa 0.2.0")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--debug", action="store_true", help="Enable debug logs")

    identity = argparse.ArgumentParser(add_help=False)
    ident_g = identity.add_argument_group("target identity (at least one required)")
    ident_g.add_argument("--username", help="Target known username")
    ident_g.add_argument("--name", help="Target known full name")
    ident_g.add_argument("--email", help="Target known email")

    knowledge_p = argparse.ArgumentParser(add_help=False)
    know_g = knowledge_p.add_argument_group("certified knowledge")
    know_g.add_argument(
        "--knowledge-file",
        type=_existing_file,
        help="Path to a JSON file containing certified knowledge",
    )
    know_g.add_argument(
        "--knowledge",
        help="Free-text knowledge about the target (alternative to --knowledge-file)",
    )

    tool_dirs = argparse.ArgumentParser(add_help=False)
    tool_g = tool_dirs.add_argument_group(
        "external tool locations (fallback: env var, then a sibling checkout)"
    )
    tool_g.add_argument(
        "--tookie-dir", help="Path to the Tookie-OSINT checkout (env: TOOKIE_DIR)"
    )
    tool_g.add_argument(
        "--holmes-dir", help="Path to the MrHolmes checkout (env: HOLMES_DIR)"
    )

    discovery = argparse.ArgumentParser(add_help=False)
    disc_g = discovery.add_argument_group("discovery tuning")
    disc_g.add_argument(
        "--ratio",
        type=_ratio_type,
        default=0.33,
        help="Fraction (0,1] of targets/URLs to actually process (default: 0.33)",
    )
    disc_g.add_argument(
        "--proxy-list",
        dest="proxy_list",
        help="Path to a file containing proxies (ip:port)",
    )

    ai = argparse.ArgumentParser(add_help=False)
    ai_g = ai.add_argument_group("AI backend")
    ai_g.add_argument(
        "--ai-agent",
        choices=AI_AGENT_CHOICES,
        default="lms",
        help="AI agent used for report synthesis. The *-http/-server variants "
        "reuse a running LLM server and are much faster.",
    )
    ai_g.add_argument("--model", help="Model the AI agent should use")
    ai_g.add_argument(
        "--ai-endpoint",
        help="Base URL for the HTTP LLM backends (default: ollama 11434 / lms 1234)",
    )

    run_p = sub.add_parser(
        "run",
        parents=[identity, knowledge_p, tool_dirs, discovery, ai, common],
        help="Run the full discovery + fusion pipeline and write a report",
    )
    run_p.add_argument(
        "--output",
        help="Directory to write the report and artifacts to "
        "(default: ./Report_<target>_resources)",
    )
    run_p.add_argument(
        "--force", action="store_true", help="Overwrite an existing report at the destination"
    )

    sub.add_parser(
        "plan",
        parents=[identity, knowledge_p, tool_dirs, discovery, common],
        help="Print the execution plan (which connectors run on which target) "
        "without any network I/O",
    )

    doctor_p = sub.add_parser(
        "doctor",
        parents=[tool_dirs, ai, common],
        help="Check that the configured AI backend, Tor, and tool paths are "
        "reachable before committing to a run",
    )
    doctor_p.add_argument(
        "--proxy-list", dest="proxy_list", help="Path to a proxy list to validate"
    )

    return parser


def _build_targets(args):
    if args.knowledge_file:
        knowledge = KnowledgeLoader.from_json(args.knowledge_file)
    elif args.knowledge:
        knowledge = KnowledgeLoader.from_text(
            args.knowledge,
            username=args.username,
            fullname=args.name,
            email=args.email,
        )
    else:
        knowledge = KnowledgeLoader.from_dict(
            {"username": args.username, "fullname": args.name, "email": args.email}
        )

    target = {"username": args.username, "fullname": args.name, "email": args.email}
    target_id = args.username or args.name or args.email

    additional_targets = (
        IdentityExpander.generate_username_permutations(args.username)
        if args.username
        else []
    ) + (IdentityExpander.generate_name_permutations(args.name) if args.name else [])
    shuffle(additional_targets)

    targets = [
        {"type": key, "value": val} for key, val in target.items()
    ] + additional_targets
    return target, target_id, targets, knowledge


def cmd_plan(args) -> int:
    base_path = os.getcwd()
    target, target_id, targets, knowledge = _build_targets(args)
    output_dir = get_report_dir(target_id, base_path)

    orchestrator = Orchestrator(
        proxies=load_proxies(args.proxy_list) if args.proxy_list else [],
        knowledge=knowledge,
        ratio=args.ratio,
        tookie_dir=args.tookie_dir,
        holmes_dir=args.holmes_dir,
    )

    print("[*] Execution plan (no network I/O):")
    print(f"    output dir: {output_dir}")
    print(f"    knowledge : {knowledge.to_dict() if knowledge else None}")
    for entry in orchestrator.plan(targets):
        print(
            f"    [{entry['type']}] {entry['value']} -> "
            f"{', '.join(entry['connectors']) or '(no connectors)'}"
        )
    print(f"    total targets: {len(targets)}")
    return 0


async def cmd_run(args) -> int:
    base_path = os.getcwd()
    target, target_id, targets, knowledge = _build_targets(args)

    if args.output:
        path_utils.set_output_override(args.output)
    output_dir = get_report_dir(target_id, base_path)

    report_path = os.path.join(output_dir, "Report.md")
    if os.path.exists(report_path) and not args.force:
        print(
            f"[x] A report already exists at {report_path}. "
            "Use --force to overwrite or --output to pick another location.",
            file=sys.stderr,
        )
        return 1

    orchestrator = Orchestrator(
        proxies=load_proxies(args.proxy_list) if args.proxy_list else [],
        knowledge=knowledge,
        ratio=args.ratio,
        tookie_dir=args.tookie_dir,
        holmes_dir=args.holmes_dir,
    )
    for key, val in target.items():
        if not val:
            continue
        if key == "username":
            orchestrator.identity.username.append(IdentityAnchor(value=val))
        if key == "email":
            orchestrator.identity.email.append(IdentityAnchor(value=val))
        if key == "fullname":
            orchestrator.identity.fullname.append(val)

    print(f"[*] Target: {target_id}")
    print(f"[*] Output: {output_dir}")

    await orchestrator.run_full_pipeline(targets)

    print(f"[*] Generating AI report via {args.ai_agent}...")
    analyst = AIAnalyst(
        agent_type=args.ai_agent, model_name=args.model, endpoint=args.ai_endpoint
    )
    writer = AIReportWriter(analyst)
    final_md = await writer.generate_report(
        target_id, orchestrator.identity, knowledge=knowledge
    )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_md)
    print(f"\n[*] REPORT_SAVED: {report_path}")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command in ("run", "plan") and not (args.username or args.name or args.email):
        parser.error(
            f"{args.command}: at least one of --username, --name, --email is required"
        )

    os.environ["DEBUG"] = "True" if args.debug else "False"
    logging.basicConfig(level=logging.INFO if args.debug else logging.WARNING)

    if args.command == "doctor":
        return doctor.run(args)
    if args.command == "plan":
        return cmd_plan(args)
    if args.command == "run":
        return asyncio.run(cmd_run(args))
    return 1


if __name__ == "__main__":
    sys.exit(main())
