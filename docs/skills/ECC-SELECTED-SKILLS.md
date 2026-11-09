# ECC — selected external skill snapshots

**Upstream:** https://github.com/affaan-m/ECC  
**Pinned source commit:** `d2ef2680594f9a17526a6e1a2e18b3d242c5d17b`  
**License:** MIT (verified from the upstream `LICENSE` at that commit).

These are curated, text-only snapshots. No ECC package, hook, script, MCP server, agent runtime, binary, or installer is copied or executed. All records remain `pinned`; none is automatically approved or activated.

| Skill | OmniBrain use | Integration boundary |
|---|---|---|
| `ecc-agent-eval` | Evidence-based comparison of agent/model variants using pass rate, cost, latency, and consistency. | The upstream skill describes a runner; no ECC evaluation executable is included. A native OmniBrain evaluator must be designed and tested before activation. |
| `ecc-agent-security-hardening` | Trust boundaries, input validation, filesystem containment, credential handling, output limits, and enforcement tests. | Guidance only; runtime enforcement remains in OmniBrain policy/tool boundaries. |
| `ecc-agent-architecture-audit` | Diagnose hidden agent layers, memory contamination, tool discipline, retries, and rendering/transport regressions. | Audit playbook only; findings must be supported by code and tests. |
| `ecc-team-agent-orchestration` | Work ownership, scope, Kanban state, branch isolation, evidence, and merge gates for agent squads. | The ECC Control Pane is not included; use OmniBrain's own trace/registry until a native UI exists. |

## Trust and activation

The snapshots are immutable references tied to the upstream commit and a per-skill SHA-256 digest. They remain unapproved and cannot be treated as executable capabilities. Run the catalog's ingestion, static scan, and evaluation workflow, review any referenced external prerequisites, and require human approval bound to the exact digest before an individual skill can become available.
