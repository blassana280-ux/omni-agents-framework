"""Tool and permission enforcement.

Two hard rules live here:

* an agent only sees the tools its profile is allowed to use;
* irreversible account-level actions (merge, force-push, delete, secret rotation)
  always require an explicit human confirmation token.
"""

from __future__ import annotations

from dataclasses import dataclass
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
        if resource:
            for rule in rules:
                deny_prefix = rule.get("deny_prefix")
                if rule.get("action") == action and deny_prefix and resource.startswith(deny_prefix):
                    return Decision(False, f"path rule denies '{action}' on '{resource}'")

        if action in self.allowed_tools(agent_id):
            if resource:
                for rule in rules:
                    if rule.get("action") == action and resource.startswith(rule.get("prefix", "\0")):
                        return Decision(True, f"path rule grants '{action}' on '{resource}'")
            return Decision(True, f"'{action}' is granted to '{agent_id}'")

        return Decision(False, f"'{action}' is not granted to '{agent_id}'")

    def require(self, agent_id: str, action: str, resource: Optional[str] = None, confirmed: bool = False) -> None:
        decision = self.check(agent_id, action, resource, confirmed)
        if not decision.allowed:
            raise PolicyDenied(f"{agent_id}: {decision.reason}")
