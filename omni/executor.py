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
from dataclasses import dataclass, field
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
        safe_brief = redact(brief.to_text())
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
                fh.write(safe_brief)
                fh.flush()

            prompt = safe_brief
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
    """Native Mistral Chat Completions provider with an explicit paid-inference gate."""

    name: str = "mistral"
    api_key: str = field(default="", repr=False)
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
            model=os.environ.get(
                "OMNI_MISTRAL_MODEL",
                os.environ.get("MISTRAL_MODEL", "mistral-small-latest"),
            ).strip(),
            allow_paid=os.environ.get("OMNI_MISTRAL_ALLOW_PAID", "") == "1",
        )

    def _load_key(self) -> Tuple[str, str]:
        if self.api_key_file is not None:
            fd = -1
            try:
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
                fd = os.open(str(self.api_key_file), flags)
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode):
                    return "", "MISTRAL_API_KEY_FILE must be a regular file"
                if os.name != "nt" and stat.S_IMODE(info.st_mode) & 0o077:
                    return "", "MISTRAL_API_KEY_FILE permissions are too broad; use chmod 600"
                with os.fdopen(fd, "r", encoding="utf-8") as handle:
                    fd = -1
                    key = handle.read(8193).strip()
                if not key or len(key) > 8192:
                    return "", "MISTRAL_API_KEY_FILE is empty or too large"
                return key, "MISTRAL_API_KEY_FILE"
            except (OSError, UnicodeError):
                return "", "MISTRAL_API_KEY_FILE is missing, unreadable, or not private"
            finally:
                if fd >= 0:
                    os.close(fd)

        key = self.api_key.strip()
        return (key, "MISTRAL_API_KEY") if key else ("", "set MISTRAL_API_KEY_FILE or MISTRAL_API_KEY")

    def available(self) -> Tuple[bool, str]:
        key, source = self._load_key()
        if not key:
            return False, source
        gate = (
            "paid inference explicitly enabled"
            if self.allow_paid
            else "paid inference locked (no API request will be sent)"
        )
        return True, f"credential configured via {source}; {gate}"

    @staticmethod
    def _content_text(content: object) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            return "\n".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            ).strip()
        return ""

    @staticmethod
    def _clean(value: object, secret: str) -> object:
        if isinstance(value, str):
            return redact(value.replace(secret, "[REDACTED]"))
        if isinstance(value, list):
            return [MistralProvider._clean(item, secret) for item in value]
        if isinstance(value, dict):
            return {
                MistralProvider._clean(key, secret): MistralProvider._clean(item, secret)
                for key, item in value.items()
            }
        return value

    def execute(self, brief: Brief, workdir: Optional[Path] = None) -> ProviderResult:
        started = time.time()
        key, source = self._load_key()
        if not key:
            return ProviderResult(
                status="failed",
                executed=False,
                provider=self.name,
                error=redact(source),
            )
        if not self.allow_paid:
            return ProviderResult(
                status="pending_human",
                summary=(
                    "Mistral is configured, but paid inference is locked. "
                    "Set OMNI_MISTRAL_ALLOW_PAID=1 only for a run you explicitly authorize."
                ),
                evidence=[f"credential_source={source}", "network_request=not_sent"],
                executed=False,
                provider=self.name,
            )

        system_prompt = (
            "You are a specialist agent in OmniBrain. Return only a JSON object with keys: "
            "summary (string), evidence (array of strings), met_criteria (array of exact acceptance "
            "criterion strings actually satisfied), artifacts (array of strings), and claims (object). "
            "Never claim code was changed, a command was run, a test passed, or an external tool was used "
            "unless the supplied context contains verifiable evidence. If a criterion requires an action "
            "you cannot perform, do not mark it as met; explain the limitation in summary."
        )
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self._clean(brief.to_text(), key)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": self.max_tokens,
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError("Mistral response exceeded 2 MiB")
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Mistral response payload is not an object")
            choices = payload.get("choices") or []
            if not choices or not isinstance(choices[0], dict):
                raise ValueError("Mistral response has no completion choice")
            message = choices[0].get("message", {})
            if not isinstance(message, dict):
                raise ValueError("Mistral response message is invalid")
            content = self._content_text(message.get("content"))
            parsed = json.loads(content) if content else None
            if not isinstance(parsed, dict):
                raise ValueError("Mistral response content is not a JSON object")

            summary = parsed.get("summary", "")
            evidence = parsed.get("evidence", [])
            met = parsed.get("met_criteria", [])
            artifacts = parsed.get("artifacts", [])
            claims = parsed.get("claims", {})
            if not isinstance(summary, str) or not summary.strip():
                raise ValueError("Mistral summary is missing")
            if not isinstance(evidence, list) or not all(isinstance(x, str) for x in evidence):
                raise ValueError("Mistral evidence must be an array of strings")
            if not isinstance(met, list) or not all(isinstance(x, str) for x in met):
                raise ValueError("Mistral met_criteria must be an array of strings")
            if not isinstance(artifacts, list) or not all(isinstance(x, str) for x in artifacts):
                raise ValueError("Mistral artifacts must be an array of strings")
            if not isinstance(claims, dict):
                raise ValueError("Mistral claims must be an object")

            proof = [
                f"mistral_request_id={payload.get('id', 'unreported')}",
                f"model={payload.get('model', self.model)}",
            ]
            usage = payload.get("usage")
            if isinstance(usage, dict):
                for key_name in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    count = usage.get(key_name)
                    if isinstance(count, int) and not isinstance(count, bool):
                        proof.append(f"{key_name}={count}")
            proof.extend(evidence)
            clean = lambda value: self._clean(value, key)
            allowed = set(brief.acceptance_criteria)
            clean_summary = clean(summary.strip())
            clean_content = clean(content)
            return ProviderResult(
                status="ok",
                summary=clean_summary[:4000],
                evidence=clean(proof),
                artifacts=clean(artifacts),
                met_criteria=clean([item for item in met if item in allowed]),
                claims=clean(claims),
                executed=True,
                provider=self.name,
                stdout=clean_content,
                duration_s=time.time() - started,
            )
        except urllib.error.HTTPError as exc:
            reason = {
                401: "authentication failed",
                403: "access denied",
                429: "rate limit or quota reached",
            }.get(exc.code, "request rejected")
            return ProviderResult(
                status="failed",
                executed=False,
                provider=self.name,
                error=f"Mistral API HTTP {exc.code}: {reason}",
                duration_s=time.time() - started,
            )
        except (urllib.error.URLError, TimeoutError, OSError):
            return ProviderResult(
                status="failed",
                executed=False,
                provider=self.name,
                error="Mistral API connection failed or timed out",
                duration_s=time.time() - started,
            )
        except (UnicodeError, json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            return ProviderResult(
                status="incomplete",
                executed=True,
                provider=self.name,
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
