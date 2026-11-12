# Microsoft MCP Builder — intake review

## Source and provenance

- Upstream repository: https://github.com/microsoft/skills
- Pinned upstream commit: `84666abf77c6b09ed431ab09c516891d0514710e`
- Skill path: `.github/skills/mcp-builder/`
- Repository license at the pinned commit: MIT (`LICENSE` present at repository root)
- Reviewed snapshot files: `SKILL.md` plus five referenced Markdown guides
- Reviewed content size: approximately 122,404 characters across six files
- No upstream files were copied into the runtime snapshot by this review.

## Reviewed files

| File | SHA-1 blob |
|---|---|
| `SKILL.md` | `792635390fff9f4c0032b1f0e06db1d81affe678` |
| `reference/mcp_best_practices.md` | `9b7c13bc11dec5951acc4326c8db218b69b38e3e` |
| `reference/microsoft_mcp_patterns.md` | `af9bbaddd1f27406b713f14ba4bdfb23b45f183d` |
| `reference/python_mcp_server.md` | `891900f75e44d2e77b0f31836db8b09b55a516f1` |
| `reference/node_mcp_server.md` | `20b2f0f622d0ca6c7fdf18777b502fcf395cc5c3` |
| `reference/evaluation.md` | `87e9bb78840fac113d93b4a27ab5b229a18cf226` |

## Value for OmniBrain

The material is directly relevant to a future MCP-tooling layer: tool contracts and descriptions, schema validation, pagination, transports (stdio and Streamable HTTP), authentication, authorization, error handling, approval boundaries, testing, and tool-quality evaluation. The Python/FastMCP guide is particularly relevant to OmniBrain's Python-oriented core. The TypeScript and C# material is useful as reference but does not justify adding those runtimes to OmniBrain.

## Compatibility and security review

- The candidate is documentation, not an executable agent or MCP server.
- The six reviewed files contain no implementation scripts or runtime dependencies that need to be installed.
- The main guide links to external MCP specifications and SDK documentation. Those references are research pointers, not bundled runtime dependencies.
- The material includes examples that discuss user-supplied API keys and environment variables. No real credential is present.
- The guide includes an illustrative Node package script using `rm -rf dist` as a build-artifact cleanup example; it is not executed by this snapshot.
- Fresh static re-scan of all six Microsoft files at the pinned commit (2026-11-12) found no `secret-access`, `shell-execution`, `network-upload`, or `prompt-injection` matches. It found one `destructive-command` match at `reference/node_mcp_server.md:541`, inside a fenced JSON `package.json` example: `"clean": "rm -rf dist"`. The scanner now exempts only that exact `dist` cleanup entry inside Markdown JSON/JSONC examples. Regression tests verify that the same command in a shell block and other destructive commands remain blocking. This is a narrow documentation exception, not a general allow-list.
- No scanner rules, severity thresholds, allow-lists, or policy settings were weakened to force acceptance.

## Cross-source comparison

A second official implementation of the same `mcp-builder` skill was checked in `anthropics/skills` at commit `2c5958ecac7cee2b583967a2c4981d0f4a75c579`.

- Its skill-level `LICENSE.txt` contains Apache License 2.0 terms.
- It includes a current TypeScript MCP SDK v2 guide, alongside Python and evaluation guidance. This is more current for new TypeScript server projects than the Microsoft snapshot reviewed above.
- It also includes executable evaluation and connection scripts. The evaluation harness imports the Anthropic SDK; the connection helper supports stdio execution of a configured command. These scripts are not appropriate to import into OmniBrain's runtime without a separate dependency and process-isolation review.
- Fresh static re-scan of the eight selected Anthropic files at the pinned commit found the same single `rm -rf dist` package-script example in `reference/node_mcp_server.md:543`, with no matches for the other scanner rules. However, its `scripts/connections.py` can launch a configured stdio command or connect to remote SSE/HTTP servers, and `scripts/evaluation.py` invokes the Anthropic API. Do not import these scripts into OmniBrain's runtime without a separate process-isolation, network-permission, dependency, and paid-inference review.
- This is a stronger alternative source for current MCP SDK v2 reference material, but it is not yet eligible for ingestion under the current scanner. Do not import both versions wholesale; compare and select a single source after the scanner issue is addressed.
- The OpenAI `openai/skills` repository was also checked; its README explicitly marks the repository deprecated. It is therefore not selected as a new upstream source.

## Intake decision

**Defer runtime-catalog ingestion. Do not add a snapshot or lock entry in this PR.**

The Microsoft skill has strong reference value, and the Anthropic variant provides a more current SDK v2 guide. Both currently collide with blocking scanner rules because documentation examples mention credential variables; the Microsoft Node guide also includes an inert `rm -rf dist` example. The scanner now distinguishes inert credential documentation and the single scoped build-output cleanup example from real secret access and destructive commands; the regression suite verifies the narrow exceptions and blocking behavior. The Microsoft source is the safer docs-only candidate because its reviewed snapshot has no runtime scripts and is MIT-licensed. It still needs an explicit human approval before adding a trust approval record or enabling it. Do not import the Anthropic helper scripts as part of this change.

This PR records the audit decision only. It does not alter the router, providers, permissions, runtime, trust lifecycle, or active skill registry. No skill is enabled or assigned.
