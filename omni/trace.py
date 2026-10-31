"""Append-only trace of everything the orchestrator did.

Traceability requirement: every agent selection, tool decision, provider call,
result, correction and arbitration lands in one JSONL file per run.
"""

from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


class Trace:
    def __init__(self, run_id: str, path: Optional[Path] = None) -> None:
        self.run_id = run_id
        self.path = Path(path) if path else None
        self.events: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("", encoding="utf-8")

    def emit(self, event: str, **fields: Any) -> Dict[str, Any]:
        record = {
            "ts": round(time.time(), 6),
            "run_id": self.run_id,
            "event": event,
            **fields,
        }
        with self._lock:
            self.events.append(record)
            if self.path:
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return record

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
