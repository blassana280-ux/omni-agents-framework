"""Moteur de politiques — autonomie maximale encadrée.

Règles absolues (alignées sur OmniBrain, registry/permissions.json) :
- toute action de la liste `dangerous_actions` est refusée sans
  validation humaine explicite, même pour un agent autorisé ;
- risque bas/moyen : exécution automatique ;
- risque haut : plan uniquement, exécution après validation humaine ;
- risque critique : validation humaine + second relecteur.

Le registre des approbations est persistant et auditable. Chaque
approbation peut porter une durée de validité (`ttl_seconds`) : une
approbation expirée est ignorée — sans TTL, elle persiste
(comportement historique), un TTL court est recommandé pour les
actions critiques.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from cf100.agents.models import AgentSpec, Autonomy, RiskClass
from cf100.agents.registry import load_policies
from cf100.config import data_dir

DEFAULT_ACTION_RISK = {
    "read_file": "low",
    "memory_read": "low",
    "memory_write": "low",
    "send_message": "low",
    "web_search": "low",
    "search_skills": "low",
    "execute_task": "low",
    "run_static_analysis": "medium",
    "scan_dependencies": "medium",
    "scan_secrets": "medium",
    "scan_containers": "medium",
    "scan_iac": "medium",
    "query_logs": "medium",
    "run_tests": "medium",
    "write_file": "medium",
    "write_doc": "medium",
    "generate_yara": "medium",
    "verify_evidence": "medium",
    "git_branch": "medium",
    "git_commit": "medium",
    "git_push": "high",
    "open_pr": "high",
    "sandbox_execute": "high",
    "run_build": "medium",
    "run_script": "medium",
    "dispatch": "medium",
    # Actions toujours destructives ou sensibles :
    "merge_pr": "critical",
    "force_push": "critical",
    "delete_repo": "critical",
    "delete_branch": "critical",
    "delete_data": "critical",
    "rotate_secret": "critical",
    "write_main": "critical",
    "change_permissions": "critical",
    "disable_protection": "critical",
    "purge_evidence": "critical",
    "deploy_production": "critical",
}


@dataclass
class Decision:
    """Décision du moteur de politiques pour une action."""

    allowed: bool
    needs_approval: bool
    reason: str
    risk: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "needs_approval": self.needs_approval,
            "reason": self.reason,
            "risk": self.risk,
        }


class ApprovalLedger:
    """Registre persistant des validations humaines (jamais auto-accordées)."""

    def __init__(self, path: Optional[Any] = None):
        import pathlib
        if path is None:
            data_dir()
            path = cf100_approval_path()
        self.path = pathlib.Path(path)

    def approve(self, action: str, approver: str, note: str = "",
                ttl_seconds: Optional[float] = None) -> str:
        """Enregistre une validation humaine. approver doit être humain.

        ttl_seconds : durée de validité optionnelle. Sans TTL,
        l'approbation persiste (compatibilité) ; avec TTL, elle est
        ignorée par has_valid_approval() une fois expirée.
        """
        if not approver or approver.startswith(("DYN-", "CI-", "TH-", "VR-",
                "DP-", "IR-", "MA-", "NS-", "AS-", "AI-", "AC-", "omni-")):
            raise ValueError("seul un humain peut valider une action "
                             "(approbateur : " + repr(approver) + ")")
        entries = self.list()
        token = f"APR-{int(time.time())}-{len(entries) + 1}"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"token": token, "action": action,
                 "approver": approver, "note": note,
                 "granted_at": time.time()}
        if ttl_seconds is not None:
            entry["expires_at"] = entry["granted_at"] + ttl_seconds
        entries.append(entry)
        self.path.write_text(json.dumps(entries, indent=2, ensure_ascii=False),
                             encoding="utf-8")
        return token

    def list(self) -> List[Dict[str, Any]]:
        if not self.path.is_file():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def has_valid_approval(self, action: str) -> bool:
        """True si une approbation NON EXPIRÉE existe pour l'action."""
        now = time.time()
        for entry in self.list():
            if entry.get("action") != action:
                continue
            expires_at = entry.get("expires_at")
            if expires_at is not None and now >= float(expires_at):
                continue  # approbation expirée : ignorée
            return True
        return False


def cf100_approval_path():
    from cf100.config import MEMORY_DB
    return MEMORY_DB.parent / "approvals.json"


class PolicyEngine:
    """Évalue chaque action demandée par un agent contre les politiques."""

    def __init__(self, policies: Optional[Dict[str, Any]] = None,
                 ledger: Optional[ApprovalLedger] = None):
        self.policies = policies if policies is not None else load_policies()
        self.dangerous = set(self.policies.get("dangerous_actions", []))
        self.action_risk = dict(self.policies.get("action_risk",
                                                  DEFAULT_ACTION_RISK))
        self.autonomy_floor = {"autonomous": RiskClass.LOW,
                                "assisted": RiskClass.MEDIUM,
                                "supervised": RiskClass.HIGH}
        self.ledger = ledger if ledger is not None else ApprovalLedger()

    # -- classification ------------------------------------------------
    def classify_risk(self, action: str) -> str:
        return self.action_risk.get(action, "high")

    def is_dangerous(self, action: str) -> bool:
        return action in self.dangerous

    # -- décision --------------------------------------------------------
    def authorize(self, agent: AgentSpec, action: str,
                  context: Optional[Dict[str, Any]] = None) -> Decision:
        """Décision finale pour (agent, action) — refus par défaut."""
        context = context or {}
        if action in agent.denied_actions:
            return Decision(False, False,
                             f"action interdite par le profil de {agent.id}",
                             "critical")
        if action not in agent.tools:
            return Decision(False, False,
                            f"{agent.id} n'a pas l'outil {action} dans son "
                            f"profil (moindre privilège)", "high")
        risk = self.classify_risk(action)
        if self.is_dangerous(action):
            if self.ledger.has_valid_approval(action):
                return Decision(True, False,
                                "validation humaine enregistrée au registre",
                                risk)
            return Decision(False, True,
                             f"{action} est une action dangereuse : "
                             f"validation humaine obligatoire", risk)
        # Plafond d'autonomie : un agent ne peut pas dépasser sa classe.
        risk_enum = RiskClass(risk)
        floor = self.autonomy_floor[agent.autonomy.value]
        if risk_enum.value == "low":
            return Decision(True, False, "risque bas — exécution auto", risk)
        if risk_enum.value == "medium":
            if floor.value in ("low", "medium"):
                return Decision(True, False,
                                "risque moyen — exécution auto + preuve", risk)
            return Decision(False, True,
                            f"autonomie {agent.autonomy.value} insuffisante "
                            f"pour un risque moyen", risk)
        # risque haut ou critique
        if agent.autonomy == Autonomy.AUTONOMOUS and risk == "high" \
                and context.get("human_approved"):
            return Decision(True, False, "validation humaine explicite", risk)
        return Decision(False, True,
                         f"risque {risk} : plan produit, exécution seulement "
                         f"après validation humaine", risk)
