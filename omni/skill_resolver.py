"""Deterministic, trust-gated skill matching. This module never executes skills."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Mapping, Tuple

from .skill_catalog import SkillCatalog, SkillIngestionResult, SkillPolicy, scan_skill

EXECUTABLE_STATES = frozenset({"approved", "available", "active"})
_TOKEN = re.compile(r"[a-z0-9+#_.-]+")
_STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "into", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "using", "with", "without", "your",
})


@dataclass(frozen=True)
class SkillMatch:
    """One approved skill that passed integrity and static-scan gates."""

    skill_id: str
    source_id: str
    sha256: str
    state: str
    name: str
    description: str
    score: float
    matched_terms: Tuple[str, ...]


@dataclass(frozen=True)
class SkillResolution:
    """Read-only resolution result with explicit exclusion counts."""

    request: str
    matches: Tuple[SkillMatch, ...]
    eligible_count: int
    excluded_counts: Dict[str, int]


def _tokens(value: str) -> set[str]:
    return {token for token in _TOKEN.findall(value.lower()) if token not in _STOP_WORDS}


def resolve_skills(
    request: str,
    catalog: SkillCatalog,
    snapshots: Mapping[str, SkillIngestionResult],
    *,
    policy: SkillPolicy | None = None,
    max_results: int = 3,
) -> SkillResolution:
    """Rank only approved, licensed, intact, non-blocking skill snapshots.

    The score is lexical overlap between request terms and the skill name and
    description. It is a relevance hint, not a quality or safety score. Skills
    are never activated or executed by this function.
    """
    if not isinstance(request, str) or not request.strip():
        raise ValueError("request must be non-empty text")
    if type(max_results) is not int or max_results < 1:
        raise ValueError("max_results must be a positive integer")
    active_policy = policy or SkillPolicy()
    request_terms = _tokens(request)
    if not request_terms:
        raise ValueError("request must contain at least one searchable term")

    excluded = {
        "trust_state": 0,
        "missing_approval": 0,
        "unsupported_license": 0,
        "missing_snapshot": 0,
        "integrity_mismatch": 0,
        "blocking_static_scan": 0,
        "no_relevant_terms": 0,
    }
    matches = []

    # Hard gates run before relevance scoring; ranking cannot override them.
    for source, record in catalog.items():
        if record.state not in EXECUTABLE_STATES:
            excluded["trust_state"] += 1
            continue
        if record.approval is None or record.approval.digest != record.sha256:
            excluded["missing_approval"] += 1
            continue
        if not source.license_spdx or source.license_spdx not in active_policy.allowed_licenses:
            excluded["unsupported_license"] += 1
            continue
        snapshot = snapshots.get(record.skill_id)
        if snapshot is None:
            excluded["missing_snapshot"] += 1
            continue
        if snapshot.source != source or snapshot.sha256 != record.sha256:
            excluded["integrity_mismatch"] += 1
            continue
        if scan_skill(snapshot, policy=active_policy).blocking:
            excluded["blocking_static_scan"] += 1
            continue

        metadata = snapshot.metadata
        name = metadata.get("name", record.skill_id)
        description = metadata.get("description", "")
        skill_terms = _tokens(f"{name} {description}")
        matched_terms = tuple(sorted(request_terms & skill_terms))
        if not matched_terms:
            excluded["no_relevant_terms"] += 1
            continue
        score = round(len(matched_terms) / len(request_terms), 3)
        matches.append(SkillMatch(
            skill_id=record.skill_id,
            source_id=record.source_id,
            sha256=record.sha256,
            state=record.state,
            name=name,
            description=description,
            score=score,
            matched_terms=matched_terms,
        ))

    ranked = tuple(sorted(matches, key=lambda item: (-item.score, item.skill_id)))
    return SkillResolution(
        request=request,
        matches=ranked[:max_results],
        eligible_count=len(ranked),
        excluded_counts=excluded,
    )


def resolution_to_dict(result: SkillResolution) -> dict:
    """Return stable JSON-friendly output for the read-only CLI."""
    return {
        "request": result.request,
        "eligible_count": result.eligible_count,
        "returned_count": len(result.matches),
        "matches": [
            {
                "skill_id": item.skill_id,
                "source_id": item.source_id,
                "sha256": item.sha256,
                "state": item.state,
                "name": item.name,
                "description": item.description,
                "score": item.score,
                "matched_terms": list(item.matched_terms),
            }
            for item in result.matches
        ],
        "excluded_counts": dict(sorted(result.excluded_counts.items())),
        "executions_performed": 0,
        "note": "Lexical relevance only; a match is not an evaluation score or permission to execute.",
    }
