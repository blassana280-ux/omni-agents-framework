"""OmniBrain — the orchestrator of the blassana280-ux agent network.

Public entry points::

    from omni import load_registry, Orchestrator, provider_from_env
    registry = load_registry("registry")
    orch = Orchestrator(registry, provider_from_env()[0], workspace=".")
    record = orch.run("build a REST endpoint and review it")
    print(record.verdict, record.squad)
"""

from pathlib import Path
from typing import Optional

from .executor import ManualProvider, SubprocessProvider, detect_clis, provider_from_env
from .models import Agent, Brief, Classification, Plan, Result, RunRecord, Skill
from .orchestrator import OMNIBRAIN, Orchestrator
from .policy import Policy, PolicyDenied
from .registry import Registry, RegistryError
from .routing import MissingSpecialty, Router
from .validation import ValidationEngine, verdict_for

__version__ = "0.1.0"

DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "registry"


def load_registry(path: Optional[str | Path] = None) -> Registry:
    return Registry.load(path or DEFAULT_REGISTRY)


__all__ = [
    "Agent",
    "Brief",
    "Classification",
    "ManualProvider",
    "MissingSpecialty",
    "OMNIBRAIN",
    "Orchestrator",
    "Plan",
    "Policy",
    "PolicyDenied",
    "Registry",
    "RegistryError",
    "Result",
    "Router",
    "RunRecord",
    "Skill",
    "SubprocessProvider",
    "ValidationEngine",
    "detect_clis",
    "load_registry",
    "provider_from_env",
    "verdict_for",
]
