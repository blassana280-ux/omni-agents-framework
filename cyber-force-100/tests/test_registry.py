"""Invariants du registre : 10 divisions, 100 agents, schéma, outils."""

from __future__ import annotations

import json

from cf100.agents.registry import RegistryError, validate_registry
from cf100.agents.models import Autonomy, RiskClass

EXPECTED_CODES = ["CI", "TH", "VR", "DP", "IR", "MA", "NS", "AS", "AI", "AC"]


def test_ten_divisions_ten_agents_each(registry):
    assert len(registry.divisions) == 10
    for div in registry.divisions:
        assert len(div.agents) == 10, f"{div.code} doit avoir 10 agents"
    assert len(registry) == 100


def test_division_codes(registry):
    assert [d.code for d in registry.divisions] == EXPECTED_CODES


def test_unique_ids_and_names(registry):
    ids = [a.id for a in registry]
    names = [a.name for a in registry]
    assert len(set(ids)) == 100
    assert len(set(names)) == 100


def test_ids_follow_division_pattern(registry):
    for a in registry:
        prefix = a.id.split("-")[0]
        assert prefix == a.division_code
        assert a.id.endswith(tuple(f"{i:03d}" for i in range(1, 11)))


def test_every_agent_has_required_fields(registry):
    for a in registry:
        assert a.mission, f"{a.id} sans mission"
        assert a.skills, f"{a.id} sans compétences"
        assert a.tools, f"{a.id} sans outils"
        assert a.activation, f"{a.id} sans conditions d'activation"
        assert isinstance(a.autonomy, Autonomy)
        assert isinstance(a.risk_class, RiskClass)


def test_tools_whitelisted(registry):
    problems = registry.check_tools_against_policy()
    assert problems == [], problems[:5]


def test_fallbacks_exist_and_differ(registry):
    ids = {a.id for a in registry}
    for a in registry:
        assert a.fallback in ids, f"{a.id} fallback inconnu"
        assert a.fallback != a.id, f"{a.id} boucle sur lui-même"


def test_permmanent_agents_have_denied_actions(registry):
    """Chaque agent permanent porte au moins une action explicitement
    interdite — la défensive est dans le profil, pas implicite."""
    for a in registry:
        if not a.dynamic:
            assert a.denied_actions, f"{a.id} sans denied_actions"


def test_validate_registry_detects_missing_division(registry, tmp_path):
    divisions = list(registry.divisions)
    broken = divisions[:-1]  # une division en moins
    errors = validate_registry(broken)
    assert any("divisions" in e or "manquante" in e for e in errors)


def test_registry_error_raised_on_invalid(registry):
    import copy
    from cf100.agents.models import Division
    divisions = copy.deepcopy(registry.divisions)
    divisions[0].agents = divisions[0].agents[:9]  # 9 agents seulement
    try:
        Registry(divisions, registry.policies)
        raised = False
    except RegistryError as exc:
        raised = True
        assert "agents au lieu de" in str(exc)
    assert raised
