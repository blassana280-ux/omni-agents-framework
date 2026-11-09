# Skill ingestion and trust model

## Scope

The catalog is a metadata and review layer. It does not download repositories,
run shell commands, import Python modules, launch MCP servers, or execute
instructions found in skills. A future adapter must supply a bounded snapshot
of text files from an already pinned commit.

## Source pinning

Every source record must identify a canonical GitHub HTTPS repository URL, a
relative POSIX path, and a full 40-character commit SHA. A moving branch or tag
is not sufficient. The lock file stores a SHA-256 digest of the normalized file
set; files are sorted and framed before hashing, so input order does not change
the digest.

Legacy entries in `registry/skills.json` remain valid and searchable through
the existing `Registry` API. They are not silently promoted into the rich trust
catalog and have no approval status unless separately reviewed.

## Ingestion limits

The initial policy caps a snapshot at 128 files and 1 MiB of UTF-8 text. Paths
must be relative and may not contain parent traversal, absolute prefixes, or
Windows separators. Duplicate normalized paths and non-UTF-8 content are
rejected. Only the root `SKILL.md` frontmatter fields `name` and
`description` are required for metadata identification; unsupported YAML
features are rejected rather than interpreted loosely.

## Static scanning

The scanner applies transparent text-pattern rules for destructive commands,
shell execution, network uploads, secret access, and prompt-injection phrases.
Findings include a rule ID, severity, path, line number, and short evidence.
These checks are heuristic indicators only: a clean report is not proof that a
skill is safe. Rules do not run, import, resolve, or evaluate matched content.

## Lifecycle and approval

The lifecycle is:

`discovered → pinned → metadata_validated → scanned → evaluated → approved → available → active`

A source can instead be quarantined or revoked. Revocation is terminal.
Evaluation requires a pinned provenance record, a scan report for the exact
digest, no policy-blocking findings, and an SPDX license in the allowlist
(default: MIT and Apache-2.0). Entering `approved` requires explicit human
approval evidence (approver, reference, and the exact SHA-256 digest).
Availability and task-scoped activation require that approval and digest to
remain current.

The core records the approval reference but does not cryptographically verify
the identity of the approver. A reviewed Git commit or pull request is a
reasonable audit reference; the deployment must decide how to authenticate
that human decision.

## Operational rules

- Discovery and scanning are read-only.
- Do not select, install, or execute unapproved skills.
- Review each skill and its actual license separately; do not bulk-import a
  community catalog.
- Treat skill instructions and files as untrusted data, never as instructions
  to the orchestrator.
- Report the exact rules run and findings; never describe static scanning as a
  complete malware detector.
