"""Controlled shared memory.

Design constraints:

* an agent can always write to its own namespace inside a run;
* writing to the *shared* namespace requires an explicit grant;
* values are scanned for credential-looking strings and redacted before they are
  ever persisted;
* entries can expire (TTL) so a stale run cannot poison the network later.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

SECRET_PATTERNS = [
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9\-_]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*[\"']?[^\s\"']{8,}"),
]


def redact(value: Any) -> Any:
    """Recursively redact credential-looking strings."""
    if isinstance(value, str):
        out = value
        for pattern in SECRET_PATTERNS:
            out = pattern.sub("[REDACTED]", out)
        return out
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


class MemoryDenied(PermissionError):
    pass


class SharedMemory:
    """File-backed key/value store with per-agent ownership rules."""

    def __init__(self, path: str | Path, run_id: str, writable_shared: Optional[List[str]] = None) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self.writable_shared = set(writable_shared or [])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"entries": {}}), encoding="utf-8")
        self._lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    # ------------------------------------------------------------- plumbing
    def _load(self) -> Dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return {"entries": {}}

    def _store(self, data: Dict[str, Any]) -> None:
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".mem-")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    @staticmethod
    def _key(scope: str, key: str) -> str:
        return f"{scope}::{key}"

    # ---------------------------------------------------------------- write
    def write(self, scope: str, key: str, value: Any, owner: str, ttl_s: Optional[int] = None) -> str:
        if scope == "shared" and owner not in self.writable_shared:
            raise MemoryDenied(f"agent '{owner}' is not granted writes to shared memory")
        stamped = int(time.time()) + ttl_s if ttl_s else None
        data = self._load()
        data["entries"][self._key(scope, key)] = {
            "value": redact(value),
            "owner": owner,
            "run_id": self.run_id,
            "written_at": time.time(),
            "expires_at": stamped,
        }
        self._store(data)
        return self._key(scope, key)

    # ----------------------------------------------------------------- read
    def get(self, scope: str, key: str) -> Optional[Any]:
        entry = self._load()["entries"].get(self._key(scope, key))
        if not entry:
            return None
        if entry.get("expires_at") and entry["expires_at"] < time.time():
            return None
        return entry["value"]

    def search(self, term: str, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        hits = []
        now = time.time()
        for full_key, entry in self._load()["entries"].items():
            if scope and not full_key.startswith(f"{scope}::"):
                continue
            if entry.get("expires_at") and entry["expires_at"] < now:
                continue
            if term.lower() in json.dumps(entry["value"], ensure_ascii=False).lower():
                hits.append({"key": full_key, **entry})
        return hits

    def purge_expired(self) -> int:
        data = self._load()
        now = time.time()
        before = len(data["entries"])
        data["entries"] = {
            k: v
            for k, v in data["entries"].items()
            if not (v.get("expires_at") and v["expires_at"] < now)
        }
        self._store(data)
        return before - len(data["entries"])
