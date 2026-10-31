"""Command line interface: ``python -m omni <command>``.

Exit codes: 0 success / READY, 1 NEEDS_WORK or error, 2 invalid usage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .audit import audit_account
from .executor import detect_clis, provider_from_env
from .gitops import GitOpsError, probe_branch_protection
from .overlays import apply as apply_overlay, plan as plan_overlays, write_manifest
from .orchestrator import Orchestrator
from .registry import Registry, RegistryError

DEFAULT_ACCOUNT = "blassana280-ux"
FrameworkDoc = "blassana280-ux/omni-agents-framework/blob/main/OMNIBRAIN.md"


def _registry(path: Optional[str]) -> Registry:
    return Registry.load(path or Path(__file__).resolve().parent.parent / "registry")


def cmd_plan(args: argparse.Namespace) -> int:
    registry = _registry(args.registry)
    orch = Orchestrator(registry, provider_from_env()[0], workspace=args.workspace)
    plan = orch.plan(args.request)
    print(f"size: {plan.classification.size}")
    print(f"rationale: {plan.classification.rationale}")
    print(f"squad: {', '.join(plan.squad) or '(none)'}")
    if plan.unresolved_specialties:
        print(f"unstaffed: {', '.join(plan.unresolved_specialties)}")
    for index, wave in enumerate(plan.waves, start=1):
        print(f"\nwave {index}:")
        for assignment in wave:
            print(f"  - {assignment.task.id} -> {assignment.agent_id} ({assignment.task.specialty})")
    if args.briefs:
        print("\n" + "\n\n".join(a.brief.to_text() for a in plan.assignments))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    registry = _registry(args.registry)
    provider, detail = provider_from_env()
    print(f"provider: {provider.name} ({detail})", file=sys.stderr)
    orch = Orchestrator(
        registry,
        provider,
        workspace=args.workspace,
        max_parallel=args.max_parallel,
        retries=args.retries,
        correction_rounds=args.correction_rounds,
    )
    record = orch.run(args.request)
    if args.json:
        print(json.dumps(record.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(orch.deliverable(record))
    return 0 if record.verdict == "READY" else 1


def cmd_providers(_: argparse.Namespace) -> int:
    provider, detail = provider_from_env()
    print(f"configured provider: {provider.name}")
    print(f"  detail: {detail}")
    print("\nlocal agent CLIs found on PATH:")
    for probe in detect_clis():
        mark = "yes" if probe["available"] else "no "
        print(f"  [{mark}] {probe['command']:<14} {probe['label']:<22} {probe['path'] or '-'}")
    print("\nSet OMNI_PROVIDER_CMD to enable real execution, e.g.:")
    print("  export OMNI_PROVIDER_CMD='claude -p {prompt}'")
    return 0


def cmd_registry(args: argparse.Namespace) -> int:
    registry = _registry(args.registry)
    problems = registry.validate()
    print(f"agents: {len(registry.agents)}  skills: {len(registry.skills)}  specialties: {len(registry.specialties)}")
    if problems:
        print("problems:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("registry coherent: no dangling agent, skill or specialty reference")
    return 0


def cmd_skills(args: argparse.Namespace) -> int:
    registry = _registry(args.registry)
    hits = registry.search_skills(args.terms)
    if not hits:
        print("no skill matches; the librarian must record a gap before a new agent is created")
        return 1
    for skill in hits:
        print(f"{skill.id:<28} {skill.verification:<14} {skill.source}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    report = audit_account(args.account, limit=args.limit)
    print(f"scanned {report['repos_scanned']} repositories of {report['account']}")
    print(f"repos carrying the injected routing file: {report['injected']}")
    print(f"repos where upstream instructions were overwritten: {len(report['overwritten'])}")
    for name in report["overwritten"]:
        print(f"  - {name}")
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"report written to {args.out}")
    return 0


def cmd_protection(args: argparse.Namespace) -> int:
    probe = probe_branch_protection(args.repo, args.branch)
    print(json.dumps(probe, indent=2))
    if args.apply:
        from .gitops import request_branch_protection

        res = request_branch_protection(args.repo, args.branch, execute=True)
        print(json.dumps(res.to_dict(), indent=2))
        return 0 if res.returncode == 0 else 1
    return 0 if probe["state"] in ("protected", "unprotected") else 1


def cmd_overlays(args: argparse.Namespace) -> int:
    actions = plan_overlays(args.account, limit=args.limit, only=args.only or None)
    pending = [a for a in actions if a.kind != "skip"]
    print(f"repositories scanned: {len(actions)}")
    print(f"actions required: {len(pending)}")
    for action in pending:
        print(f"  - {action.repo:<45} {action.kind:<16} {action.reason}")
    if args.manifest:
        path = write_manifest(actions, args.manifest, handled={"blassana280-ux/agentskills": "PR #4"})
        print(f"manifest written to {path}")
    if not args.apply:
        print("\ndry run — nothing was written. Re-run with --apply (needs write access).")
        return 0
    body = (
        "Automated repair by OmniBrain.\n\n"
        "The upstream `AGENTS.md` was replaced by the injected routing file. This PR restores it\n"
        "verbatim and appends the local network rules as a separate, clearly marked section.\n\n"
        f"Source of truth: `{FrameworkDoc}`\n"
    )
    blocked = 0
    for action in pending:
        result = apply_overlay(action, pr_body=body)
        line = f"  - {result.repo:<45} {result.status:<8} {result.detail}"
        if result.pr_url:
            line += f" {result.pr_url}"
        print(line)
        if result.status in ("blocked", "failed"):
            blocked += 1
    return 0 if blocked == 0 else 1


def cmd_selftest(_: argparse.Namespace) -> int:
    import unittest

    suite = unittest.TestLoader().discover(str(Path(__file__).resolve().parent.parent / "tests"),
                                           top_level_dir=str(Path(__file__).resolve().parent.parent))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="omni", description="OmniBrain orchestration CLI")
    parser.add_argument("--registry", help="path to the registry directory")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="classify a request and show the squad")
    plan.add_argument("request")
    plan.add_argument("--workspace", default=".")
    plan.add_argument("--briefs", action="store_true", help="print the full briefs")
    plan.set_defaults(func=cmd_plan)

    run = sub.add_parser("run", help="execute a request through the configured provider")
    run.add_argument("request")
    run.add_argument("--workspace", default=".")
    run.add_argument("--json", action="store_true")
    run.add_argument("--max-parallel", type=int, default=4, dest="max_parallel")
    run.add_argument("--retries", type=int, default=1)
    run.add_argument("--correction-rounds", type=int, default=1, dest="correction_rounds")
    run.set_defaults(func=cmd_run)

    prov = sub.add_parser("providers", help="show what can really execute briefs")
    prov.set_defaults(func=cmd_providers)

    reg = sub.add_parser("registry", help="validate the registries")
    reg.set_defaults(func=cmd_registry)

    skills = sub.add_parser("skills", help="search the skill registry")
    skills.add_argument("terms", nargs="+")
    skills.set_defaults(func=cmd_skills)

    audit = sub.add_parser("audit", help="audit the GitHub account (read-only)")
    audit.add_argument("--account", default=DEFAULT_ACCOUNT)
    audit.add_argument("--limit", type=int, default=200)
    audit.add_argument("--out")
    audit.set_defaults(func=cmd_audit)

    overlays = sub.add_parser("overlays", help="repair/refresh AGENTS.md across the account")
    overlays.add_argument("--account", default=DEFAULT_ACCOUNT)
    overlays.add_argument("--limit", type=int, default=200)
    overlays.add_argument("--only", nargs="*", help="restrict to these repository names")
    overlays.add_argument("--apply", action="store_true")
    overlays.add_argument("--manifest", help="write a content-free repair plan (markdown)")
    overlays.set_defaults(func=cmd_overlays)

    selftest = sub.add_parser("selftest", help="run the real test suite")
    selftest.set_defaults(func=cmd_selftest)

    protection = sub.add_parser("protection", help="probe branch protection (and optionally apply it)")
    protection.add_argument("repo")
    protection.add_argument("--branch", default="main")
    protection.add_argument("--apply", action="store_true")
    protection.set_defaults(func=cmd_protection)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (RegistryError, GitOpsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
