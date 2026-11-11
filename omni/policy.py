"""Tool and permission enforcement.

Two hard rules live here:

* an agent only sees the tools its profile is allowed to use;
* irreversible account-level actions (merge, force-push, delete, secret rotation)
  always require an explicit human confirmation token.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional

DEFAULT_DANGEROUS = [
    "merge_pr",
    "force_push",
    "delete_repo",
    "delete_branch",
    "rotate_secret",
    "write_main",
]


@dataclass
class Decision:
    allowed: bool
    reason: str
    requires_confirmation: bool = False


class PolicyDenied(PermissionError):
    pass


class Policy:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config or {}
        self.defaults = self.config.get("defaults", {})
        self.agents = self.config.get("agents", {})
        self.dangerous = set(self.config.get("dangerous_actions", DEFAULT_DANGEROUS))

    # ------------------------------------------------------------ helpers
    def allowed_tools(self, agent_id: str) -> List[str]:
        entry = self.agents.get(agent_id, {})
        return list(entry.get("allowed_tools", self.defaults.get("allowed_tools", [])))

    def max_parallel(self, agent_id: str) -> int:
        return int(
            self.agents.get(agent_id, {}).get(
                "max_parallel", self.defaults.get("max_parallel", 1)
            )
        )

    @staticmethod
    def _normalize_resource(resource: str) -> str:
        """Normalize an untrusted relative path before applying path boundaries."""
        if not isinstance(resource, str) or not resource:
            raise ValueError("resource path must be non-empty text")
        if (
            "\x00" in resource
            or "\\" in resource
            or resource.startswith("/")
            or re.match(r"^[A-Za-z]:", resource)
        ):
            raise ValueError("resource path is absolute or ambiguous")
        parts = resource.split("/")
        if any(part == ".." for part in parts):
            raise ValueError("resource path traversal is not allowed")
        normalized = [part for part in parts if part not in ("", ".")]
        if not normalized:
            raise ValueError("resource path must identify a file")
        return "/".join(normalized).casefold()

    @classmethod
    def _matches_path_rule(cls, resource: str, prefix: str) -> bool:
        """Match file prefixes on path-component boundaries where appropriate."""
        if not isinstance(prefix, str) or not prefix:
            raise ValueError("path-rule prefix must be non-empty text")
        directory_rule = prefix.endswith("/")
        normalized_prefix = cls._normalize_resource(prefix.rstrip("/"))
        if directory_rule:
            return resource == normalized_prefix or resource.startswith(normalized_prefix + "/")
        # Preserve the existing .env* protection while preventing case bypasses.
        return resource.startswith(normalized_prefix)

    # ------------------------------------------------------------- checks
    def check(
        self,
        agent_id: str,
        action: str,
        resource: Optional[str] = None,
        confirmed: bool = False,
    ) -> Decision:
        entry = self.agents.get(agent_id)
        if entry is None:
            return Decision(False, f"agent '{agent_id}' is not declared in permissions.json")

        if action in self.dangerous and not self.defaults.get("allow_dangerous", False):
            if not confirmed:
                return Decision(
                    False,
                    f"action '{action}' is irreversible and requires explicit human confirmation",
                    requires_confirmation=True,
                )

        # Deny rules win over the blanket grant: a path rule is a hard boundary.
        rules = entry.get("path_rules", [])
        matching_rules = [rule for rule in rules if rule.get("action") == action]
        normalized_resource = resource
        if resource is not None and matching_rules:
            try:
                normalized_resource = self._normalize_resource(resource)
            except ValueError as exc:
                return Decision(False, f"path rule rejects '{action}' on ambiguous resource: {exc}")

        if normalized_resource is not None:
            for rule in matching_rules:
                deny_prefix = rule.get("deny_prefix")
                if deny_prefix:
                    try:
                        denied = self._matches_path_rule(normalized_resource, deny_prefix)
                    except ValueError:
                        return Decision(False, f"path rule for '{action}' is malformed")
                    if denied:
                        return Decision(False, f"path rule denies '{action}' on '{resource}'")

        if action in self.allowed_tools(agent_id):
            if normalized_resource is not None:
                for rule in matching_rules:
                    prefix = rule.get("prefix")
                    if prefix:
                        try:
                            granted = self._matches_path_rule(normalized_resource, prefix)
                        except ValueError:
                            return Decision(False, f"path rule for '{action}' is malformed")
                        if granted:
                            return Decision(True, f"path rule grants '{action}' on '{resource}'")
            return Decision(True, f"'{action}' is granted to '{agent_id}'")

        return Decision(False, f"'{action}' is not granted to '{agent_id}'")

    def require(self, agent_id: str, action: str, resource: Optional[str] = None, confirmed: bool = False) -> None:
        decision = self.check(agent_id, action, resource, confirmed)
        if not decision.allowed:
            raise PolicyDenied(f"{agent_id}: {decision.reason}")
