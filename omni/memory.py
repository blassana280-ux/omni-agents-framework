"""Controlled, file-backed shared memory.

Design constraints:
* agents may write to their own run namespace;
* shared writes require an explicit grant;
* credential-looking values are redacted before persistence;
* updates are atomic and serialized across threads and processes;
* malformed state fails closed instead of being silently replaced.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

SECRET_PATTERNS = [
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9\-_]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"""(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*["']?[^\s"']{8,}"""),
]


def redact(value: Any) -> Any:
    """Recursively redact credential-looking strings, including mapping keys."""
    if isinstance(value, str):
        out = value
        for pattern in SECRET_PATTERNS:
            out = pattern.sub("[REDACTED]", out)
        return out
    if isinstance(value, dict):
        return {
            redact(key) if isinstance(key, str) else key: redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class MemoryDenied(PermissionError):
    """Raised when an agent attempts a memory write without a grant."""


class MemoryStorageError(RuntimeError):
    """Raised when the memory file or its locking mechanism is unavailable."""


class MemoryCorruptionError(MemoryStorageError):
    """Raised when persisted memory is malformed; the original file is preserved."""


_PATH_LOCKS: Dict[str, threading.RLock] = {}
_PATH_LOCKS_GUARD = threading.Lock()


def _thread_lock(path: Path) -> threading.RLock:
    """Return one process-local lock for each canonical lock-file path."""
    key = str(path.resolve())
    with _PATH_LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(key, threading.RLock())


class SharedMemory:
    """File-backed key/value store with per-agent ownership and safe updates."""

    def __init__(
        self,
        path: str | Path,
        run_id: str,
        writable_shared: Optional[List[str]] = None,
    ) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self.writable_shared = set(writable_shared or [])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.path.with_suffix(self.path.suffix + ".lock")

        # Initialization is itself a transaction: two first-run processes must
        # not race to create/truncate the same store.
        with self._exclusive_lock():
            if self.path.is_symlink():
                raise MemoryStorageError("memory path must not be a symbolic link")
            if not self.path.exists():
                self._store({"entries": {}})
            elif os.name != "nt":
                os.chmod(self.path, 0o600)
            self._load()  # validate existing state before accepting writes

    @contextmanager
    def _exclusive_lock(self) -> Iterator[None]:
        """Serialize read/modify/write transactions across threads and processes."""
        if self._lock_path.is_symlink():
            raise MemoryStorageError("memory lock path must not be a symbolic link")

        with _thread_lock(self._lock_path):
            try:
                lock_file = self._lock_path.open("a+b")
            except OSError as exc:
                raise MemoryStorageError(f"cannot open memory lock: {exc}") from exc

            with lock_file:
                if os.name == "nt":
                    import msvcrt

                    lock_file.seek(0, os.SEEK_END)
                    if lock_file.tell() == 0:
                        lock_file.write(b"x")
                        lock_file.flush()
                    lock_file.seek(0)
                    try:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                    except OSError as exc:
                        raise MemoryStorageError(f"cannot lock memory store: {exc}") from exc
                    try:
                        yield
                    finally:
                        lock_file.seek(0)
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    try:
                        import fcntl
                    except ImportError as exc:  # pragma: no cover - unusual Python platform
                        raise MemoryStorageError("cross-process file locking is unavailable") from exc

                    try:
                        os.chmod(self._lock_path, 0o600)
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    except OSError as exc:
                        raise MemoryStorageError(f"cannot lock memory store: {exc}") from exc
                    try:
                        yield
                    finally:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    # ------------------------------------------------------------- plumbing
    def _load(self) -> Dict[str, Any]:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {"entries": {}}
        except OSError as exc:
            raise MemoryStorageError(f"cannot read memory store: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MemoryCorruptionError(
                f"memory store contains invalid JSON at line {exc.lineno}, column {exc.colno}"
            ) from exc

        if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
            raise MemoryCorruptionError("memory store must be an object with an entries object")
        if any(not isinstance(entry, dict) for entry in data["entries"].values()):
            raise MemoryCorruptionError("memory store contains a malformed entry")
        return data

    def _store(self, data: Dict[str, Any]) -> None:
        """Durably replace the store; a failed write leaves the old file intact."""
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".mem-")
        open_fd: Optional[int] = fd
        try:
            if os.name != "nt":
                os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                open_fd = None
                json.dump(data, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())

            os.replace(tmp, self.path)
            if os.name != "nt":
                directory_fd = os.open(
                    str(self.path.parent),
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
                )
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        finally:
            if open_fd is not None:
                os.close(open_fd)
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass

    @staticmethod
    def _key(scope: str, key: str) -> str:
        return f"{scope}::{key}"

    @staticmethod
    def _validate_address(scope: str, key: str, owner: str) -> None:
        if not isinstance(scope, str) or not scope or "::" in scope:
            raise ValueError("scope must be a non-empty string without '::'")
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty string")
        if not isinstance(owner, str) or not owner:
            raise ValueError("owner must be a non-empty string")
        address = f"{scope}::{key}"
        if redact(address) != address or redact(owner) != owner:
            raise ValueError("memory address/owner must not contain credential-like data")

    # ---------------------------------------------------------------- write
    def write(
        self,
        scope: str,
        key: str,
        value: Any,
        owner: str,
        ttl_s: Optional[int] = None,
    ) -> str:
        self._validate_address(scope, key, owner)
        if scope == "shared" and owner not in self.writable_shared:
            raise MemoryDenied(f"agent '{owner}' is not granted writes to shared memory")
        if ttl_s is not None and (
            isinstance(ttl_s, bool) or not isinstance(ttl_s, int) or ttl_s <= 0
        ):
            raise ValueError("ttl_s must be a positive integer or None")

        full_key = self._key(scope, key)
        now = time.time()
        entry = {
            "value": redact(value),
            "owner": owner,
            "run_id": self.run_id,
            "written_at": now,
            "expires_at": now + ttl_s if ttl_s is not None else None,
        }
        with self._exclusive_lock():
            data = self._load()
            data["entries"][full_key] = entry
            self._store(data)
        return full_key

    # ----------------------------------------------------------------- read
    def get(self, scope: str, key: str) -> Optional[Any]:
        entry = self._load()["entries"].get(self._key(scope, key))
        if not entry:
            return None
        expires_at = entry.get("expires_at")
        if expires_at is not None and expires_at < time.time():
            return None
        return entry["value"]

    def search(self, term: str, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        hits = []
        now = time.time()
        for full_key, entry in self._load()["entries"].items():
            if scope and not full_key.startswith(f"{scope}::"):
                continue
            expires_at = entry.get("expires_at")
            if expires_at is not None and expires_at < now:
                continue
            if term.lower() in json.dumps(entry["value"], ensure_ascii=False).lower():
                hits.append({"key": full_key, **entry})
        return hits

    def purge_expired(self) -> int:
        with self._exclusive_lock():
            data = self._load()
            now = time.time()
            before = len(data["entries"])
            data["entries"] = {
                key: entry
                for key, entry in data["entries"].items()
                if entry.get("expires_at") is None or entry["expires_at"] >= now
            }
            removed = before - len(data["entries"])
            if removed:
                self._store(data)
            return removed
