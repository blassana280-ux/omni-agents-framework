# Context and harness engineering skill set

OmniBrain pins six complementary skills from the MIT-licensed repository [muratcankoylan/agent-skills-for-context-engineering](https://github.com/muratcankoylan/agent-skills-for-context-engineering).

## Pinned skills

| Skill | Main contribution |
| --- | --- |
| `harness-engineering` | Autonomy boundaries, durable logs, rollback, approval gates, and PR-producing harnesses |
| `multi-agent-patterns` | Context isolation, supervisor/swarm patterns, handoffs, and parallel work |
| `memory-systems` | Persistent semantic memory, entity/temporal tracking, and memory architecture |
| `self-improvement-loops` | Bounded self-improvement, failure mining, and safe optimization of the harness |
| `tool-design` | Agent-facing tool contracts, schemas, descriptions, and error recovery |
| `context-compression` | Durable handoffs and context compression that preserves decisions, files, risks, and next actions |

- Upstream commit: `9ff0c99108b36d3b886defd825d8ac1f47dba374`
- Repository license: MIT
- Trust state for all entries: `pinned`; none is active or automatically assigned.
- Snapshots include each skill's `SKILL.md` and the referenced runtime resources/scripts listed in the lock digest.

## Static review

The selected runtime snapshots were reviewed with OmniBrain's preliminary static patterns. No high/critical blocking matches were found in these six skills. This heuristic scan is not a security certification, and the bundled scripts have not been executed.

Two candidates were deliberately not admitted in this pass:
- `hosted-agents` was held back because its infrastructure reference contains a high-severity environment-secret access pattern and shell-execution examples that need a separate review.
- `advanced-evaluation` was deferred to avoid adding another evaluation skill before the existing ECC evaluation skill has been compared for overlap.

The repository remains an external source; these entries do not modify the legacy active skills registry. Promotion still requires the standard snapshot scan, evaluation, and explicit human approval.
