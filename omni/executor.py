"""Execution providers.

The framework never pretends an agent ran. A run either goes through a provider
that really executed something (``executed=True``), or through
``ManualProvider`` which reports ``pending_human`` and ``executed=False``.

Configured providers are taken from the environment, never from committed
secrets::

    OMNI_PROVIDER_CMD='claude -p {prompt}'        # any local agent CLI
    OMNI_PROVIDER_NAME=claude

Nothing in this module talks to a network API by itself. If you want an API
provider, implement :class:`Provider` in your own (non-committed) module.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import stat
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Sequence, Tuple

from .memory import redact
from .models import Brief, ProviderResult

# Local agent CLIs the network knows how to detect. Detection is a PATH lookup
# only: presence on PATH is reported, absence is reported as unavailable.
KNOWN_CLIS: Dict[str, str] = {
    "claude": "Claude Code CLI",
    "codex": "OpenAI Codex CLI",
    "gemini": "Gemini CLI",
    "kilo": "Kilo Code CLI",
    "kilocode": "Kilo Code CLI",
    "opencode": "OpenCode CLI",
    "cursor-agent": "Cursor agent CLI",
    "aider": "Aider CLI",
    "gh": "GitHub CLI",
}


class Provider(Protocol):
    name: str

    def available(self) -> Tuple[bool, str]: ...

    def execute(self, brief: Brief, workdir: Optional[Path] = None) -> ProviderResult: ...


@dataclass
class SubprocessProvider:
    """Runs a real local command per brief and captures its output.

    ``command`` is a template list; ``{prompt}`` is replaced by the brief text and
    ``{brief_file}`` by a path to a file containing it. The command's exit code
    decides success: 0 -> ok, anything else -> failed.
    """

    command: Sequence[str]
    name: str = "subprocess"
    timeout: int = 1800

    def available(self) -> Tuple[bool, str]:
        if not self.command:
            return False, "empty command template"
        exe = self.command[0]
        path = shutil.which(exe)
        if not path:
            return False, f"executable '{exe}' not found on PATH"
        return True, f"using {path}"

    def execute(self, brief: Brief, workdir: Optional[Path] = None) -> ProviderResult:
        ok, detail = self.available()
        if not ok:
            return ProviderResult(
                status="failed",
                executed=False,
                provider=self.name,
                error=redact(detail),
            )

        workdir = Path(workdir or Path.cwd())
        workdir.mkdir(parents=True, exist_ok=True)
        fd, brief_path = tempfile.mkstemp(
            prefix=".omni-brief-",
            suffix=".md",
            dir=str(workdir),
        )
        brief_file = Path(brief_path)
        open_fd: Optional[int] = fd
        started = time.time()
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                open_fd = None
                if os.name != "nt":
                    os.fchmod(fh.fileno(), 0o600)
                fh.write(brief.to_text())
                fh.flush()

            prompt = brief.to_text()
            argv = [
                str(part).replace("{prompt}", prompt).replace("{brief_file}", str(brief_file))
                for part in self.command
            ]

            try:
                proc = subprocess.run(
                    argv,
                    cwd=str(workdir),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
            except subprocess.TimeoutExpired as exc:
                stdout = exc.stdout or ""
                stderr = exc.stderr or ""
                if isinstance(stdout, bytes):
                    stdout = stdout.decode("utf-8", errors="replace")
                if isinstance(stderr, bytes):
                    stderr = stderr.decode("utf-8", errors="replace")
                stdout = redact(stdout.strip())
                stderr = redact(stderr.strip())
                return ProviderResult(
                    status="failed",
                    executed=False,
                    provider=self.name,
                    error=redact(f"timeout after {self.timeout}s"),
                    summary=stdout[:4000],
                    stdout=stdout,
                    stderr=stderr,
                    duration_s=time.time() - started,
                )
            except OSError as exc:
                return ProviderResult(
                    status="failed",
                    executed=False,
                    provider=self.name,
                    error=redact(str(exc)),
                    duration_s=time.time() - started,
                )

            out = redact((proc.stdout or "").strip())
            err = redact((proc.stderr or "").strip())
            return ProviderResult(
                status="ok" if proc.returncode == 0 else "failed",
                summary=out[:4000],
                evidence=[f"exit_code={proc.returncode}", f"stdout_chars={len(out)}"],
                executed=True,
                provider=self.name,
                error=None if proc.returncode == 0 else redact(f"exit {proc.returncode}: {err[:800]}".strip()),
                stdout=out,
                stderr=err,
                duration_s=time.time() - started,
            )
        finally:
            if open_fd is not None:
                os.close(open_fd)
            try:
                brief_file.unlink()
            except FileNotFoundError:
                pass


@dataclass
class MistralProvider:
    """Native Mistral Chat Completions provider; inference is opt-in per environment."""

    api_key: str = ""
    api_key_file: Optional[Path] = None
    model: str = "mistral-small-latest"
    allow_paid: bool = False
    timeout: int = 120
    max_tokens: int = 1024
    endpoint: str = "https://api.mistral.ai/v1/chat/completions"

    @classmethod
    def from_env(cls) -> "MistralProvider":
        key_file = os.environ.get("MISTRAL_API_KEY_FILE", "").strip()
        return cls(
            api_key=os.environ.get("MISTRAL_API_KEY", "").strip(),
            api_key_file=Path(key_file).expanduser() if key_file else None,
            model=os.environ.get("MISTRAL_MODEL", "mistral-small-latest").strip(),
            allow_paid=os.environ.get("OMNI_MISTRAL_ALLOW_PAID", "") == "1",
        )

    def _load_key(self) -> Tuple[str, str]:
        if self.api_key_file is not None:
            path = self.api_key_file
            try:
                if path.is_symlink() or not path.is_file():
                    return "", "MISTRAL_API_KEY_FILE must point to a regular, non-symlink file"
                mode = stat.S_IMODE(path.stat().st_mode)
                if os.name != "nt" and mode & 0o077:
                    return "", "MISTRAL_API_KEY_FILE permissions are too broad; use chmod 600"
                key = path.read_text(encoding="utf-8").strip()
            except (OSError, UnicodeError):
                return "", "MISTRAL_API_KEY_FILE could not be read"
            return (key, "MISTRAL_API_KEY_FILE") if key else ("", "MISTRAL_API_KEY_FILE is empty")
        key = self.api_key.strip()
        return (key, "MISTRAL_API_KEY") if key else ("", "set MISTRAL_API_KEY_FILE or MISTRAL_API_KEY")

    def available(self) -> Tuple[bool, str]:
        key, source = self._load_key()
        if not key:
            return False, source
        gate = "paid inference explicitly enabled" if self.allow_paid else "paid inference locked (no API request will be sent)"
        return True, f"credential configured via {source}; {gate}"

    def execute(self, brief: Brief, workdir: Optional[Path] = None) -> ProviderResult:
        key, source = self._load_key()
        if not key:
            return ProviderResult(
                status="failed",
                executed=False,
                provider="mistral",
                error=redact(source),
            )
        if not self.allow_paid:
            return ProviderResult(
                status="pending_human",
                summary="Mistral is configured, but paid inference is locked. Set OMNI_MISTRAL_ALLOW_PAID=1 only for a run you explicitly authorize.",
                evidence=[f"credential_source={source}", "network_request=not_sent"],
                executed=False,
                provider="mistral",
            )

        request_body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": brief.to_text()}],
            "max_tokens": self.max_tokens,
            "temperature": 0.2,
        }).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=request_body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(2 * 1024 * 1024)
            payload = json.loads(raw.decode("utf-8"))
            message = payload["choices"][0]["message"]
            answer = message.get("content", "")
            if isinstance(answer, list):
                answer = "\n".join(
                    str(part.get("text", ""))
                    for part in answer
                    if isinstance(part, dict) and part.get("type") == "text"
                )
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("Mistral returned no text content")
            clean = redact(answer).replace(key, "[REDACTED]")
            return ProviderResult(
                status="ok",
                summary=clean[:4000],
                evidence=[f"endpoint={self.endpoint}", f"model={self.model}"],
                executed=True,
                provider="mistral",
                stdout=clean,
                duration_s=time.time() - started,
            )
        except urllib.error.HTTPError as exc:
            return ProviderResult(
                status="failed",
                executed=False,
                provider="mistral",
                error=redact(f"Mistral API returned HTTP {exc.code}"),
                duration_s=time.time() - started,
            )
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError, UnicodeError) as exc:
            detail = "Mistral request failed" if not isinstance(exc, ValueError) else "Mistral response was invalid"
            safe = redact(f"{detail}: {type(exc).__name__}").replace(key, "[REDACTED]")
            return ProviderResult(
                status="failed",
                executed=False,
                provider="mistral",
                error=safe,
                duration_s=time.time() - started,
            )


@dataclass
class ManualProvider:
    """Explicit no-op: hands the brief to a human and says so."""

    name: str = "manual"

    def available(self) -> Tuple[bool, str]:
        return True, "no automated provider configured; briefs are handed to the operator"

    def execute(self, brief: Brief, workdir: Optional[Path] = None) -> ProviderResult:
        return ProviderResult(
            status="pending_human",
            summary=(
                f"No automated provider is configured. Brief for task {brief.task_id} "
                f"({brief.specialty}) is ready for the operator; nothing was executed by an AI agent."
            ),
            evidence=[],
            executed=False,
            provider=self.name,
        )


def detect_clis() -> List[Dict[str, object]]:
    """Truthful PATH probe of the local agent CLIs."""
    found = []
    for cmd, label in KNOWN_CLIS.items():
        path = shutil.which(cmd)
        found.append({"command": cmd, "label": label, "available": bool(path), "path": path or ""})
    return found


def provider_from_env() -> Tuple[Provider, str]:
    """Build the explicitly selected provider, defaulting to an honest manual hand-off."""
    selected = os.environ.get("OMNI_PROVIDER", "").strip().lower()
    if selected == "mistral":
        provider = MistralProvider.from_env()
        ok, detail = provider.available()
        return provider, detail if ok else f"Mistral not ready ({detail})"
    cmd = os.environ.get("OMNI_PROVIDER_CMD", "").strip()
    if not cmd:
        return ManualProvider(), "OMNI_PROVIDER_CMD is not set"
    argv = shlex.split(cmd)
    provider = SubprocessProvider(command=argv, name=os.environ.get("OMNI_PROVIDER_NAME", argv[0]))
    ok, detail = provider.available()
    if not ok:
        return ManualProvider(), f"configured provider unusable ({detail})"
    return provider, detail


def available_provider_names() -> List[str]:
    return [c["command"] for c in detect_clis() if c["available"]]
