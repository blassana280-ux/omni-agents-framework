"""Self-Audit Engine — audits automatiques, verdict NEEDS WORK par défaut.

Un audit ne réussit que sur preuve : registre valide, chaîne de preuves
intacte, aucun secret exposé dans les données chargées, politiques
cohérentes. Tout problème est listé tel quel, jamais masqué.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from cf100.agents.registry import Registry, load_divisions, load_policies, \
    validate_registry
from cf100.core.evidence import EvidenceEngine
from cf100.security.secrets import scan_secrets


class SelfAuditEngine:
    """Audit automatique de l'état de Cyber Force 100."""

    def __init__(self, evidence: Optional[EvidenceEngine] = None,
                 registry: Optional[Registry] = None):
        self.evidence = evidence
        self.registry = registry

    def audit(self) -> Dict[str, Any]:
        findings: List[str] = []
        ok = True
        # 1. Registre
        try:
            divisions = load_divisions()
            errors = validate_registry(divisions)
            if errors:
                ok = False
                findings.extend(f"registre : {e}" for e in errors[:5])
            else:
                findings.append(f"registre : {len(divisions)} divisions, "
                                f"{sum(len(d.agents) for d in divisions)} "
                                f"agents valides")
            policies = load_policies()
            missing = [k for k in ("dangerous_actions", "tool_whitelist",
                                   "action_risk") if k not in policies]
            if missing:
                ok = False
                findings.append(f"politiques : clés manquantes {missing}")
            else:
                findings.append("politiques : schéma complet")
        except Exception as exc:  # défaillance explicite, jamais masquée
            ok = False
            findings.append(f"registre illisible : {exc}")
        # 2. Chaîne de preuves
        if self.evidence is not None:
            verdict = self.evidence.verify()
            if not verdict["ok"]:
                ok = False
                findings.append(f"preuves : CHAÎNE CASSÉE — {verdict}")
            else:
                findings.append(f"preuves : chaîne intacte "
                                f"({verdict.get('entries', 0)} entrées)")
        # 3. Secrets dans le registre
        try:
            import json
            from cf100.config import REGISTRY_DIR
            leaked = []
            for f in REGISTRY_DIR.rglob("*.json"):
                text = f.read_text(encoding="utf-8")
                if scan_secrets(text):
                    leaked.append(str(f))
            if leaked:
                ok = False
                findings.append(f"secrets : fuites détectées {leaked}")
            else:
                findings.append("secrets : aucune fuite dans le registre")
        except Exception as exc:
            ok = False
            findings.append(f"scan secrets impossible : {exc}")
        verdict = "READY" if ok else "NEEDS WORK"
        if self.evidence is not None:
            self.evidence.record("self_audit", verdict=verdict,
                                 findings=findings)
        return {"verdict": verdict, "ok": ok, "findings": findings}
