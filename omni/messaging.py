"""Agent-to-agent messaging.

A file-backed mailbox, scoped to a run. Messages are append-only JSONL so the
conversation between agents is auditable after the fact. Unknown senders or
recipients are rejected: the bus only carries traffic between declared agents.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class Message:
    run_id: str
    sender: str
    recipient: str
    subject: str
    body: str
    kind: str = "info"  # info | question | answer | correction | arbitration
    payload: Optional[Dict[str, Any]] = None
    ts: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ts"] = self.ts or time.time()
        return d


class UnknownAgent(LookupError):
    pass


class MessageBus:
    def __init__(self, path: str | Path, run_id: str, known_agents: Set[str]) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self.known_agents = set(known_agents)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def _validate(self, agent_id: str, role: str) -> None:
        if agent_id not in self.known_agents:
            raise UnknownAgent(f"{role} '{agent_id}' is not a declared agent")

    def send(self, message: Message) -> Message:
        self._validate(message.sender, "sender")
        self._validate(message.recipient, "recipient")
        if message.run_id != self.run_id:
            raise ValueError("message run_id does not match the bus run")
        message.ts = message.ts or time.time()
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")
        return message

    def all(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            if msg.get("run_id") == self.run_id:
                out.append(msg)
        return out

    def inbox(self, agent_id: str) -> List[Dict[str, Any]]:
        self._validate(agent_id, "recipient")
        return [m for m in self.all() if m["recipient"] == agent_id]

    def outbox(self, agent_id: str) -> List[Dict[str, Any]]:
        self._validate(agent_id, "sender")
        return [m for m in self.all() if m["sender"] == agent_id]
