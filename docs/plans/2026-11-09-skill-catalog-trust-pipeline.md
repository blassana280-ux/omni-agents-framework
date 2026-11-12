# OmniBrain SUPREME — Skill Catalog & Trust Pipeline Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe, auditable, offline-first catalog for external agent skills without changing OmniBrain's existing public contracts or executing untrusted skill content.

**Architecture:** Keep the current Python 3.11 standard-library core and the existing `Skill` / `Registry` contracts. Add a separate catalog layer for pinned source metadata, provenance, validation, scanning and lifecycle state. Only skills explicitly approved by a human may become eligible for task-level selection; discovery and scanning never execute skill instructions or scripts.

**Tech Stack:** Python 3.11 standard library, JSON registries, unittest, existing `python3 -m omni` CLI.

## Global Constraints

- Never write directly to `main` or `master`; work only on a dedicated branch and use a PR.
- Preserve `omni.models.Skill`, `Registry.load()`, `Registry.validate()`, `Registry.search_skills()`, `Router.classify()`, `Router.select_agent()` and `Router.plan()`.
- Preserve the existing four registry files and backward compatibility for current `registry/skills.json` entries.
- Do not add third-party runtime dependencies or require a PC, local daemon, paid API, or paid inference.
- Do not execute external skill scripts, hooks, MCP servers, or instructions during discovery, ingestion, validation, or scanning.
- Pin external sources by immutable commit SHA and content digest; a moving branch name alone is insufficient.
- A discovered, fetched, scanned, or evaluated skill is not approved. Human approval is a separate explicit transition.
- No automatic fork creation, merge, permission change, or irreversible action.
- Never claim a skill is safe merely because static checks pass; report exactly which checks ran.
- Preserve honest provider semantics: no simulated agent execution and no READY verdict without real execution evidence.

---

### Task 1: Add a versioned skill-source and trust metadata contract

**Files:**
- Create: `registry/skill-sources.json`
- Create: `registry/skills.lock.json`
- Create: `omni/skill_catalog.py`
- Create: `tests/test_skill_catalog.py`
- Read-only compatibility boundary: `omni/models.py`, `omni/registry.py`

**Interfaces:**
- Consumes: existing `Skill` fields (`id`, `title`, `source`, `specialties`, `verification`, `notes`).
- Produces: `SkillSource`, `SkillTrustRecord`, `SkillCatalog.load(directory)`, `SkillCatalog.validate()`, and `SkillCatalog.get(skill_id)`. These are new catalog-only types; do not replace or mutate the public `Skill` dataclass.
- Source records carry canonical repository URL, exact skill path, immutable commit SHA, declared SPDX license, and maintainer/upstream identity when known.
- Lock records carry the source identity and SHA-256 digest of the normalized skill file set. Unknown values remain explicitly unknown.

- [ ] **Step 1: Add failing contract tests**

Test valid pinned source and lock records; missing commit SHA; malformed digest; duplicate skill IDs; duplicate source identities; unknown lifecycle state; and a legacy `registry/skills.json` entry that has no rich metadata.

- [ ] **Step 2: Verify the relevant failure**

Run: `python3 -m unittest tests.test_skill_catalog -v`

Expected: tests fail because the catalog types and loader do not exist; imports and test setup must succeed.

- [ ] **Step 3: Implement the minimum catalog contract**

Implement immutable data objects and JSON loading using only the standard library. Reject malformed JSON, duplicate IDs, unsupported state values, and invalid digest format with a clear `SkillCatalogError`. Keep missing optional provenance fields unknown rather than inferring them. Existing `Registry.load()` must not be changed to require the new files.

- [ ] **Step 4: Verify the focused pass**

Run: `python3 -m unittest tests.test_skill_catalog -v`

Expected: every catalog contract test passes, including legacy-registry compatibility.

- [ ] **Step 5: Run the affected integration check**

Run: `python3 -m unittest discover -s tests -t .`

Expected: all existing tests and the new catalog tests pass.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add registry/skill-sources.json registry/skills.lock.json omni/skill_catalog.py tests/test_skill_catalog.py
git commit -m "feat: add versioned skill catalog contract"
```

### Task 2: Add safe, read-only skill metadata ingestion and provenance checks

**Files:**
- Modify: `omni/skill_catalog.py`
- Create: `tests/test_skill_ingestion.py`
- Create: `docs/skills/INGESTION.md`

**Interfaces:**
- Consumes: pinned `SkillSource` records from Task 1 and caller-supplied source file bytes/text.
- Produces: `ingest_skill(source, files)` returning a structured result with source identity, normalized file list, digest, metadata findings, and no execution side effects.
- Ingestion accepts a bounded set of text files under the declared skill root; it does not fetch arbitrary URLs itself.

- [ ] **Step 1: Add failing ingestion tests**

Cover a valid `SKILL.md`; missing `SKILL.md`; path traversal such as `../outside.txt`; absolute paths; duplicate normalized paths; unsupported binary payload; digest determinism regardless of input order; and a source commit that is not pinned.

- [ ] **Step 2: Verify the relevant failure**

Run: `python3 -m unittest tests.test_skill_ingestion -v`

Expected: tests fail because the safe ingestion function is not implemented; no test may execute an external command.

- [ ] **Step 3: Implement read-only ingestion**

Normalize and sort relative paths before hashing; reject paths outside the declared root, absolute paths, duplicate paths, and unsupported payloads. Parse only the documented frontmatter fields needed for identification and description. Do not follow symlinks, download resources, execute shell commands, or resolve instructions as tool calls.

- [ ] **Step 4: Verify the focused pass**

Run: `python3 -m unittest tests.test_skill_ingestion -v`

Expected: all path, pinning, metadata, and deterministic-digest tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `python3 -m unittest discover -s tests -t .`

Expected: full suite passes; existing registry and routing behavior remains unchanged.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add omni/skill_catalog.py tests/test_skill_ingestion.py docs/skills/INGESTION.md
git commit -m "feat: validate pinned skill metadata safely"
```

### Task 3: Add static trust checks and explicit lifecycle transitions

**Files:**
- Modify: `omni/skill_catalog.py`
- Create: `tests/test_skill_trust.py`
- Create: `registry/skill-policy.json`
- Modify: `docs/skills/INGESTION.md`

**Interfaces:**
- Consumes: ingestion result and per-skill policy from `registry/skill-policy.json`.
- Produces: `scan_skill(record)`, `transition_skill(record, target_state, approval)`, and structured findings with severity, rule ID, file path, and evidence.
- Lifecycle states: `discovered`, `pinned`, `metadata_validated`, `scanned`, `evaluated`, `approved`, `available`, `active`, `quarantined`, and `revoked`.

- [ ] **Step 1: Add failing trust tests**

Cover suspicious shell execution strings, network exfiltration indicators, secret-access indicators, destructive command indicators, a clean text-only skill, blocked state jumps, missing human approval, approval invalidated by digest change, quarantine, and revocation preventing future activation.

- [ ] **Step 2: Verify the relevant failure**

Run: `python3 -m unittest tests.test_skill_trust -v`

Expected: tests fail because scanner and lifecycle functions do not exist; tests must not execute matched content.

- [ ] **Step 3: Implement deterministic static checks**

Use transparent, documented pattern rules that produce findings, not claims of malware detection. Block activation for policy-defined critical findings, unknown or disallowed licenses, unpinned sources, and changed digests. Require an explicit approval record to transition to `approved`; require a current approval and unchanged digest for `available` or task-scoped `active`. Keep quarantined and revoked records auditable.

- [ ] **Step 4: Verify the focused pass**

Run: `python3 -m unittest tests.test_skill_trust -v`

Expected: all state-machine and scanner tests pass, including denial of activation without approval.

- [ ] **Step 5: Run the affected integration check**

Run: `python3 -m unittest discover -s tests -t .`

Expected: full suite passes and existing six execution gates are unchanged.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add omni/skill_catalog.py tests/test_skill_trust.py registry/skill-policy.json docs/skills/INGESTION.md
git commit -m "feat: add skill trust and approval lifecycle"
```

### Task 4: Expose catalog inspection without changing execution routing

**Files:**
- Modify: `omni/cli.py`
- Modify: `omni/skill_catalog.py`
- Create: `tests/test_skill_catalog_cli.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `SkillCatalog` read APIs and existing CLI argument conventions.
- Produces: read-only CLI operations `python3 -m omni skills catalog`, `python3 -m omni skills inspect <skill-id>`, and `python3 -m omni skills scan <skill-id>`.
- The scan command reports findings only. It cannot approve, activate, install, or execute a skill.
- Existing `python3 -m omni skills` behavior must remain compatible.

- [ ] **Step 1: Add failing CLI tests**

Assert stable JSON/text output for a known skill, a missing skill, an unpinned source, and a critical static finding. Assert that invoking catalog/inspect/scan does not change lifecycle state or execute subprocesses.

- [ ] **Step 2: Verify the relevant failure**

Run: `python3 -m unittest tests.test_skill_catalog_cli -v`

Expected: tests fail because the read-only subcommands do not exist; CLI parsing and test harness load successfully.

- [ ] **Step 3: Implement read-only commands**

Follow current `omni/cli.py` conventions. Return non-zero for malformed catalog input or an unknown requested ID; return a findings report for a valid scan even when findings exist. Do not add an approval or activation CLI in this milestone.

- [ ] **Step 4: Verify the focused pass**

Run: `python3 -m unittest tests.test_skill_catalog_cli -v`

Expected: all CLI behavior and no-side-effect assertions pass.

- [ ] **Step 5: Run full verification**

Run: `python3 -m unittest discover -s tests -t .`
Run: `python3 -m omni registry`
Run: `python3 -m omni skills catalog`
Run: `python3 -m omni selftest`

Expected: the full test suite passes, registry reports no dangling references, catalog output is deterministic, and selftest reports no regression.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add omni/cli.py omni/skill_catalog.py tests/test_skill_catalog_cli.py README.md
git commit -m "feat: expose read-only skill catalog commands"
```

## Integration and review gates

- Keep the current deterministic router as the only routing authority in this milestone. Do not make external or unapproved skills selectable.
- Add approved-skill routing only in a later, separately reviewed change after trust-state semantics and policy behavior have been demonstrated.
- Review every imported skill individually; do not bulk-import thousands of entries or copy whole repositories.
- Do not fork projects solely to collect their metadata. Reuse the account's existing forks where applicable; fork capability was not exposed in the inspected GitHub connector.
- Before opening a PR, verify the branch diff against `omnibrain/supreme-design-v1`, run the complete test suite in a real Python 3.11 environment, inspect all changed files, and report exact CI status. If no Python runtime is available, do not claim tests passed.
- No merge, branch-protection change, GitHub permission change, or paid API call is included in this plan.

## Unresolved product decisions

- Which SPDX licenses are permitted by default beyond MIT and Apache-2.0; CC-BY-4.0 needs per-skill attribution review.
- Whether human approval is recorded in a signed local file, a reviewed Git commit, or a GitHub PR approval. The initial implementation should keep the approval interface abstract and avoid assuming a trusted signing key exists.
- Whether source retrieval will be performed by a later GitHub connector adapter or by a user-provided offline snapshot. This plan keeps network access outside the core catalog.
- Whether the catalog should later support non-`SKILL.md` agent profiles in a separate schema, rather than forcing every source into the Agent Skills format.
