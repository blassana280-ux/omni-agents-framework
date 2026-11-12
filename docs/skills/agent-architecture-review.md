# Agent Architecture — intake review

## Source and provenance

- Upstream repository: https://github.com/github/awesome-copilot
- Pinned upstream commit: `227949a7542a55d2155c00e7cdb998d9a0fee4f3` (2026-11-10)
- Skill path: `skills/agent-architecture/`
- Per-skill license: MIT, supplied as `LICENSE.txt`; copyright holder: Stanislav Bankovskii
- Upstream contribution history: commit `9bf465b455f10d22971f94de8f40bf97947195d1`, PR #3015
- Snapshot: 16 files (the skill, 13 references, license, and inert OpenAI UI metadata)
- Content size: 167,360 characters; all files are text

## Value for OmniBrain

The skill provides a disciplined architecture-design and audit method: requirements discovery, evidence and decision tracking, trust/data boundaries, separation of model/skill/tool/runtime/human responsibilities, evaluation contracts, validation loops, and long-running task continuity (checkpoints, recovery, budgets, escalation queues, and scheduling).

It complements the existing `ecc-agent-architecture-audit`, `harness-engineering`, and `multi-agent-patterns` material. Its main differentiator is the end-to-end design workflow and detailed execution-continuity contract, not generic advice to use multiple agents.

## Compatibility and security review

- All 16 snapshot files are Markdown or YAML; no scripts, hooks, binaries, or runtime dependencies are included.
- All relative Markdown references resolve within the pinned snapshot.
- The five static scan rule patterns currently used by OmniBrain (`destructive-command`, `shell-execution`, `network-upload`, `secret-access`, and `prompt-injection`) produced no matches in the reviewed files.
- No router, provider, permission, executor, or active-skill behavior is changed.
- `agents/openai.yaml` is platform-specific display metadata and is retained as inert source material; it is not executed by OmniBrain.
- The skill's `result-delivery.md` defaults to producing a PDF and diagram. OmniBrain must not claim to have created these artifacts unless its actual tools produce them; adapt this contract before activation.
- The skill is design/audit guidance, not an autonomous runtime agent. It remains pinned and disabled, with no human approval record and no automatic assignment.

## Intake decision

Accept as a pinned, documentation-only snapshot for later human review. Keep it disabled and unassigned. Before activation, adapt the PDF/diagram delivery requirement to supported OmniBrain outputs and evaluate its interview workflow against representative tasks. No scanner rule or trust policy was weakened.
