"""Agent-to-agent messaging.

A file-backed mailbox, scoped to a run. Messages are append-only JSONL so the
conversation between agents is auditable after the fact. Unknown senders or
recipients are rejected. Secret-looking content is redacted before it reaches
disk or the in-memory inbox/outbox.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .memory import redact


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
    """Run-scoped JSONL mailbox with thread-safe, redacted persistence."""

    ALLOWED_KINDS = frozenset({"info", "question", "answer", "correction", "arbitration"})

    def __init__(self, path: str | Path, run_id: str, known_agents: Set[str]) -> None:
        if not isinstance(run_id, str) or not run_id or redact(run_id) != run_id:
            raise ValueError("run_id must be a non-empty string without credential-like data")
        self.path = Path(path)
        self.run_id = run_id
        self.known_agents = set(known_agents)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise ValueError("message bus path must not be a symbolic link")
        flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY
        fd = os.open(self.path, flags, 0o600)
        try:
            if os.name != "nt":
                os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        self._lock = threading.Lock()

    def _validate(self, agent_id: str, role: str) -> None:
        if agent_id not in self.known_agents:
            raise UnknownAgent(f"{role} '{agent_id}' is not a declared agent")

    def send(self, message: Message) -> Message:
        self._validate(message.sender, "sender")
        self._validate(message.recipient, "recipient")
        if message.run_id != self.run_id:
            raise ValueError("message run_id does not match the bus run")
        if message.kind not in self.ALLOWED_KINDS:
            raise ValueError(f"unsupported message kind: {message.kind!r}")

        # Redact the object itself so callers cannot accidentally reuse an
        # unsanitized message after it has crossed the persistence boundary.
        message.subject = redact(message.subject)
        message.body = redact(message.body)
        message.payload = redact(message.payload) if message.payload is not None else None
        message.ts = message.ts or time.time()
        line = json.dumps(message.to_dict(), ensure_ascii=False) + "\n"
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()
        return message

    def all(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            if msg.get("run_id") == self.run_id:
                # Also protect consumers reading legacy files created before
                # write-time redaction was introduced.
                out.append(redact(msg))
        return out

    def inbox(self, agent_id: str) -> List[Dict[str, Any]]:
        self._validate(agent_id, "recipient")
        return [m for m in self.all() if m["recipient"] == agent_id]

    def outbox(self, agent_id: str) -> List[Dict[str, Any]]:
        self._validate(agent_id, "sender")
        return [m for m in self.all() if m["sender"] == agent_id]
