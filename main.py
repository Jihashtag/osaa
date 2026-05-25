import argparse
import asyncio
import logging
import os
import subprocess
from orchestrator import Orchestrator
from identity_expander import IdentityExpander
from ai_analyst import AIAnalyst
from path_utils import get_report_dir
from reporters.ai_report_writer import AIReportWriter
from proxy_utils import load_proxies
from random import shuffle
from models import IdentityAnchor
from knowledge_loader import KnowledgeLoader


async def main():
    base_path = os.getcwd()

    parser = argparse.ArgumentParser()
    parser.add_argument("--username", help="Target known username")
    parser.add_argument("--name", help="Target known full name")
    parser.add_argument("--email", help="Target known email")
    parser.add_argument("--debug", action="store_true", help="Enable debug logs")
    parser.add_argument(
        "--ai-agent",
        choices=["lms", "ollama", "gemini"],
        default="lms",
        help="AI agent to use for analysis",
    )
    parser.add_argument("--model", help="Model the AI agent should use")
    parser.add_argument(
        "--proxy_list", help="Path to a file containing proxies (ip:port)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print execution plan without running"
    )
    parser.add_argument(
        "--knowledge-file", help="Path to a JSON file containing certified knowledge"
    )

    args = parser.parse_args()

    if args.debug:
        os.environ["DEBUG"] = "True"
    else:
        os.environ["DEBUG"] = "False"

    logging.basicConfig(
        level=(
            logging.WARNING
            if not os.environ.get("DEBUG", False) == "True"
            else logging.INFO
        )
    )

    proxies = []
    if args.proxy_list:
        proxies = load_proxies(args.proxy_list)

    # Initialize knowledge from CLI args or file
    knowledge = None
    if args.knowledge_file:
        knowledge = KnowledgeLoader.from_json(args.knowledge_file)
    else:
        # Fallback to CLI basic knowledge
        knowledge = KnowledgeLoader.from_dict(
            {"username": args.username, "fullname": args.name, "email": args.email}
        )

    target = {"username": args.username, "fullname": args.name, "email": args.email}
    target_id = args.username or args.name or args.email

    output_dir = get_report_dir(target_id, base_path)

    additional_targets = (
        []
        + (
            IdentityExpander.generate_username_permutations(args.username)
            if args.username
            else []
        )
        + (IdentityExpander.generate_name_permutations(args.name) if args.name else [])
    )
    shuffle(additional_targets)

    orchestrator = Orchestrator(proxies=proxies, knowledge=knowledge)

    for key, val in target.items():
        if not val:
            continue
        if key == "username":
            orchestrator.identity.username.append(IdentityAnchor(value=val))
        if key == "email":
            orchestrator.identity.email.append(IdentityAnchor(value=val))
        if key == "fullname":
            orchestrator.identity.fullname.append(val)

    targets = [
        {"type": key, "value": val} for key, val in target.items()
    ] + additional_targets

    await orchestrator.run_full_pipeline(targets)

    analyst = AIAnalyst(agent_type=args.ai_agent, model_name=args.model)
    writer = AIReportWriter(analyst)

    final_md = await writer.generate_report(
        target_id, orchestrator.identity, knowledge=knowledge
    )

    report_path = os.path.join(output_dir, "Report.md")
    with open(report_path, "x", encoding="utf-8") as f:
        f.write(final_md)
    print(f"\n[*] REPORT_SAVED: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
