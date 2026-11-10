"""Execution providers.

The framework never pretends an agent ran. A run either goes through a provider
that really executed something (``executed=True``), or through
``ManualProvider`` which reports ``pending_human`` and ``executed=False``.

Configured providers are taken from the environment, never from committed
secrets::

    OMNI_PROVIDER_CMD='claude -p {prompt}'        # any local agent CLI
    OMNI_PROVIDER_NAME=claude

The optional Mistral provider makes one explicit Chat Completions API request per task. It reads credentials from a private key file and never verifies configuration by sending a request.
"""

from __future__ import annotations

import json
import os
import shlex
import stat
import shutil
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
class MistralAPIProvider:
    """Mistral Chat Completions provider backed by a private key file."""

    model: str = "mistral-small-latest"
    timeout: int = 120
    max_tokens: int = 2048
    name: str = "mistral"
    endpoint: str = "https://api.mistral.ai/v1/chat/completions"

    def _read_api_key(self) -> str:
        configured = os.environ.get("MISTRAL_API_KEY_FILE", "").strip()
        if not configured:
            raise ValueError("MISTRAL_API_KEY_FILE is not set")
        path = Path(configured).expanduser()
        fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("Mistral key path must be a regular file")
            if os.name != "nt" and stat.S_IMODE(info.st_mode) & 0o077:
                raise ValueError("Mistral key file permissions must be 0600 or stricter")
            with os.fdopen(fd, "r", encoding="utf-8") as handle:
                fd = -1
                key = handle.read(8193).strip()
            if not key or len(key) > 8192:
                raise ValueError("Mistral key file is empty or too large")
            return key
        finally:
            if fd >= 0:
                os.close(fd)

    def available(self) -> Tuple[bool, str]:
        try:
            self._read_api_key()
        except (OSError, UnicodeError, ValueError):
            return False, "Mistral key file is missing, unreadable, or not private"
        return True, "private Mistral key file is ready; no API request was sent"

    @staticmethod
    def _content_text(content: object) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            ]
            return "\n".join(parts).strip()
        return ""

    def execute(self, brief: Brief, workdir: Optional[Path] = None) -> ProviderResult:
        started = time.time()
        try:
            api_key = self._read_api_key()
        except (OSError, UnicodeError, ValueError):
            return ProviderResult(
                status="failed", executed=False, provider=self.name,
                error="Mistral is not configured with a readable private key file",
            )

        system_prompt = (
            "You are a specialist agent in the OmniBrain orchestration system. "
            "Return only one JSON object with keys: summary (string), evidence (array of strings), "
            "met_criteria (array of exact acceptance-criterion strings actually satisfied by this response), "
            "artifacts (array of strings), and claims (object). "
            "Never claim that code was changed, a command was run, a test passed, or an external tool "
            "was used unless the supplied context contains verifiable evidence. If a criterion requires "
            "an action you cannot perform, do not mark it as met and explain the limitation in summary."
        )
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": brief.to_text()},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": self.max_tokens,
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError("response too large")
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("response payload is not an object")
            choices = payload.get("choices") or []
            message = choices[0].get("message", {}) if choices else {}
            content = self._content_text(message.get("content"))
            parsed = json.loads(content) if content else None
            if not isinstance(parsed, dict):
                raise ValueError("response is not a JSON object")

            summary = parsed.get("summary", "")
            if not isinstance(summary, str) or not summary.strip():
                raise ValueError("response summary is missing")
            allowed = set(brief.acceptance_criteria)
            met = parsed.get("met_criteria", [])
            evidence = parsed.get("evidence", [])
            artifacts = parsed.get("artifacts", [])
            claims = parsed.get("claims", {})
            if not isinstance(met, list) or not all(isinstance(x, str) for x in met):
                raise ValueError("met_criteria must be an array of strings")
            if not isinstance(evidence, list) or not all(isinstance(x, str) for x in evidence):
                raise ValueError("evidence must be an array of strings")
            if not isinstance(artifacts, list) or not all(isinstance(x, str) for x in artifacts):
                raise ValueError("artifacts must be an array of strings")
            if not isinstance(claims, dict):
                raise ValueError("claims must be an object")

            proof = [
                f"mistral_request_id={payload.get('id', 'unreported')}",
                f"model={payload.get('model', self.model)}",
            ]
            proof.extend(evidence)
            return ProviderResult(
                status="ok",
                summary=redact(summary.strip())[:4000],
                evidence=redact(proof),
                artifacts=redact(artifacts),
                met_criteria=[item for item in met if item in allowed],
                claims=redact(claims),
                executed=True,
                provider=self.name,
                stdout=redact(content),
                duration_s=time.time() - started,
            )
        except urllib.error.HTTPError as exc:
            reason = {
                401: "authentication failed",
                403: "access denied",
                429: "rate limit or quota reached",
            }.get(exc.code, "request rejected")
            return ProviderResult(
                status="failed", executed=False, provider=self.name,
                error=f"Mistral API HTTP {exc.code}: {reason}",
                duration_s=time.time() - started,
            )
        except (urllib.error.URLError, TimeoutError):
            return ProviderResult(
                status="failed", executed=False, provider=self.name,
                error="Mistral API connection failed or timed out",
                duration_s=time.time() - started,
            )
        except (UnicodeError, json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            return ProviderResult(
                status="incomplete", executed=True, provider=self.name,
                error="Mistral response did not satisfy the expected JSON contract",
                evidence=[f"model={self.model}"],
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
    """Build the explicitly selected provider, otherwise an honest manual hand-off."""
    selected = os.environ.get("OMNI_PROVIDER", "").strip().lower()
    if selected == "mistral":
        provider = MistralAPIProvider(model=os.environ.get("OMNI_MISTRAL_MODEL", "mistral-small-latest"))
        ok, detail = provider.available()
        return (provider, detail) if ok else (ManualProvider(), f"Mistral selected but unavailable ({detail})")
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
