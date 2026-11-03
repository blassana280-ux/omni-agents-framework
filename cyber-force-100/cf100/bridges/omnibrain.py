"""OmniBrain Bridge — coordination avec l'orchestrateur central.

OmniBrain (dépôt omni-agents-framework, omni/orchestrator.py) est LE
coordinateur central : Cyber Force 100 ne le remplace jamais, il
s'y raccorde. Ce pont fournit, dès la Phase 1 :

1. lecture des registres OmniBrain (agents, permissions) pour
   l'alignement des formats et l'évitement des doublons ;
2. export des 100 agents CF100 au format compatible OmniBrain
   (mêmes champs que registry/agents.json : id, title, specialties,
   skills, provenance, boundaries, brief_template) — le fichier
   produit peut être fusionné dans le registre OmniBrain ;
3. un protocole de communication documenté (voir ci-dessous).

Protocole (Phase 1, lecture/export ; Phase 5, dispatch réel) :
- OmniBrain -> CF100 : demande avec {skill, task, context} ;
- CF100 -> OmniBrain : résultat avec {agent, ok, result, evidence_hash} ;
- toute demande passe la garde anti-injection et le moteur de
  politiques CF100 ; tout refus est retourné explicitement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from cf100.agents.registry import Registry
from cf100.config import OMNI_REGISTRY_DIR


class OmniBrainBridge:
    """Lecture des registres OmniBrain + export compatible."""

    def __init__(self, omni_registry_dir: Optional[Path] = None,
                 cf100_registry: Optional[Registry] = None):
        self.omni_dir = Path(omni_registry_dir
                             if omni_registry_dir is not None
                             else OMNI_REGISTRY_DIR)
        self.cf100 = cf100_registry

    # -- lecture des registres OmniBrain ---------------------------------
    def omni_agents(self) -> List[Dict[str, Any]]:
        path = self.omni_dir / "agents.json"
        if not path.is_file():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("agents", []))

    def omni_permissions(self) -> Dict[str, Any]:
        path = self.omni_dir / "permissions.json"
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def omni_dangerous_actions(self) -> List[str]:
        return list(self.omni_permissions().get("dangerous_actions", []))

    def find_omni_specialists(self, specialty: str) -> List[Dict[str, Any]]:
        return [a for a in self.omni_agents()
                if specialty in a.get("specialties", [])]

    # -- évitement de doublons -------------------------------------------
    def overlapping_skills(self) -> List[Dict[str, str]]:
        """Spécialités déjà couvertes par OmniBrain — CF100 les référence
        au lieu de les dupliquer (l'agent omni-security reste LE
        relecteur sécurité défensive ; CF100 apporte la profondeur 100)."""
        omni = {s for a in self.omni_agents()
                for s in a.get("specialties", [])}
        overlaps = []
        for agent in (self.cf100.agents if self.cf100 else []):
            for skill in agent.skills:
                if skill in omni:
                    overlaps.append({"agent": agent.id, "skill": skill})
        return overlaps

    # -- export vers le format OmniBrain -----------------------------------
    def export_cf100_for_omni(self, out_path: Optional[Path] = None) -> Path:
        """Produit registry-compatible OmniBrain pour les 100 agents.

        Chaque agent CF100 est exposé avec id, title, specialties,
        skills, provenance, boundaries et brief_template — champs attendus
        par registry/agents.json d'omni-agents-framework.
        """
        if self.cf100 is None:
            raise ValueError("registre CF100 requis pour l'export")
        agents = []
        for spec in self.cf100.agents:
            agents.append({
                "id": spec.id.lower(),
                "title": f"{spec.name} ({spec.division})",
                "specialties": spec.skills,
                "skills": [f"cf100-{s}" for s in spec.skills],
                "provenance": f"cf100 division {spec.division_code} "
                              f"({'dynamic' if spec.dynamic else 'permanent'})",
                "boundaries": (
                    [f"no {d.replace('_', ' ')}"
                     for d in spec.denied_actions]
                    or ["defensive only"]),
                "brief_template": f"Exécuter la mission : {spec.mission}",
            })
        payload = {
            "version": 1,
            "description": ("Cyber Force 100 agents, export au format "
                             "OmniBrain (registry/agents.json)."),
            "agents": agents,
        }
        out = Path(out_path) if out_path is not None else (
            Path(__file__).resolve().parents[2] / "registry" / "exports" /
            "cf100-for-omnibrain.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        return out

    # -- alignement des actions dangereuses ---------------------------------
    def dangerous_action_alignment(self) -> Dict[str, Any]:
        """Compare les listes d'actions dangereuses CF100 vs OmniBrain."""
        import cf100.agents.registry as reg
        cf100 = set(reg.load_policies().get("dangerous_actions", []))
        omni = set(self.omni_dangerous_actions())
        return {
            "common": sorted(cf100 & omni),
            "cf100_only": sorted(cf100 - omni),
            "omni_only": sorted(omni - cf100),
            "aligned": bool(omni) and omni <= cf100,
        }
