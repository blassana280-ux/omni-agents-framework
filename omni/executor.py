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

import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Sequence, Tuple

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
                error=detail,
            )

        workdir = Path(workdir or Path.cwd())
        brief_file = workdir / f".omni-brief-{brief.task_id}.md"
        brief_file.write_text(brief.to_text(), encoding="utf-8")
        prompt = brief.to_text()
        argv = [str(part).replace("{prompt}", prompt).replace("{brief_file}", str(brief_file)) for part in self.command]

        started = time.time()
        try:
            proc = subprocess.run(
                argv,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return ProviderResult(
                status="failed",
                executed=False,
                provider=self.name,
                error=f"timeout after {self.timeout}s",
                stdout=(exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                duration_s=time.time() - started,
            )
        except OSError as exc:
            return ProviderResult(status="failed", executed=False, provider=self.name, error=str(exc))

        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return ProviderResult(
            status="ok" if proc.returncode == 0 else "failed",
            summary=out[:4000],
            evidence=[f"exit_code={proc.returncode}", f"stdout_chars={len(out)}"],
            executed=True,
            provider=self.name,
            error=None if proc.returncode == 0 else f"exit {proc.returncode}: {err[:800]}".strip(),
            stdout=out,
            stderr=err,
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
    """Build the configured provider, defaulting to an honest manual hand-off."""
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
