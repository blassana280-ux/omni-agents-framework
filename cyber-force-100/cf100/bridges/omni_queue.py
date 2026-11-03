"""Omni Queue — coordination bidirectionnelle CF100 ↔ OmniBrain.

Protocole sur fichiers JSONL (aucun service externe requis) :

- `omni-inbox.jsonl`   : demandes déposées POUR CF100 (par OmniBrain ou
                         un opérateur) — {id, skill, request, task} ;
- `cf100-outbox.jsonl` : réponses de CF100 — {in_response_to, agent, ok,
                         result} ;
- `omni-done.jsonl`    : accusés de traitement (append-only) — une
                         demande acked n'est plus relue par poll().

Toute demande passe par le Command Core (garde anti-injection + moteurs
de politiques CF100) : un refus est retourné explicitement, jamais masqué.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from cf100.core.command import CommandCore
from cf100.core.evidence import EvidenceEngine


class OmniQueue:
    """File de messages JSONL inbox/outbox avec accusés append-only."""

    def __init__(self, queue_dir: Path):
        self.dir = Path(queue_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.inbox = self.dir / "omni-inbox.jsonl"
        self.outbox = self.dir / "cf100-outbox.jsonl"
        self.done = self.dir / "omni-done.jsonl"

    # -- lecture utilitaire ------------------------------------------------
    @staticmethod
    def _read(path: Path) -> List[Dict[str, Any]]:
        if not path.is_file():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    def _append(self, path: Path, message: Dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(message, ensure_ascii=False) + "\n")

    # -- côté émetteur (OmniBrain / opérateur) -----------------------------
    def submit(self, skill: str, request: str,
               task: Optional[Dict[str, Any]] = None,
               message_id: Optional[str] = None) -> str:
        """Dépose une demande dans la file entrante de CF100."""
        mid = message_id or f"OMNI-{int(time.time() * 1000)}-{skill}"
        self._append(self.inbox, {"id": mid, "skill": skill,
                                   "request": request, "task": task or {}})
        return mid

    # -- côté CF100 ---------------------------------------------------------
    def poll(self) -> List[Dict[str, Any]]:
        """Demandes non encore acquittées (ordre de dépôt)."""
        acked = {m["id"] for m in self._read(self.done)}
        return [m for m in self._read(self.inbox) if m["id"] not in acked]

    def pending(self) -> int:
        return len(self.poll())

    def ack(self, message_id: str) -> None:
        self._append(self.done, {"id": message_id,
                                 "acked_at": time.time()})

    def reply(self, message: Dict[str, Any]) -> None:
        self._append(self.outbox, message)

    def read_replies(self) -> List[Dict[str, Any]]:
        return self._read(self.outbox)


class OmniCoordinator:
    """Traite les demandes de la file via le Command Core CF100."""

    def __init__(self, queue: OmniQueue, core: CommandCore,
                 evidence: Optional[EvidenceEngine] = None,
                 omni_registry_dir: Optional[Path] = None):
        self.queue = queue
        self.core = core
        self.evidence = evidence
        self.omni_registry_dir = (Path(omni_registry_dir)
                                   if omni_registry_dir else None)

    def process_once(self) -> List[Dict[str, Any]]:
        """Traite toutes les demandes en attente, une par une."""
        replies: List[Dict[str, Any]] = []
        for message in self.queue.poll():
            outcome = self.core.handle(
                message.get("request", ""), message.get("skill", ""),
                message.get("task") or {})
            dispatched = outcome.get("outcome") or {}
            reply = {
                "in_response_to": message.get("id"),
                "agent": dispatched.get("agent"),
                "ok": bool(outcome.get("ok")),
                "status": outcome.get("status"),
                "result": outcome,
                "replied_at": time.time(),
            }
            self.queue.reply(reply)
            self.queue.ack(message["id"])
            replies.append(reply)
        if replies and self.evidence is not None:
            self.evidence.record("omni_queue_processed",
                                 messages=len(replies))
        return replies

    def sync(self) -> Dict[str, Any]:
        """Rapport de synchronisation des registres CF100 / OmniBrain."""
        omni_agents: List[Dict[str, Any]] = []
        if self.omni_registry_dir is not None:
            path = self.omni_registry_dir / "agents.json"
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8"))
                omni_agents = list(data.get("agents", []))
        report = {
            "cf100_agents": len(self.core.orchestrator.agents),
            "omni_agents": len(omni_agents),
            "queue_pending": self.queue.pending(),
            "omni_registry_present": bool(omni_agents),
        }
        if self.evidence is not None:
            self.evidence.record("registry_sync", **{
                k: v for k, v in report.items()})
        return report
