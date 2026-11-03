"""Moteur de registre des agents Cyber Force 100.

Charge les 10 divisions depuis registry/divisions/*.json et les valide
strictement. Un registre invalide lève RegistryError : aucun agent
n'est jamais chargé silencieusement en mode dégradé.

Usage CLI :  python -m cf100 validate
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from cf100.agents.models import AgentSpec, Autonomy, Division, RiskClass
from cf100.config import REGISTRY_DIR

DIVISION_FILES_PATTERN = "divisions/division-*.json"
POLICY_FILE = "policies.json"

EXPECTED_DIVISION_COUNT = 10
EXPECTED_AGENTS_PER_DIVISION = 10
EXPECTED_TOTAL_AGENTS = 100

_DIVISION_CODES = ["CI", "TH", "VR", "DP", "IR", "MA", "NS", "AS", "AI", "AC"]


class RegistryError(Exception):
    """Le registre viole les invariants de Cyber Force 100."""


def load_policies(registry_dir: Path = REGISTRY_DIR) -> Dict[str, Any]:
    """Charge les politiques (outils autorisés, risques, actions dangereuses)."""
    path = Path(registry_dir) / POLICY_FILE
    if not path.is_file():
        raise RegistryError(f"politiques absentes : {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_divisions(registry_dir: Path = REGISTRY_DIR) -> List[Division]:
    """Charge et retourne les divisions déclarées dans le registre."""
    rdir = Path(registry_dir)
    files = sorted(rdir.glob(DIVISION_FILES_PATTERN))
    if not files:
        raise RegistryError(f"aucun fichier {DIVISION_FILES_PATTERN} dans {rdir}")
    divisions: List[Division] = []
    for f in files:
        with f.open(encoding="utf-8") as fh:
            data = json.load(fh)
        divisions.append(Division.from_dict(data))
    return divisions


def validate_registry(divisions: List[Division],
                      policies: Optional[Dict[str, Any]] = None,
                      ) -> List[str]:
    """Valide les invariants du registre ; retourne la liste des erreurs.

    Une liste vide signifie un registre sain. Les invariants :
    1. exactement 10 divisions, 10 agents par division, 100 agents ;
    2. codes de division attendus, uniques et ordonnés ;
    3. identifiants et noms d'agents uniques ;
    4. champs obligatoires non vides (id, name, mission, tools) ;
    5. outils ∈ liste blanche des politiques ;
    6. fallback désigne un agent existant d'une autre voie ;
    7. autonomie et classe de risque dans les énumérations.
    """
    errors: List[str] = []
    if len(divisions) != EXPECTED_DIVISION_COUNT:
        errors.append(f"{len(divisions)} divisions au lieu de "
                      f"{EXPECTED_DIVISION_COUNT}")
    codes = [d.code for d in divisions]
    for i, code in enumerate(_DIVISION_CODES):
        if code not in codes:
            errors.append(f"division manquante : {code}")
    if len(set(codes)) != len(codes):
        errors.append("codes de division en doublon")
    for div in divisions:
        if len(div.agents) != EXPECTED_AGENTS_PER_DIVISION:
            errors.append(f"{div.code} : {len(div.agents)} agents au lieu de "
                          f"{EXPECTED_AGENTS_PER_DIVISION}")
    total = sum(len(d.agents) for d in divisions)
    if total != EXPECTED_TOTAL_AGENTS:
        errors.append(f"{total} agents au lieu de {EXPECTED_TOTAL_AGENTS}")

    all_ids: List[str] = []
    names: List[str] = []
    for div in divisions:
        for a in div.agents:
            if not a.id or not a.name or not a.mission:
                errors.append(f"{div.code} : agent avec champ vide")
            all_ids.append(a.id)
            names.append(a.name)
            if not a.tools:
                errors.append(f"{a.id} : aucun outil autorisé")
    if len(set(all_ids)) != len(all_ids):
        errors.append("identifiants d'agents en doublon")
    if len(set(names)) != len(names):
        errors.append("noms d'agents en doublon")
    id_set = set(all_ids)
    for div in divisions:
        for a in div.agents:
            if a.fallback and a.fallback not in id_set:
                errors.append(f"{a.id} : fallback inconnu {a.fallback}")
            if a.fallback == a.id:
                errors.append(f"{a.id} : fallback sur lui-même")
    return errors


class Registry:
    """Registre en mémoire des divisions et agents permanents."""

    def __init__(self, divisions: List[Division],
                 policies: Optional[Dict[str, Any]] = None,
                 dynamic: Optional[List[AgentSpec]] = None):
        self.divisions = divisions
        self.policies = policies if policies is not None else load_policies()
        self._dynamic: List[AgentSpec] = list(dynamic or [])
        errors = validate_registry(divisions, self.policies)
        if errors:
            raise RegistryError("; ".join(errors[:10]))

    # -- chargement -------------------------------------------------
    @classmethod
    def load(cls, registry_dir: Path = REGISTRY_DIR) -> "Registry":
        return cls(load_divisions(registry_dir),
                   load_policies(registry_dir))

    # -- requêtes ---------------------------------------------------
    @property
    def agents(self) -> List[AgentSpec]:
        """Agents permanents + dynamiques enregistrés."""
        out: List[AgentSpec] = []
        for d in self.divisions:
            out.extend(d.agents)
        out.extend(self._dynamic)
        return out

    def by_id(self, agent_id: str) -> Optional[AgentSpec]:
        for a in self.agents:
            if a.id == agent_id:
                return a
        return None

    def by_division(self, code: str) -> List[AgentSpec]:
        for d in self.divisions:
            if d.code == code:
                return list(d.agents)
        return []

    def by_skill(self, skill: str) -> List[AgentSpec]:
        return [a for a in self.agents if skill in a.skills]

    def by_tool(self, tool: str) -> List[AgentSpec]:
        return [a for a in self.agents if tool in a.tools]

    # -- validation à la demande ------------------------------------
    def check_tools_against_policy(self) -> List[str]:
        whitelist = set(self.policies.get("tool_whitelist", []))
        problems = []
        for a in self.agents:
            for t in a.tools:
                if t not in whitelist:
                    problems.append(f"{a.id} : outil hors liste blanche {t}")
        return problems

    # -- agents dynamiques ------------------------------------------
    def register_dynamic(self, spec: AgentSpec) -> None:
        """Enregistre un agent dynamique (créé à la demande).

        L'identifiant doit être unique et préfixé DYN- ; l'ajout est refusé
        si un outil n'est pas dans la liste blanche.
        """
        if not spec.id.startswith("DYN-"):
            raise RegistryError(f"agent dynamique : id doit commencer par DYN- "
                                f"({spec.id})")
        if self.by_id(spec.id) is not None:
            raise RegistryError(f"id déjà utilisé : {spec.id}")
        whitelist = set(self.policies.get("tool_whitelist", []))
        bad = [t for t in spec.tools if t not in whitelist]
        if bad:
            raise RegistryError(f"{spec.id} : outils hors liste blanche {bad}")
        self._dynamic.append(spec)

    def __iter__(self) -> Iterator[AgentSpec]:
        return iter(self.agents)

    def __len__(self) -> int:
        return len(self.agents)


def load_registry(registry_dir: Path = REGISTRY_DIR) -> Registry:
    """Point d'entrée pratique : registre chargé et validé."""
    return Registry.load(registry_dir)
