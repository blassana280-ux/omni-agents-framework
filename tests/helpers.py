"""Shared fixtures.

``ScriptedProvider`` is an explicit **test double**: it exercises the
orchestrator's control flow deterministically and never touches a model. Any
test using it asserts orchestration logic only. Real provider execution is
covered separately in ``test_executor.py`` against a genuine subprocess.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omni.models import Brief, ProviderResult  # noqa: E402
from omni.registry import Registry  # noqa: E402

REGISTRY_SRC = ROOT / "registry"


def copy_registry(tmp_path: Path, mutate: Optional[Callable[[Path], None]] = None) -> Path:
    dest = Path(tmp_path) / "registry"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(REGISTRY_SRC, dest)
    if mutate:
        mutate(dest)
    return dest


def load_registry(tmp_path: Path, mutate: Optional[Callable[[Path], None]] = None) -> Registry:
    return Registry.load(copy_registry(tmp_path, mutate))


def patch_json(path: Path, fn: Callable[[dict], None]) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class ScriptedProvider:
    """Deterministic in-process test double for :class:`omni.executor.Provider`.

    ``script`` maps an agent id to either a list of responses (consumed in order,
    last one repeated) or a callable taking the brief.
    """

    name = "scripted-double"

    def __init__(
        self,
        script: Optional[Dict[str, Union[List[ProviderResult], Callable[[Brief], ProviderResult]]]] = None,
        *,
        delay: float = 0.0,
        default: Optional[ProviderResult] = None,
    ) -> None:
        self.script = script or {}
        self.delay = delay
        self.default = default
        self.calls: List[Dict[str, object]] = []
        self._cursor: Dict[str, int] = {}

    def available(self):
        return True, "deterministic test double"

    def execute(self, brief: Brief, workdir=None) -> ProviderResult:
        self.calls.append(
            {
                "agent": brief.agent_id,
                "task": brief.task_id,
                "attempt": brief.attempt,
                "missing": list(brief.missing_criteria),
                "tools": list(brief.allowed_tools),
            }
        )
        if self.delay:
            time.sleep(self.delay)
        entry = self.script.get(brief.agent_id)
        if callable(entry):
            return entry(brief)
        if isinstance(entry, list) and entry:
            idx = self._cursor.get(brief.agent_id, 0)
            self._cursor[brief.agent_id] = min(idx + 1, len(entry) - 1)
            return entry[idx]
        if self.default is not None:
            return self.default
        return ProviderResult(
            status="ok",
            summary=f"{brief.agent_id} completed {brief.task_id}",
            evidence=[f"scripted evidence for {brief.task_id}"],
            met_criteria=list(brief.acceptance_criteria),
            executed=True,
            provider=self.name,
        )


def all_ok(registry: Registry, **kwargs) -> ScriptedProvider:
    """Default provider that succeeds everywhere (criteria fully met)."""
    return ScriptedProvider(default=ProviderResult(
        status="ok",
        summary="done",
        evidence=["scripted evidence"],
        executed=True,
        provider="scripted-double",
        met_criteria=[],
    ), **kwargs)


def criteria_provider(registry: Registry, *, skip_first_n: int = 0) -> ScriptedProvider:
    """Provider that returns every acceptance criterion, optionally skipping the
    first N criteria on the first call per agent (to trigger corrections)."""

    def make(brief: Brief) -> ProviderResult:
        met = list(brief.acceptance_criteria)
        if skip_first_n and brief.attempt == 1:
            met = met[skip_first_n:]
        return ProviderResult(
            status="ok",
            summary=f"{brief.agent_id} handled {brief.task_id}",
            evidence=[f"evidence:{brief.task_id}:{brief.attempt}"],
            met_criteria=met,
            executed=True,
            provider="scripted-double",
        )

    return ScriptedProvider()


def failing(agent_id: str, times: int = 99) -> List[ProviderResult]:
    return [
        ProviderResult(status="failed", error=f"{agent_id} exploded", executed=False, provider="scripted-double")
        for _ in range(times)
    ]
