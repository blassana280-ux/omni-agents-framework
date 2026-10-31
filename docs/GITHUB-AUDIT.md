# Audit GitHub — compte `blassana280-ux`

Audit reproductible : `python3 -m omni audit --account blassana280-ux --out audit.json`

Date de l'audit : 2026-10-30. Source : API GitHub via `gh` (lecture seule).

## 1. Référence cassée OmniBrain

| Élément | Résultat vérifié |
|---|---|
| `blassana280-ux/optimiser-mes-agents-IA` | **non vérifiable** — `GET /repos/...` → `403 Resource not accessible by integration` ; `git ls-remote` → `403` ; absent de `GET /user/repos` et de la recherche |
| `specialized/specialized-omnibrain-orchestrator-agent.md` | **jamais lu** — aucun accès au dépôt censé le contenir |
| Remplacement opérationnel | **ce dépôt** : `OMNIBRAIN.md` + `omni/orchestrator.py` + `registry/` + `tests/` |

Conclusion : la référence doit être considérée comme *inexistante ou inaccessible* — jamais comme valide. Les overlays `AGENTS.md` du compte ont été corrigés pour pointer vers `blassana280-ux/omni-agents-framework`.

## 2. Synthèse

- **41 dépôts** accessibles (40 forks, 1 dépôt natif).
- **38** portent le fichier `AGENTS.md` injecté (1 682 octets, blob `3116c8cadc`).
- **10** avaient un `AGENTS.md` upstream **écrasé** : `agent-skills-3`, `agentskills`, `cognee`, `hindsight`, `kilocode`, `LMCache`, `mem0`, `OmniRoute`, `Open-Agents`, `xquads-squads`.
- **27** ont reçu le fichier alors que l'upstream n'en avait pas (aucune instruction locale perdue).
- **3** n'ont pas de `AGENTS.md` : `9router`, `minimind`, `vpn-decryptor`.
- **0** ont un fichier différent (non injecté).

## 3. Détail par dépôt

| Dépôt | Fork de | Branche | `AGENTS.md` local | `AGENTS.md` upstream | Verdict |
|---|---|---|---|---|---|
| `9router` | `decolua/9router` | `master` | absent | absent | absent |
| `agency-agents` | `msitarzewski/agency-agents` | `main` | injected | absent | ajouté |
| `agent-skills` | `JPeetz/agent-skills` | `main` | injected | absent | ajouté |
| `agent-skills-3` | `simota/agent-skills` | `main` | injected | present (10204 o) | **écrasé** |
| `agent-skills-index` | `imDev2023/agent-skills-index` | `main` | injected | absent | ajouté |
| `agentskills` | `agentskills/agentskills` | `main` | injected | present (1960 o) | **écrasé** |
| `ai-agent-skills-collection` | `soahimrahman/ai-agent-skills-collection` | `main` | injected | absent | ajouté |
| `ai-engineering-hub` | `patchy631/ai-engineering-hub` | `main` | injected | absent | ajouté |
| `antigravity-skills` | `pantalon81/antigravity-skills` | `main` | injected | absent | ajouté |
| `awesome-agent-skills` | `VoltAgent/awesome-agent-skills` | `main` | injected | absent | ajouté |
| `awesome-claude-code` | `hesreallyhim/awesome-claude-code` | `main` | injected | absent | ajouté |
| `awesome-claude-code-toolkit` | `rohitg00/awesome-claude-code-toolkit` | `main` | injected | absent | ajouté |
| `Awesome-Context-Engineering` | `Meirtz/Awesome-Context-Engineering` | `main` | injected | absent | ajouté |
| `awesome-gamedev-agent-skills` | `gamedev-skills/awesome-gamedev-agent-skills` | `main` | injected | absent | ajouté |
| `awesome-llm-apps` | `Shubhamsaboo/awesome-llm-apps` | `main` | injected | absent | ajouté |
| `builder` | `HeyPuter/builder` | `main` | injected | absent | ajouté |
| `cc-skills-golang` | `samber/cc-skills-golang` | `main` | injected | absent | ajouté |
| `cognee` | `topoteretes/cognee` | `main` | injected | present (11700 o) | **écrasé** |
| `Context-Engineering` | `jasontang-ai/Context-Engineering` | `main` | injected | absent | ajouté |
| `designer-skills` | `Owl-Listener/designer-skills` | `main` | injected | absent | ajouté |
| `GPTCache` | `zilliztech/GPTCache` | `main` | injected | absent | ajouté |
| `hindsight` | `vectorize-io/hindsight` | `main` | injected | present (92 o) | **écrasé** |
| `how-claude-code-works` | `Windy3f3f3f3f/how-claude-code-works` | `main` | injected | absent | ajouté |
| `kilocode` | `Kilo-Org/kilocode` | `main` | injected | present (18553 o) | **écrasé** |
| `LLMLingua` | `microsoft/LLMLingua` | `main` | injected | absent | ajouté |
| `LMCache` | `LMCache/LMCache` | `dev` | injected | present (11833 o) | **écrasé** |
| `mem0` | `mem0ai/mem0` | `main` | injected | present (11997 o) | **écrasé** |
| `minimind` | `jingyaogong/minimind` | `master` | absent | absent | absent |
| `omni-agents-framework` | `-` | `main` | injected | n/a | inchangé |
| `OmniRoute` | `cheaper-inference/OmniRoute` | `release/v3.8.50` | injected | present (40075 o) | **écrasé** |
| `Open-Agents` | `Impertio-Studio/Open-Agents` | `main` | injected | present (178211 o) | **écrasé** |
| `Prompt-Engineering-Guide` | `dair-ai/Prompt-Engineering-Guide` | `main` | injected | absent | ajouté |
| `Qwen3.8` | `QwenLM/Qwen3.8` | `main` | injected | absent | ajouté |
| `Red-DiscordBot` | `Cog-Creators/Red-DiscordBot` | `V3/develop` | injected | absent | ajouté |
| `ResumeSkills` | `Paramchoudhary/ResumeSkills` | `main` | injected | absent | ajouté |
| `skills` | `anthropics/skills` | `main` | injected | absent | ajouté |
| `skills-` | `microsoft/skills` | `main` | injected | absent | ajouté |
| `skills-collection` | `alexander-kastil/skills-collection` | `master` | injected | absent | ajouté |
| `video-use` | `browser-use/video-use` | `main` | injected | absent | ajouté |
| `vpn-decryptor` | `Matrixzat/vpn-decryptor` | `main` | absent | absent | absent |
| `xquads-squads` | `ohmyjahh/xquads-squads` | `main` | injected | present (2949 o) | **écrasé** |

## 4. Autres constats

- Aucun secret détecté dans les fichiers `AGENTS.md` inspectés.
- `9router`, `minimind`, `vpn-decryptor` : pas de `AGENTS.md` (aucun overlay à restaurer).
- Les `CLAUDE.md` upstream existants (`cognee`, `kilocode`, `Context-Engineering`, `9router`, `Prompt-Engineering-Guide`) n'ont **pas** été modifiés.
- Les 41 dépôts sont des forks d'upstreams tiers, sauf `omni-agents-framework` : ce sont des **sources de compétences**, pas des services exécutés localement.
