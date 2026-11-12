# Selected engineering skills from Addy Osmani

OmniBrain pins five complementary skills from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills).

- Upstream commit: `301b02b12bff98e4688e6984af6556802322bbde`
- Upstream repository license: MIT
- Full license text: [`docs/third-party-licenses/addyosmani-agent-skills-MIT.txt`](../third-party-licenses/addyosmani-agent-skills-MIT.txt)
- Trust state: all five entries are `pinned`; none is active or automatically assigned.
- Snapshot policy: only the selected `SKILL.md` files and the performance reference are copied. No upstream scripts, hooks, commands, plugin manifests, or runtime dependencies are installed.

## Selected skills

| Skill | Main contribution |
| --- | --- |
| `api-and-interface-design` | Contract-first API and module boundary design, compatibility, and error semantics |
| `doubt-driven-development` | Fresh-context adversarial review of assumptions and implementation claims |
| `frontend-ui-engineering` | Accessible, responsive, production-quality frontend implementation |
| `observability-and-instrumentation` | Structured logging, metrics, tracing, and operational evidence |
| `performance-optimization` | Measurement-led optimization across application layers and database queries |

## Static review and exclusions

The selected snapshots were checked against the current OmniBrain static rules. No configured high/critical blocking matches were found. This is a heuristic scan, not a security certification, and the skills have not been activated or executed.

Two candidates were held back for a separate review:
- `source-driven-development`: the prompt-injection heuristic matches a literal adversarial example quoted in its guidance about treating fetched documentation as untrusted data.
- `security-and-hardening`: the secret-access heuristic matches defensive examples that read environment variables and search staged diffs for secret-like strings.

Neither candidate was silently allowlisted. A later change should improve rule precision and add explicit regression tests before reconsidering them.

All selected entries remain external snapshots with pinned provenance and content digests. Promotion still requires the existing trust lifecycle and explicit human approval.
