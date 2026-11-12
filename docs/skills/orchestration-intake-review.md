# Orchestration intake review: RUG and Gem Team

**Review date:** 2026-11-10  
**Review scope:** documentation and agent-definition intake only; no upstream code execution  
**Decision:** do not import either candidate as a runnable OmniBrain skill or agent in this change.

## Executive decision

| Candidate | Pinned source | License evidence | Intake result |
|---|---|---|---|
| RUG orchestrator | `github/awesome-copilot` commit `227949a7542a55d2155c00e7cdb998d9a0fee4f3`, `agents/rug-orchestrator.agent.md` | Repository root MIT license | Reject direct import; useful concepts are already represented in OmniBrain and its pinned skills, while its tool contract is VS Code-specific |
| Gem Team orchestrator | `mubaidr/gem-team` commit `49ab1a142b3b926e84df493985654d21623111ad`, `.apm/agents/gem-orchestrator.agent.md` | Repository `LICENSE`: Apache-2.0 | Defer direct import; potentially useful workflow ideas, but it is part of a larger APM-managed harness and contains material policy conflicts |

No source files, scripts, packages, hooks, runtime dependencies, or agent definitions were copied into OmniBrain. No registry, route, permission, provider, executor, or lifecycle state was changed.

## 1. RUG orchestrator

### Source and behavior inspected

- Source file: `agents/rug-orchestrator.agent.md`.
- Pinned upstream commit: `227949a7542a55d2155c00e7cdb998d9a0fee4f3`.
- Repository root license: MIT.
- Defines a manager-only orchestrator that decomposes tasks, creates a todo list, delegates all work to subagents, launches a separate validator, retries failed work, and performs a final integration validation.

### Compatibility findings

1. **Tool contract mismatch:** the definition requires VS Code-specific `runSubagent` and `manage_todo_list` and names `vscode`, `execute`, `read`, `agent`, `edit`, `search`, `web`, and `todo` tools. OmniBrain's current runtime is a Python 3.11 standard-library orchestrator with its own provider, policy, message bus, and validation contracts; these tool names are not a portable runtime interface.
2. **Over-delegation:** it mandates delegation even for small tasks and forbids the orchestrator from reading or searching directly. This is a rigid context-management preference, not a generally safe execution contract.
3. **Existing overlap:** OmniBrain already has parallel wave dispatch, retries/fallback/escalation, correction loops, traceability, and explicit validation gates. Its pinned catalog also already contains dispatching-parallel-agents and multi-agent-patterns guidance.
4. **No executable integration:** importing this prompt would not create subagents or provide the VS Code tools it assumes.

### Decision

**Reject direct import.** Reconsider only individual, runtime-neutral practices if a concrete gap is demonstrated by a test. Do not add an agent profile or claim that RUG is executable in OmniBrain.

## 2. Gem Team

### Source and behavior inspected

- Orchestrator: `.apm/agents/gem-orchestrator.agent.md`.
- Knowledge/memory model: `docs/src/content/2.guide/2.core-concepts.md`.
- Pinned upstream commit: `49ab1a142b3b926e84df493985654d21623111ad`.
- Repository `LICENSE`: Apache-2.0.
- The project describes a broader harness with APM-managed agent definitions, planner/reviewer/specialist roles, ordered waves, persistent plans, typed handoffs, memory tiers, and model-routing configuration.

### Potentially valuable ideas

- Stable typed handoff contracts and role-scoped configuration snapshots.
- Explicit plan IDs and resumable task state separated from durable project knowledge.
- Bounded retry/failure categories and evidence references rather than oversized handoff payloads.
- Promotion of durable learnings only after successful completion and a confidence threshold.
- Cost-aware prompt-prefix stability and scoped parallelism.

These are candidate design ideas, not evidence that the full Gem Team runtime can be dropped into OmniBrain.

### Compatibility and safety findings

1. **Harness dependency:** the orchestrator is designed around Gem Team's named specialists, APM layout, configuration, plan artifacts, and payload schema. It is not a standalone portable skill. The README's installation path requires APM and generates harness-specific files.
2. **Verification-policy conflict:** Gem Team's orchestrator says to trust specialist outputs and never re-verify completed work. OmniBrain's current design deliberately checks evidence through validation gates, arbitrates contradictions, and runs correction loops. Removing those gates would weaken an existing safety invariant.
3. **Approval-policy conflict:** the inspected orchestrator says not to pause for approval and to proceed immediately except for blockers. OmniBrain's controlled-autonomy policy must remain authoritative for consequential or irreversible actions.
4. **Memory-policy mismatch:** Gem Team's repo/session/global memory tiers and 30-day TTL are interesting, but OmniBrain already has run-scoped shared memory with secret redaction and TTL. A user-global memory tier must not be introduced by copying a prompt; it needs explicit storage, privacy, retention, deletion, and access-control design.
5. **Model-routing assumptions:** premium/explore tiers and provider choices depend on Gem Team configuration. They cannot be assumed to map to OmniBrain's real provider capabilities or the user's available models.
6. **Scope and licensing:** Apache-2.0 is compatible with the current allowlist, but license compatibility alone does not establish architectural compatibility or justify importing the wider harness.

### Decision

**Defer direct import.** Do not copy the orchestrator or its agent pack. If a future implementation is justified, extract only narrowly scoped, runtime-neutral handoff or resumable-plan concepts, write an OmniBrain-native specification, preserve independent validation and approval gates, and add tests before changing runtime behavior.

## 3. Existing OmniBrain capabilities considered

The current repository README documents tested support for:

- deterministic task classification and squad/wave planning;
- real parallel dispatch;
- retry, fallback, escalation, arbitration, and correction loops;
- run JSON/JSONL traceability and shared verdicts;
- controlled shared memory with secret redaction and TTL;
- run-scoped agent messaging and a permission model;
- external skill provenance, lock digests, local static scanning, and an explicit human-approval lifecycle.

The external skill catalog already pins `ecc-team-agent-orchestration`, `multi-agent-patterns`, `memory-systems`, `ethos-orchestrate`, and `agent-architecture`. The intake bar is therefore additive value demonstrated against these existing capabilities, not feature count.

## 4. Follow-up gates

Before any future extraction or runtime change:

1. Identify a concrete unmet requirement in OmniBrain and a test that currently fails or is missing.
2. Specify the minimal OmniBrain-native behavior and its trust/approval boundary.
3. Map every proposed handoff field, memory scope, retry rule, and provider capability to existing contracts.
4. Preserve independent validation, evidence requirements, secret redaction, and human approval for consequential actions.
5. Add deterministic offline tests and verify the complete CI suite.
6. Keep any imported source pinned, licensed, hashed, scanned, reviewed, and disabled until explicit human approval.

**Final status:** both candidates reviewed; neither imported or activated. This is an intake decision, not a claim that the broader OmniBrain upgrade is complete.
