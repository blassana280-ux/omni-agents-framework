# Vercel React Best Practices — intake review

- Upstream: https://github.com/vercel-labs/agent-skills
- Pinned commit: `1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62` (2026-10-27)
- Skill path: `skills/react-best-practices`
- Declared license: MIT in the individual `SKILL.md` frontmatter.
- License evidence caveat: no repository-root `LICENSE` file was found at the pinned commit. The catalogue records the per-skill MIT declaration; this should be confirmed upstream before any broader redistribution or promotion.
- Snapshot: `registry/snapshots/vercel-react-best-practices/`
- Digest: `47004bbcfb90686bde66784f09e300da201e7957812f5bf523a2f54edffeed5f`
- Contents: original `SKILL.md` plus the complete compiled `AGENTS.md` reference (70 rules across eight categories).

## Value for OmniBrain

Adds framework-specific engineering guidance for React and Next.js: eliminating async waterfalls, reducing bundle size, server-side performance, client data fetching, render optimization, rendering performance, JavaScript performance, and advanced patterns. It complements rather than replaces the existing general frontend engineering and performance skills.

## Compatibility and safety

- The imported files are documentation only; no JavaScript scripts, hooks, plugins, or package dependencies are included.
- The guide does not change OmniBrain's Python standard-library-only runtime, router, provider, permissions, or historical skill registry.
- The same five static pattern classes used by the current catalogue scanner were checked against both imported files; no matches were found.
- The record remains `pinned`, disabled and unassigned. It is not executable by OmniBrain and is not automatically selected for agents.
- `AGENTS.md` is the complete compiled guide, so the individual per-rule Markdown files are not required in this snapshot.

## Intake decision

Accept as a pinned documentation snapshot pending confirmation of the per-skill MIT licensing evidence and separate human review. Do not promote or activate automatically.
