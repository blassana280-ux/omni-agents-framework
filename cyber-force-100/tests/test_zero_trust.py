"""Zero Trust : identité vérifiée, refus par défaut, moindre privilège."""

from __future__ import annotations

import pytest

from cf100.security.zero_trust import (IdentityError, Principal,
                                       authenticate, authorize_scope)

HUMAN_IDS = {"lassana": "secret-partage-hors-depot"}


def test_human_authenticated_via_directory():
    principal = authenticate("lassana", token=HUMAN_IDS["lassana"],
                             human_ids=HUMAN_IDS)
    assert principal.kind == "human"
    assert principal.token_valid


def test_human_wrong_secret_rejected():
    # l'identifiant seul ne suffit jamais : le secret doit correspondre
    with pytest.raises(IdentityError):
        authenticate("lassana", token="mauvais-secret", human_ids=HUMAN_IDS)


def test_human_without_secret_rejected():
    # refus par défaut : pas de secret présenté, pas d'authentification
    with pytest.raises(IdentityError):
        authenticate("lassana", human_ids=HUMAN_IDS)


def test_agent_authenticated_via_registry(registry):
    principal = authenticate("CI-001", registry=registry)
    assert principal.kind == "agent"
    assert principal.attributes["division"] == "CI"


def test_unknown_principal_rejected(registry):
    with pytest.raises(IdentityError):
        authenticate("XX-999", registry=registry)


def test_agent_without_registry_untrusted():
    principal = authenticate("CI-001")  # pas de registre fourni
    assert principal.token_valid is False


def test_scope_default_deny():
    untrusted = Principal("CI-001", "agent", False, 0.0)
    assert not authorize_scope(untrusted, "intel:read", ["intel:read"])


def test_scope_least_privilege():
    trusted = Principal("CI-001", "agent", True, 0.0)
    assert authorize_scope(trusted, "intel:read", ["intel:read"])
    assert not authorize_scope(trusted, "identity:write", ["intel:read"])


def test_human_full_scope():
    human = Principal("lassana", "human", True, 0.0)
    assert authorize_scope(human, "intel:read", [])
