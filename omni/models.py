"""Core data types for the OmniBrain network.

Everything here is plain data so it can be serialised into the run trace and
asserted on in tests. No behaviour lives in this module.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
# Registry entities
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Agent:
    """A role profile, not a running program.

    An agent profile says *what* should be done, by which tools it is allowed to
    do it, and where the knowledge came from. Actual execution always requires
    an explicit :class:`omni.executor.Provider`.
    """

    id: str
    title: str
    specialties: List[str]
    skills: List[str]
    provenance: str
    boundaries: List[str] = field(default_factory=list)
    brief_template: str = ""

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Agent":
        return Agent(
            id=d["id"],
            title=d["title"],
            specialties=list(d.get("specialties", [])),
            skills=list(d.get("skills", [])),
            provenance=d.get("provenance", ""),
            boundaries=list(d.get("boundaries", [])),
            brief_template=d.get("brief_template", ""),
        )


@dataclass(frozen=True)
class Skill:
    id: str
    title: str
    source: str
    specialties: List[str]
    verification: str  # "repo-exists" | "path-verified" | "unverified"
    notes: str = ""

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Skill":
        return Skill(
            id=d["id"],
            title=d["title"],
            source=d["source"],
            specialties=list(d.get("specialties", [])),
            verification=d.get("verification", "unverified"),
            notes=d.get("notes", ""),
        )


# --------------------------------------------------------------------------- #
# Planning
# --------------------------------------------------------------------------- #
@dataclass
class Task:
    id: str
    specialty: str
    title: str
    objective: str
    acceptance_criteria: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)


@dataclass
class Brief:
    """Self-contained instructions handed to one agent in one wave."""

    task_id: str
    agent_id: str
    specialty: str
    objective: str
    acceptance_criteria: List[str]
    allowed_tools: List[str]
    boundaries: List[str]
    context: Dict[str, Any] = field(default_factory=dict)
    attempt: int = 1
    correction_of: Optional[str] = None
    missing_criteria: List[str] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [
            f"# Task {self.task_id} -> agent {self.agent_id} (attempt {self.attempt})",
            f"Specialty: {self.specialty}",
            "",
            "## Objective",
            self.objective,
            "",
            "## Acceptance criteria",
        ]
        lines += [f"- {c}" for c in self.acceptance_criteria] or ["- (none declared)"]
        lines += ["", "## Allowed tools"]
        lines += [f"- {t}" for t in self.allowed_tools] or ["- (none)"]
        if self.boundaries:
            lines += ["", "## Boundaries (do not cross)"]
            lines += [f"- {b}" for b in self.boundaries]
        if self.correction_of:
            lines += [
                "",
                "## Correction requested",
                f"Previous attempt {self.correction_of} was incomplete.",
                "Missing criteria: " + ", ".join(self.missing_criteria or ["(unspecified)"]),
            ]
        if self.context:
            lines += ["", "## Shared context", json.dumps(self.context, indent=2, ensure_ascii=False)]
        return "\n".join(lines)


@dataclass
class Assignment:
    task: Task
    agent_id: str
    wave: int
    brief: Brief


@dataclass
class Classification:
    size: str  # simple | medium | complex
    scores: Dict[str, float]
    specialties: List[str]
    rationale: str

    @property
    def squad_size(self) -> int:
        return max(1, len(self.specialties))


@dataclass
class Plan:
    request: str
    classification: Classification
    tasks: List[Task]
    assignments: List[Assignment]
    squad: List[str]
    unresolved_specialties: List[str] = field(default_factory=list)

    @property
    def waves(self) -> List[List[Assignment]]:
        out: Dict[int, List[Assignment]] = {}
        for a in self.assignments:
            out.setdefault(a.wave, []).append(a)
        return [out[k] for k in sorted(out)]


# --------------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------------- #
@dataclass
class ProviderResult:
    status: str = "failed"  # ok | failed | incomplete | pending_human
    summary: str = ""
    evidence: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    met_criteria: List[str] = field(default_factory=list)
    claims: Dict[str, Any] = field(default_factory=dict)
    executed: bool = False
    provider: str = "none"
    error: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Result:
    task_id: str
    agent_id: str
    status: str
    summary: str
    evidence: List[str]
    artifacts: List[str]
    met_criteria: List[str]
    claims: Dict[str, Any]
    executed: bool
    provider: str
    attempt: int = 1
    error: Optional[str] = None
    duration_s: float = 0.0
    reassigned_from: Optional[str] = None

    @classmethod
    def from_provider(cls, brief: Brief, pr: ProviderResult, reassigned_from: Optional[str] = None) -> "Result":
        return cls(
            task_id=brief.task_id,
            agent_id=brief.agent_id,
            status=pr.status,
            summary=pr.summary,
            evidence=list(pr.evidence),
            artifacts=list(pr.artifacts),
            met_criteria=list(pr.met_criteria),
            claims=dict(pr.claims),
            executed=pr.executed,
            provider=pr.provider,
            attempt=brief.attempt,
            error=pr.error,
            duration_s=pr.duration_s,
            reassigned_from=reassigned_from,
        )


@dataclass
class Correction:
    task_id: str
    agent_id: str
    missing_criteria: List[str]
    round: int


@dataclass
class Arbitration:
    topic: str
    values: Dict[str, Any]
    winner_agent: str
    winner_task: str
    rule: str
    resolved: bool = True


@dataclass
class GateFinding:
    gate: str
    passed: bool
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RunRecord:
    request: str
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    size: str = ""
    specialties: List[str] = field(default_factory=list)
    squad: List[str] = field(default_factory=list)
    results: List[Result] = field(default_factory=list)
    corrections: List[Correction] = field(default_factory=list)
    arbitrations: List[Arbitration] = field(default_factory=list)
    findings: List[GateFinding] = field(default_factory=list)
    unresolved_specialties: List[str] = field(default_factory=list)
    verdict: str = "NEEDS_WORK"
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    trace: List[Dict[str, Any]] = field(default_factory=list)

    def by_task(self) -> Dict[str, Result]:
        """Latest result per task."""
        out: Dict[str, Result] = {}
        for r in self.results:
            out[r.task_id] = r
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "request": self.request,
            "size": self.size,
            "specialties": self.specialties,
            "squad": self.squad,
            "verdict": self.verdict,
            "unresolved_specialties": self.unresolved_specialties,
            "results": [asdict(r) for r in self.results],
            "corrections": [asdict(c) for c in self.corrections],
            "arbitrations": [asdict(a) for a in self.arbitrations],
            "findings": [f.to_dict() for f in self.findings],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": (self.finished_at or self.started_at) - self.started_at,
        }
