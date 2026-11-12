# OmniBrain SUPREME — external systems review

**Review date:** 2026-11-09  
**Branch:** `omnibrain/skills-catalog-plan-v1`  
**Purpose:** record integration decisions from the current ecosystem review. This document is research evidence, not a claim that the reviewed projects have been installed or activated.

## Decisions at a glance

| Source | Decision | Reason |
|---|---|---|
| [Adaptive Task Routing for Gemini CLI](https://github.com/zyzdev/adaptive-task-routing-gemini) | **Keep as a design reference; do not import as-is.** | MIT, but its runtime and packaging are built around Gemini CLI and host-specific model/context controls. |
| [NVIDIA Agent Skills](https://github.com/NVIDIA/skills) | **Use governance ideas; do not copy CC-BY skill content under the current policy.** | NVIDIA's source code is Apache-2.0, while its skills and documentation are CC-BY-4.0. OmniBrain currently admits MIT and Apache-2.0 only. |
| [ECC](https://github.com/affaan-m/ECC) | **Curated snapshots already added to the trust catalog.** | Four MIT-licensed skills were selected; no runtime, scripts, hooks, MCP server, package, or binary was imported. See `docs/skills/ECC-SELECTED-SKILLS.md`. |
| [Agent Consent Patterns](https://github.com/mrchaarlie/agent-consent-patterns) | **Pinned reference already added to the trust catalog.** | MIT-licensed guidance for scoped grants, action approval, revocation, identity, receipts, and interruption. |
| [Zuora Coding Agent](https://github.com/zuora/zuora-coding-agent) | **Do not add to OmniBrain core.** | It is focused on Zuora-specific billing APIs and workflows, not a general-purpose agent runtime or reusable orchestration layer. |
| [AgentBroko ChatGPT plugin](https://chatgpt.com/plugins/plugins_6a99d0b00e28819184ae0cb4675e01a8) | **Keep as an optional media-tool reference; do not import into the core yet.** | The ChatGPT listing describes reusable video, audio, PDF, caption and social-export skills, version 1.4.6, from Broke Innovation. An npm listing also identifies an `agentbroko` 1.4.6 package as MIT, but a canonical source repository and the exact portable skill files were not verified in this review. |
| [Skill Submission Pack Writer](https://chatgpt.com/plugins?category=developer-tools) | **Treat as a ChatGPT plugin listing, not a portable source skill.** | The directory listing identifies a BEIKE YAN submission-materials plugin. A separate MIT community skill, `submission-pack-builder`, has now been pinned from Plugin Autopilot; it is not the same product. |
| Qlynk Agent Builder | **Do not add to the core.** | The supplied name does not identify a verified portable open-source runtime in this review. A hosted/no-code builder would not become an OmniBrain execution capability merely by linking it. |
| 22 Skills | **Out of scope for the agent registry.** | The connected product is a résumé/job-posting match workflow, not a general-purpose agent-skill source. |


## AgentBroko and submission preparation: clarified identities

**AgentBroko** is identifiable as a ChatGPT plugin published by Broke Innovation. Its listing describes reusable workflows for video production/editing, audio mixing, captions, PDF handling, thumbnails, and social exports; the listed version is 1.4.6. A package index also lists an `agentbroko` npm package at 1.4.6 under MIT. However, this review did not establish a canonical GitHub source repository or verify the exact package contents. Keep it as an optional multimedia tool reference, not as an imported agent runtime. Do not claim its local FFmpeg/video workflows are available in OmniBrain until the actual source, dependencies and Android/host compatibility are validated.

**Skill Submission Pack Writer** is a ChatGPT Directory plugin listing from BEIKE YAN for writing submission materials. It is not itself the open-source portable skill. The related `submission-pack-builder` from `imMamdouhaboammar/chatgpt-codex-plugin-autopilot` has been added separately as a MIT-licensed, pinned text snapshot with its two supporting reference files. These names and products must not be conflated.

## Adaptive routing: concepts worth adapting

Upstream reference: `zyzdev/adaptive-task-routing-gemini`, commit `90f18cadaef3038701265cc961b90dd56a43a8dd` (MIT).

The upstream design separates three distinct decisions:
1. **Context:** continue in the current conversation, hand off a focused context, or start clean.
2. **Model/reasoning:** retain the observed setup or propose a justified change for the next phase.
3. **Execution routing:** select the OmniBrain specialist and the approved skills needed for the task.

Transferable principles:
- Evaluate routing at meaningful phase boundaries, not after every short exchange.
- Keeping the current setup is a valid outcome when it is sufficient.
- Account for context continuity and switching costs; do not recommend a change on model name alone.
- Unknown runtime capability must remain unknown until observed.
- Ask before changing settings unless a supported, authorized, verifiable operation was explicitly enabled.
- Do not claim a model/context change was applied until the host confirms it.
- A routing recommendation or plan does not grant permission to implement the proposed work.
- Keep an explicit deterministic fallback when adaptive metadata or a provider probe is unavailable.

**OmniBrain mapping:** the existing `omni/routing.py` remains the deterministic specialty/agent router. The future native resolver belongs in `omni/adaptive_routing.py` as described in the SUPREME architecture specification. It must resolve agent, skill, and provider/model separately, filter by trust state and permissions before relevance ranking, and verify provider availability through the actual provider interface. The Gemini extension, its `GEMINI.md`, Gemini-specific runtime projection, and host model-selection assumptions are not portable implementation files for this Python repository.

**Status:** design guidance only. No adaptive model switcher or context handoff engine is implemented by this research note.

## NVIDIA governance: ideas worth evaluating

Upstream reference: `NVIDIA/skills`, commit `fce3cca4170be75e82c64920654d56ee2811b005`.

NVIDIA describes a stronger publication gate than a content hash alone: source ownership, security scanning for software and agent-native risks, task-based evaluation, a skill card describing ownership/dependencies/limitations, and detached cryptographic signatures. OmniBrain's current catalog already pins source commits and SHA-256 content digests, performs heuristic static scans, and requires human approval bound to the exact digest.

Useful future work:
- Add a structured skill card schema for owner, intended use, exclusions, dependencies, runtime assumptions, licence, evaluator version and evidence.
- Add deterministic task evaluations and retain per-commit results; compare the same agent/task with and without a skill.
- Evaluate detached signing and trusted publisher identities as a later trust tier.
- Keep scanner findings, benchmark results and signatures separate from runtime permission enforcement.

**Licence boundary:** the NVIDIA repository states that source code is Apache-2.0 while skills/documentation are CC-BY-4.0. Do not copy or redistribute skill text into the current MIT/Apache-only catalog unless the policy is deliberately updated and attribution requirements are met. A link to the upstream catalog and lessons from its governance process are safe research references; they are not an imported NVIDIA skill.

## Implementation gap confirmed in the current OmniBrain runtime

The existing router is deterministic and selects specialties from configured keyword triggers and weights. The orchestration layer provides parallel task waves, provider results, correction/retry handling, validation gates, trace events and file-backed shared memory. It does **not** yet provide:
- adaptive scoring based on measured agent quality, latency or cost;
- a first-class resolver that chooses only approved skills for each brief;
- a provider/model selector driven by verified live capability probes and a configured budget;
- cross-harness context handoff;
- an Agent Factory that proposes profiles and tests without activating them.

These are future implementation targets, not capabilities delivered by this source review. The existing deterministic router and manual provider must remain truthful fallbacks until each feature is implemented and tested.

## Source integrity and scope

The ECC and Agent Consent entries in the trust catalog are pinned to exact upstream commits, content digests and MIT licence declarations. Their current lifecycle status is `pinned`, not `approved`, `available` or `active`. This document does not grant permission to execute upstream scripts, install dependencies, contact paid providers, or broaden the OmniBrain permission policy.
