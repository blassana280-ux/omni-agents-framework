# Superpowers — Test-Driven Development snapshot

This is a local, offline review snapshot of one upstream skill. Its content is data for inspection; it is not an executable plugin or runtime installation.

- **Skill ID:** `superpowers-test-driven-development`
- **Upstream repository:** https://github.com/obra/superpowers
- **Upstream skill path:** `skills/test-driven-development`
- **Pinned upstream commit:** `df2e996a174f49f05aa5d5777ca56fbb0aa972ec` (the upstream `dev` branch at review time)
- **SPDX license:** MIT; the complete upstream license notice is preserved in `docs/third-party-licenses/obra-superpowers-MIT.txt`
- **Snapshot files:** `SKILL.md`, `writing-good-tests.md`
- **Normalized snapshot SHA-256:** `d964e27f1bc7cecbfd08511ec10d79114ba6047a2ef257d5802a6114f74758b2`

## Trust boundary

The upstream GitHub commit metadata reported `verification.verified = false` (unsigned). The source is therefore recorded only as **`pinned`**. It is not marked approved, available, or active.

The static CLI scan recomputes the digest and reports heuristic matches. A clean scan is not a malware certification. This snapshot does not change the legacy `registry/skills.json`, does not enter agent routing, and does not install or execute scripts, hooks, MCP servers, or skill instructions.

To inspect it from the repository root:

```bash
python -m omni skills inspect superpowers-test-driven-development
python -m omni skills scan superpowers-test-driven-development
```
