# Plan de réparation des `AGENTS.md`

Généré en lecture seule par `python3 -m omni overlays --manifest <fichier>`.
Aucun contenu upstream n'est inclus ici : uniquement des empreintes,
pour que le résultat puisse être vérifié après application.

- dépôts scannés : **41**
- actions en attente : **38**

| Dépôt | Action | Taille (octets) | sha256 |
|---|---|---|---|
| `blassana280-ux/agentskills` | restore+overlay *(traité : PR #4)* | 3494 | `13e027cd1804e2d1…` |
| `blassana280-ux/omni-agents-framework` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/agency-agents` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/antigravity-skills` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/Context-Engineering` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/Prompt-Engineering-Guide` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/awesome-claude-code-toolkit` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/Awesome-Context-Engineering` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/ResumeSkills` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/ai-agent-skills-collection` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/Qwen3.8` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/how-claude-code-works` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/designer-skills` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/Red-DiscordBot` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/ai-engineering-hub` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/LLMLingua` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/Open-Agents` | restore+overlay | 179745 | `18c75579f62ca435…` |
| `blassana280-ux/agent-skills-3` | restore+overlay | 11738 | `c4f1e4107200df4f…` |
| `blassana280-ux/GPTCache` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/awesome-gamedev-agent-skills` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/xquads-squads` | restore+overlay | 4483 | `643f983338d9b01d…` |
| `blassana280-ux/agent-skills` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/awesome-llm-apps` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/builder` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/cc-skills-golang` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/agent-skills-index` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/mem0` | restore+overlay | 13531 | `6e97c44f68749435…` |
| `blassana280-ux/skills-` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/video-use` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/awesome-agent-skills` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/hindsight` | restore+overlay | 1626 | `8c475ebdde28e479…` |
| `blassana280-ux/skills-collection` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/LMCache` | restore+overlay | 13367 | `5057470d350f9a6c…` |
| `blassana280-ux/awesome-claude-code` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/cognee` | restore+overlay | 13234 | `6918d7a733bc40dc…` |
| `blassana280-ux/skills` | refresh | 1533 | `0b721cdd59ec3dd6…` |
| `blassana280-ux/kilocode` | restore+overlay | 20087 | `2b4e5e03e99e69f7…` |
| `blassana280-ux/OmniRoute` | restore+overlay | 41609 | `c3cbd4db1dc396e7…` |

## Application

```bash
python3 -m omni overlays --account blassana280-ux --apply
```

Chaque dépôt reçoit une branche `omnibrain/agents-md-<ts>` et une Pull Request ;
`main` n'est jamais écrit directement. Un refus d'écriture est rapporté comme
`blocked`, jamais comme un succès.
