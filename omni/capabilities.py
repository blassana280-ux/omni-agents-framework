"""Registre des capacités OmniBrain SUPREME.

Couche d'intégration au-dessus de "registry/skills.json" : une *capacité*
est une brique logicielle externe ou interne réutilisable, décrite avec ses
prérequis, ses permissions, ses dépendances, ses points d'entrée (lecture
paresseuse), ses preuves de vérification, ses tests et son statut
d'intégration.

Règles de sécurité appliquées par ce module :

* le code des dépôts externes n'est **jamais** exécuté ici — il est indexé,
  catégorisé et chargé à la demande (lecture de fichiers) par l'agent qui en a
  besoin, avec approbation humaine pour toute exécution ;
* un projet externe ne peut être référencé que sous une licence permissive
  déclarée dans "licenses_allowed" ;
* aucun secret ne doit figurer dans le registre ou le journal de résultats
  (détection + rédaction automatiques).

CLI : "python -m omni.capabilities --validate" (validations CI).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

REGISTRY_FILENAME = "capabilities.json"

SECRET_PATTERNS: Dict[str, "re.Pattern[str]"] = {
    "github-token": re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}"),
    "openai-key": re.compile(r"sk-[A-Za-z0-9]{8,}"),
    "slack-token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "aws-key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private-key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "bearer-token": re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    "generic-credential": re.compile(
        r"""(?i)\b[A-Z0-9_]*(?:API[_-]?KEY|ACCESS[_-]?TOKEN|REFRESH[_-]?TOKEN|CLIENT[_-]?SECRET|SECRET|PASSWORD|AUTHORIZATION|PRIVATE[_-]?KEY)\b\s*(?:=\s*|:\s+)(?:"[^"]*"|'[^']*'|[^\s,;]+)"""
    ),
}


class CapabilityError(RuntimeError):
    pass


def redact(text: Any) -> str:
    """Renvoie le texte avec tout motif de secret remplacé par [REDACTED]."""
    out = str(text)
    for pattern in SECRET_PATTERNS.values():
        out = pattern.sub("[REDACTED]", out)
    return out


def scan_secrets(payload: Any) -> List[str]:
    """Noms des motifs de secret détectés dans la charge utile."""
    blob = json.dumps(payload, ensure_ascii=False)
    return [name for name, pattern in SECRET_PATTERNS.items() if pattern.search(blob)]


# --------------------------------------------------------------------------- #
# Data types
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class EntryPoint:
    path: str
    purpose: str

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EntryPoint":
        return EntryPoint(path=d["path"], purpose=d.get("purpose", ""))


@dataclass(frozen=True)
class TestRef:
    name: str
    status: str
    reason: str = ""

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "TestRef":
        return TestRef(name=d.get("name", ""), status=d.get("status", ""), reason=d.get("reason", ""))


@dataclass(frozen=True)
class Capability:
    id: str
    title: str
    domain: str
    description: str
    specialties: List[str]
    status: str  # indexed | forked | verified | rejected
    upstream: Optional[str]
    fork: Optional[str]
    license_spdx: str
    license_verified: str
    risk: str
    execution_policy: str
    prerequisites: List[str]
    permissions_needed: List[str]
    dependencies: List[str]
    entry_points: List[EntryPoint]
    evidence: List[str]
    verified_at: str
    reason: str
    tests: List[TestRef]

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Capability":
        source = d.get("source") or {}
        lic = d.get("license") or {}
        integ = d.get("integration") or {}
        return Capability(
            id=d["id"],
            title=d.get("title", ""),
            domain=d.get("domain", ""),
            description=d.get("description", ""),
            specialties=list(d.get("specialties", [])),
            status=integ.get("status", "indexed"),
            upstream=source.get("upstream"),
            fork=source.get("fork"),
            license_spdx=lic.get("spdx", ""),
            license_verified=lic.get("verified", "unverified"),
            risk=d.get("risk", "medium"),
            execution_policy=d.get("execution_policy", "external-manual-only"),
            prerequisites=list(d.get("prerequisites", [])),
            permissions_needed=list(d.get("permissions_needed", [])),
            dependencies=list(d.get("dependencies", [])),
            entry_points=[EntryPoint.from_dict(e) for e in d.get("entry_points", [])],
            evidence=list(integ.get("evidence", [])),
            verified_at=integ.get("verified_at", ""),
            reason=integ.get("reason", ""),
            tests=[TestRef.from_dict(t) for t in d.get("tests", [])],
        )

    def repo_ref(self) -> str:
        """Dépôt à lire en priorité pour le chargement paresseux."""
        return self.fork or self.upstream or ""


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
class CapabilityRegistry:
    def __init__(self, data: Dict[str, Any], capabilities: Dict[str, Capability],
                 root: Optional[Path] = None) -> None:
        self.data = data
        self.capabilities = capabilities
        self.root = root

    # ------------------------------------------------------------------ load
    @classmethod
    def load(cls, path: str | Path) -> "CapabilityRegistry":
        p = Path(path)
        if p.is_dir():
            p = p / REGISTRY_FILENAME
        if not p.is_file():
            raise CapabilityError(f"missing capability registry: {p}")
        with p.open(encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise CapabilityError(f"invalid JSON in {p}: {exc}") from exc
        capabilities: Dict[str, Capability] = {}
        for item in data.get("capabilities", []):
            cap = Capability.from_dict(item)
            if cap.id in capabilities:
                raise CapabilityError(f"duplicate capability id: {cap.id}")
            capabilities[cap.id] = cap
        return cls(data, capabilities, p.parent)

    # --------------------------------------------------------------- queries
    def by_domain(self) -> Dict[str, List[Capability]]:
        out: Dict[str, List[Capability]] = {}
        for cap in self.capabilities.values():
            out.setdefault(cap.domain, []).append(cap)
        return out

    def search(self, terms: List[str], domain: Optional[str] = None) -> List[Capability]:
        """Découverte : recherche plein-texte sur id/titre/description/domaine."""
        lowered = [t.lower() for t in terms if t and t.strip()]
        hits: List[Capability] = []
        for cap in self.capabilities.values():
            if domain and cap.domain != domain:
                continue
            haystack = " ".join(
                [cap.id, cap.title, cap.description, cap.domain] + list(cap.specialties)
            ).lower()
            if not lowered or any(t in haystack for t in lowered):
                hits.append(cap)
        return hits

    @staticmethod
    def _safe_entry_path(path: str) -> bool:
        """Only allow unambiguous repository-relative POSIX paths."""
        if (
            not isinstance(path, str)
            or not path
            or "\x00" in path
            or "\\" in path
            or path.startswith("/")
            or re.match(r"^[A-Za-z]:", path)
        ):
            return False
        parts = path.split("/")
        if parts[-1] == "":
            parts = parts[:-1]  # directory entry points may end with one slash
        return bool(parts) and all(part not in ("", ".", "..") for part in parts)

    def entry_paths(self, cap_id: str) -> List[Dict[str, str]]:
        """Directives de chargement paresseux : quoi lire, dans quel dépôt, pourquoi."""
        cap = self.capabilities.get(cap_id)
        if cap is None:
            raise CapabilityError(f"unknown capability: {cap_id}")
        directives: List[Dict[str, str]] = []
        for ep in cap.entry_points:
            if not self._safe_entry_path(ep.path):
                raise CapabilityError(f"unsafe entry point path for '{cap_id}': {ep.path!r}")
            directives.append({"repo": cap.repo_ref(), "path": ep.path, "purpose": ep.purpose})
        return directives

    def suggest_agents(self, cap_id: str, registry: Any) -> List[str]:
        """Routage : agents de l'orchestrateur couvrant les spécialités de la capacité."""
        cap = self.capabilities.get(cap_id)
        if cap is None:
            raise CapabilityError(f"unknown capability: {cap_id}")
        agents: List[str] = []
        for specialty in cap.specialties:
            for agent in registry.agents_for(specialty):
                if agent.id not in agents:
                    agents.append(agent.id)
        return agents

    def dependency_report(self) -> Dict[str, List[str]]:
        return {cid: list(cap.dependencies) for cid, cap in self.capabilities.items()
                if cap.dependencies}

    def forks_pending(self) -> List[Capability]:
        return [c for c in self.capabilities.values()
                if c.status == "indexed" and c.upstream]

    def status_report(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for cap in self.capabilities.values():
            counts[cap.status] = counts.get(cap.status, 0) + 1
        return {
            "total": len(self.capabilities),
            "by_status": counts,
            "by_domain": {d: len(v) for d, v in sorted(self.by_domain().items())},
            "forks_pending": [c.id for c in self.forks_pending()],
        }

    # ----------------------------------------------------------- validation
    def validate(self, known_specialties: Optional[List[str]] = None) -> List[str]:
        """Renvoie tous les problèmes trouvés ; liste vide = registre cohérent."""
        problems: List[str] = []
        data = self.data

        if data.get("version") != 1:
            problems.append("capabilities.json: version != 1")
        statuses = set(data.get("statuses", []))
        allowed_licenses = set(data.get("licenses_allowed", []))
        domains = set(data.get("domains", {}))
        if not statuses:
            problems.append("no statuses declared")
        if not allowed_licenses:
            problems.append("no licenses_allowed declared")
        if not self.capabilities:
            problems.append("no capabilities declared")

        for cap in self.capabilities.values():
            where = f"capability '{cap.id}'"
            if not cap.title or not cap.description:
                problems.append(f"{where}: missing title or description")
            if cap.status not in statuses:
                problems.append(f"{where}: unknown status '{cap.status}'")
            if cap.domain not in domains:
                problems.append(f"{where}: unknown domain '{cap.domain}'")
            if not cap.entry_points:
                problems.append(f"{where}: no entry_points (lazy loading impossible)")
            for entry_point in cap.entry_points:
                if not self._safe_entry_path(entry_point.path):
                    problems.append(
                        f"{where}: unsafe entry point path {entry_point.path!r}"
                    )
            if not cap.specialties:
                problems.append(f"{where}: no routing specialties")
            if cap.upstream:
                if cap.license_spdx not in allowed_licenses:
                    problems.append(
                        f"{where}: license '{cap.license_spdx}' not in licenses_allowed"
                    )
                if cap.status in ("forked", "verified") and not cap.fork:
                    problems.append(
                        f"{where}: status '{cap.status}' requires a fork reference"
                    )
            if cap.status == "indexed" and not cap.upstream:
                problems.append(f"{where}: indexed status requires an upstream source")
            if cap.status == "verified":
                if not cap.evidence:
                    problems.append(f"{where}: verified status requires evidence")
                if not any(t.status == "pass" for t in cap.tests):
                    problems.append(
                        f"{where}: verified status requires at least one passing test"
                    )
            if known_specialties is not None:
                for specialty in cap.specialties:
                    if specialty not in known_specialties:
                        problems.append(
                            f"{where}: unknown routing specialty '{specialty}'"
                        )

        for name in scan_secrets(data):
            problems.append(f"secret pattern detected in registry: {name}")
        return problems


# --------------------------------------------------------------------------- #
# Results memory — mémoire des résultats et des erreurs
# --------------------------------------------------------------------------- #
class CapabilityLedger:
    """Journal JSONL des résultats et erreurs d'utilisation des capacités.

    Toute valeur écrite passe par "redact()" — un secret ne peut jamais y
    entrer, même par accident.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, cap_id: str, outcome: str, summary: str = "",
               evidence: Optional[List[str]] = None) -> Dict[str, Any]:
        if outcome not in ("ok", "error"):
            raise CapabilityError(f"outcome must be 'ok' or 'error', got '{outcome}'")
        entry = {
            "ts": round(time.time(), 3),
            "capability": cap_id,
            "outcome": outcome,
            "summary": redact(summary),
            "evidence": [redact(e) for e in (evidence or [])],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def history(self, cap_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.path.is_file():
            return []
        entries: List[Dict[str, Any]] = []
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue  # ligne corrompue : ignorée, jamais de crash
                if cap_id is None or entry.get("capability") == cap_id:
                    entries.append(entry)
        return entries


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
ACTION_FLAGS = {
    "--validate": "validate",
    "--list": "list",
    "--status": "status",
    "--pending": "pending",
    "--search": "search",
}


def _normalize_action(argv: List[str]) -> List[str]:
    """Accepte les deux formes : --validate (drapeau) et validate (positionnel)."""
    out = list(argv)
    for flag, action in ACTION_FLAGS.items():
        if flag in out:
            out.remove(flag)
            if action not in out:
                out.insert(0, action)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m omni.capabilities",
        description="Validation et interrogation du registre de capacités OmniBrain.",
    )
    parser.add_argument("action", nargs="?", default="validate",
                        choices=["validate", "list", "status", "pending", "search"])
    parser.add_argument("--terms", default="", help="termes de recherche (action search)")
    parser.add_argument("--registry", default=None,
                        help="chemin du registre (défaut : registry/ du dépôt)")
    args = parser.parse_args(_normalize_action(list(argv) if argv is not None else sys.argv[1:]))

    reg_path = Path(args.registry) if args.registry else \
        Path(__file__).resolve().parent.parent / "registry"

    try:
        registry = CapabilityRegistry.load(reg_path)
    except CapabilityError as exc:
        print(f"ERROR: {exc}")
        return 2

    if args.action == "validate":
        problems = registry.validate()
        if problems:
            for p in problems:
                print(f"PROBLEM: {p}")
            print(f"VALIDATION FAILED: {len(problems)} problem(s)")
            return 1
        print(f"OK: {len(registry.capabilities)} capacités, 0 problème")
        return 0

    if args.action == "list":
        for cap in registry.capabilities.values():
            print(f"{cap.id} [{cap.status}] {cap.domain} :: {cap.title}")
        return 0

    if args.action == "status":
        print(json.dumps(registry.status_report(), indent=2, ensure_ascii=False))
        return 0

    if args.action == "pending":
        for cap in registry.forks_pending():
            print(f"{cap.id} <- {cap.upstream}")
        return 0

    # search
    terms = [t for t in args.terms.split(",") if t.strip()]
    for cap in registry.search(terms):
        print(f"{cap.id} [{cap.status}] {cap.domain} :: {cap.title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
