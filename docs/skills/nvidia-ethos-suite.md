# NVIDIA ETHOS skill suite

OmniBrain records three complementary skills from the upstream [NVIDIA/skills](https://github.com/NVIDIA/skills) repository.

## Pinned entries

| Skill | Purpose | Runtime snapshot |
| --- | --- | --- |
| `ethos-orchestrate` | Route requests through the ETHOS workflow | `SKILL.md` |
| `ethos-explore` | Inspect an agent and clarify intent, constraints, and success criteria | `SKILL.md` |
| `ethos-write` | Draft and validate an `ETHOS.md` from confirmed intent | `SKILL.md`, `references/templates/ethos.md`, `scripts/validate_ethos.py` |

- Upstream repository: https://github.com/NVIDIA/skills
- Pinned commit: `03ea0b0e3599cfebbdf9b40dd9ed12fa764c9f75`
- Declared license for these skill files: Apache-2.0
- Maintainer: NVIDIA Corporation
- Trust state: `pinned` only; not approved, available, or active.

## Provenance and quality evidence

Each upstream skill directory contains a `skill-card.md`, `skill.oms.sig`, `evals/evals.json`, and `BENCHMARK.md`. The benchmark reports a PASS publication recommendation for each skill. These artifacts are retained upstream and are not copied into OmniBrain's runtime snapshot.

The signature artifacts are present, but this integration has **not** performed cryptographic signature verification. The benchmark reports are upstream evidence, not a guarantee of performance in OmniBrain.

## Safety boundary

The registry pins exact upstream commits and SHA-256 digests for the runtime files listed above. A preliminary static scan of those files found no matches for OmniBrain's current high/critical blocking rules. This is a heuristic scan, not a malware certification.

The skills remain in the external catalog at `pinned` state. They are not copied into the legacy active skills registry, executed, or automatically assigned to agents. Promotion requires the normal ingestion, scan, evaluation, and explicit human-approval workflow.
