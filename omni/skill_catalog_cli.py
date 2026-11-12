"""Read-only command handlers for the versioned skill catalog.

These commands inspect trusted metadata and scan caller-provided local snapshots.
They never fetch repositories, approve skills, change lifecycle state, or execute
any skill content.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .skill_resolver import resolve_skills, resolution_to_dict

from .skill_catalog import (
    SkillCatalog,
    SkillCatalogError,
    SkillPolicy,
    ingest_skill,
    load_skill_policy,
    scan_skill,
)


def _registry_directory(args: Any) -> Path:
    return Path(args.registry) if getattr(args, "registry", None) else Path(__file__).resolve().parent.parent / "registry"


def _source_json(source) -> Dict[str, Any]:
    return {
        "source_id": source.source_id,
        "skill_id": source.skill_id,
        "repository_url": source.repository_url,
        "skill_path": source.skill_path,
        "commit_sha": source.commit_sha,
        "license_spdx": source.license_spdx,
        "upstream_identity": source.upstream_identity,
        "maintainer": source.maintainer,
    }


def _approval_json(approval):
    if approval is None:
        return None
    return {
        "approver": approval.approver,
        "digest": approval.digest,
        "reference": approval.reference,
    }


def _record_json(record) -> Dict[str, Any]:
    return {
        "skill_id": record.skill_id,
        "source_id": record.source_id,
        "sha256": record.sha256,
        "state": record.state,
        "approval": _approval_json(record.approval),
    }


def _load_snapshot(directory: Path, policy: SkillPolicy) -> Dict[str, bytes]:
    """Read a bounded local directory, rejecting symlinks and special files."""
    if not directory.is_dir() or directory.is_symlink():
        raise SkillCatalogError(f"snapshot directory does not exist or is unsafe: {directory}")
    files: Dict[str, bytes] = {}
    total_bytes = 0
    for current, dirnames, filenames in os.walk(directory, topdown=True, followlinks=False):
        current_path = Path(current)
        for dirname in list(dirnames):
            child = current_path / dirname
            if child.is_symlink():
                raise SkillCatalogError(f"snapshot contains a symlink directory: {child}")
        for filename in filenames:
            path = current_path / filename
            if path.is_symlink() or not path.is_file():
                raise SkillCatalogError(f"snapshot contains a symlink or special file: {path}")
            relative = path.relative_to(directory).as_posix()
            if len(files) >= policy.max_files:
                raise SkillCatalogError(f"skill contains too many files (max {policy.max_files})")
            total_bytes += path.stat().st_size
            if total_bytes > policy.max_bytes:
                raise SkillCatalogError(f"skill snapshot exceeds {policy.max_bytes} bytes")
            files[relative] = path.read_bytes()
    if not files:
        raise SkillCatalogError("snapshot directory contains no files")
    return files


def handle_skill_command(args: Any) -> Optional[int]:
    """Handle catalog/inspect/scan verbs, or return None for legacy search."""
    terms = list(getattr(args, "terms", []) or [])
    if not terms or terms[0] not in {"catalog", "inspect", "scan", "resolve"}:
        return None

    action = terms[0]
    if action == "catalog" and len(terms) != 1:
        print("usage: omni skills catalog", file=sys.stderr)
        return 2
    if action in {"inspect", "scan"} and len(terms) != 2:
        print(f"usage: omni skills {action} <skill-id>", file=sys.stderr)
        return 2
    if action == "resolve" and len(terms) < 2:
        print("usage: omni skills resolve <task brief>", file=sys.stderr)
        return 2

    try:
        root = _registry_directory(args)
        catalog = SkillCatalog.load(root)
        problems = catalog.validate()
        if problems:
            raise SkillCatalogError("catalog consistency errors: " + "; ".join(problems))

        if action == "catalog":
            items = [
                {"source": _source_json(source), "trust": _record_json(record)}
                for source, record in catalog.items()
            ]
            print(json.dumps({"schema_version": 1, "count": len(items), "skills": items}, indent=2, ensure_ascii=False))
            return 0

        if action == "resolve":
            if getattr(args, "snapshot_dir", None):
                print("usage: omni skills resolve <task brief> (does not accept --snapshot-dir)", file=sys.stderr)
                return 2
            request = " ".join(terms[1:]).strip()
            policy = load_skill_policy(root)
            snapshots = {}
            for source, record in catalog.items():
                if record.state not in {"approved", "available", "active"}:
                    continue
                if not source.license_spdx or source.license_spdx not in policy.allowed_licenses:
                    continue
                snapshot_dir = root / "snapshots" / record.skill_id
                snapshot = ingest_skill(source, _load_snapshot(snapshot_dir, policy), policy=policy)
                if snapshot.sha256 != record.sha256:
                    raise SkillCatalogError(
                        f"{record.skill_id}: snapshot SHA-256 does not match the pinned lock record"
                    )
                snapshots[record.skill_id] = snapshot
            result = resolve_skills(request, catalog, snapshots, policy=policy)
            print(json.dumps(resolution_to_dict(result), indent=2, ensure_ascii=False))
            return 0

        skill_id = terms[1]
        if action == "scan" and skill_id == "all":
            if getattr(args, "snapshot_dir", None):
                print("usage: omni skills scan all (does not accept --snapshot-dir)", file=sys.stderr)
                return 2
            policy = load_skill_policy(root)
            reports = []
            for source, record in catalog.items():
                snapshot_dir = root / "snapshots" / record.skill_id
                snapshot = ingest_skill(source, _load_snapshot(snapshot_dir, policy), policy=policy)
                if snapshot.sha256 != record.sha256:
                    raise SkillCatalogError(
                        f"{record.skill_id}: snapshot SHA-256 does not match the pinned lock record"
                    )
                report = scan_skill(snapshot, policy=policy)
                reports.append({
                    "skill_id": record.skill_id,
                    "sha256": report.sha256,
                    "rules_scanned": list(report.rules_scanned),
                    "blocking": report.blocking,
                    "findings": [
                        {
                            "rule_id": finding.rule_id,
                            "severity": finding.severity,
                            "path": finding.path,
                            "line_number": finding.line_number,
                            "evidence": finding.evidence,
                        }
                        for finding in report.findings
                    ],
                })
            blocking = any(item["blocking"] for item in reports)
            print(json.dumps({
                "schema_version": 1,
                "count": len(reports),
                "blocking": blocking,
                "skills": reports,
                "note": "Static pattern scan only; no findings is not a safety certification.",
            }, indent=2, ensure_ascii=False))
            return 1 if blocking else 0

        entry = catalog.get(skill_id)
        if entry is None:
            print(f"unknown skill in trust catalog: {skill_id}", file=sys.stderr)
            return 1
        source, record = entry

        if action == "inspect":
            print(json.dumps({"source": _source_json(source), "trust": _record_json(record)}, indent=2, ensure_ascii=False))
            return 0

        policy = load_skill_policy(root)
        snapshot_dir = Path(getattr(args, "snapshot_dir", None) or (root / "snapshots" / skill_id))
        snapshot = ingest_skill(source, _load_snapshot(snapshot_dir, policy), policy=policy)
        if snapshot.sha256 != record.sha256:
            raise SkillCatalogError("snapshot SHA-256 does not match the pinned lock record")
        report = scan_skill(snapshot, policy=policy)
        output = {
            "skill_id": skill_id,
            "sha256": report.sha256,
            "rules_scanned": list(report.rules_scanned),
            "blocking": report.blocking,
            "findings": [
                {
                    "rule_id": finding.rule_id,
                    "severity": finding.severity,
                    "path": finding.path,
                    "line_number": finding.line_number,
                    "evidence": finding.evidence,
                }
                for finding in report.findings
            ],
            "note": "Static pattern scan only; no findings is not a safety certification.",
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    except (SkillCatalogError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
