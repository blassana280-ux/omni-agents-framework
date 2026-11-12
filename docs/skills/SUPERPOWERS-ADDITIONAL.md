# Additional Superpowers skill snapshots

Six additional skills from `obra/superpowers` are stored as offline review snapshots. Four are self-contained; systematic debugging includes five supporting references and one shell helper stored as text; writing-skills includes eight reference files and a renderer script stored as text. The renderer is not executed.

- **Upstream commit:** `df2e996a174f49f05aa5d5777ca56fbb0aa972ec`
- **Upstream repository:** https://github.com/obra/superpowers
- **SPDX license:** MIT; complete notice preserved at `docs/third-party-licenses/obra-superpowers-MIT.txt`
- **Maintainer identity recorded by source:** Jesse Vincent (`obra`)
- **Signature status:** GitHub reports the upstream commit as unsigned (`verification.verified = false`).

| Skill ID | Upstream path | Bytes | Normalized SHA-256 |
|---|---|---:|---|
| `superpowers-dispatching-parallel-agents` | `skills/dispatching-parallel-agents` | 6078 | `66c6623c372c4dff8d64ddf759ad73fe22ed85f1353b38aa67116c8761615e89` |
| `superpowers-finishing-a-development-branch` | `skills/finishing-a-development-branch` | 7781 | `0354b0c1585bf562f9d2a424e6857e647b798f2d26eee7fef8f53e1901b3695d` |
| `superpowers-receiving-code-review` | `skills/receiving-code-review` | 6203 | `2a97da4ab372d0213a00331b25212a78df9b26d40265d683f653c5a2fc94952a` |
| `superpowers-using-git-worktrees` | `skills/using-git-worktrees` | 6813 | `e0ac19a652ce46003d1133d8a207f9cafe43b3d1f520d50b1641746e148f369f` |
| `superpowers-systematic-debugging` | `skills/systematic-debugging` | 29057 | `e1bddfb78115f3ebbe5a07531e2469d7d9f87af20584c27f3cac44c05ad577f8` |
| `superpowers-writing-skills` | `skills/writing-skills` | 109209 | `7774fa35b436c3f549dc923bfb7a2700b40959c557ffd651c4183b76ddb0d12e` |

## Trust and execution boundaries

All six entries are marked **`pinned` only**. They are not approved, available, or active. The upstream commit is unsigned, so provenance is commit-pinned and content-hashed but not signature-verified.

The CLI performs a digest check and heuristic static scan; a clean scan is not a safety certification. These are read-only text snapshots. The `find-polluter.sh` helper and `render-graphs.js` are stored as text and are not installed or run. No commands, hooks, agents, or skill instructions are activated or executed. The existing `registry/skills.json` and agent routing remain unchanged.
