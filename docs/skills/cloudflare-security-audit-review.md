# Cloudflare Security Audit — intake review

- Upstream: https://github.com/cloudflare/security-audit-skill
- Pinned commit: `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`
- License: MIT; notice preserved in `docs/third-party-licenses/cloudflare-security-audit-MIT.txt`.
- Snapshot: `registry/snapshots/cloudflare-security-audit/`.
- Status: pinned, review-required, disabled; not assigned to agents and not automatically executed.

## Value for OmniBrain

Provides a structured security-review workflow: reconnaissance, coverage planning, parallel vulnerability hunting, independent validation, and evidence-based reporting. Its AI/LLM guidance explicitly covers prompt injection, tool argument injection, MCP trust boundaries, memory provenance, delegated authority, and confused-deputy risks.

## Safety and compatibility assessment

The upstream workflow is deliberately strict: source inspection is read-only; target-controlled execution is allowed only inside an OS-enforced sandbox with resource limits, isolated scratch space, and no ambient credentials or network dependency installation. If those controls are unavailable, execution must not proceed and the result must be marked as needing validation.

The snapshot includes Node.js `.cjs` validators and their tests. OmniBrain's core runtime is Python standard-library-only, so these validators are preserved as upstream reference material and are not wired into the core or executed by the agent router. A future native adapter requires a separately reviewed design and tests. No imported script is granted shell, network, secret, or repository-write authority.

## Intake decision

Keep as a pinned, disabled skill snapshot pending a native compatibility adapter and independent validation. This PR does not enable the skill, change agent permissions, modify routing, or activate imported code.
