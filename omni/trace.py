"""Append-only, secret-redacted trace of orchestrator decisions."""

from __future__ import annotations

import json
import os
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .memory import redact


class Trace:
    def __init__(self, run_id: str, path: Optional[Path] = None) -> None:
        if not isinstance(run_id, str) or not run_id or redact(run_id) != run_id:
            raise ValueError("run_id must be a non-empty string without credential-like data")
        self.run_id = run_id
        self.path = Path(path) if path else None
        self.events: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.is_symlink():
                raise ValueError("trace path must not be a symbolic link")
            fd = os.open(self.path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
            try:
                if os.name != "nt":
                    os.fchmod(fd, 0o600)
            finally:
                os.close(fd)

    def emit(self, event: str, **fields: Any) -> Dict[str, Any]:
        record = redact({
            "ts": round(time.time(), 6),
            "run_id": self.run_id,
            "event": event,
            **fields,
        })
        # Normalize non-JSON values through the same redactor before either
        # retaining the event in memory or appending it to the trace file.
        serialized = json.dumps(
            record,
            ensure_ascii=False,
            default=lambda value: redact(str(value)),
        )
        safe_record = json.loads(serialized)
        line = json.dumps(safe_record, ensure_ascii=False) + "\n"
        with self._lock:
            self.events.append(safe_record)
            if self.path:
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
        return safe_record

    # ------------------------------------------------------------ queries
    def of_type(self, event: str) -> List[Dict[str, Any]]:
        return [e for e in self.events if e["event"] == event]

    def agents_seen(self) -> List[str]:
        seen: List[str] = []
        for event in self.of_type("dispatch"):
            aid = event.get("agent")
            if aid and aid not in seen:
                seen.append(aid)
        return seen

    def tools_seen(self) -> List[str]:
        tools: List[str] = []
        for event in self.of_type("policy"):
            tool = event.get("action")
            if tool and tool not in tools:
                tools.append(tool)
        return tools

    def to_dict(self) -> Dict[str, Any]:
        return {"run_id": self.run_id, "path": str(self.path) if self.path else None, "events": self.events}
