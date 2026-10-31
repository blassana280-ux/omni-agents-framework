# Intégrations — état réel, vérifié

Règle appliquée : une intégration n'est déclarée « fonctionnelle » que si une
commande réelle l'a prouvée. Tout le reste est marqué **source de compétence**
(le dépôt est lu et cité) ou **non intégré**.

## 1. Statuts

| Statut | Signification |
|---|---|
| **exécuté** | du code du dépôt tourne réellement dans ce framework (prouvé par un test) |
| **source de compétence** | le dépôt est une référence documentaire enregistrée dans `registry/skills.json` ; aucun code n'en est exécuté |
| **non intégré** | dépôt inspecté mais ni exécuté ni exploité ; raison indiquée |

## 2. Détail par dépôt

| Dépôt du compte | Type | Statut | Détail vérifié |
|---|---|---|---|
| `omni-agents-framework` | natif | **exécuté** | orchestrateur, registres, gitops, mémoire, bus — 63 tests réels |
| `agentskills` | fork `agentskills/agentskills` | **exécuté** (partiel) + source | `AGENTS.md` (instructions upstream restaurées) et `CONTRIBUTING.md` sont enregistrés comme skills `path-verified` ; `skills-ref/` n'est pas exécuté ici (`pytest` non installé dans l'environnement d'audit) |
| `agency-agents` | fork (Shell) | source de compétence | rôles d'agents réutilisés comme modèles de brief ; aucun script lancé |
| `agent-skills`, `agent-skills-3` | forks (Python) | source de compétence | pack de skills ; pas d'installation |
| `agent-skills-index` | fork | source de compétence | utilisé par `omni-librarian` pour la recherche de skills manquants |
| `awesome-agent-skills`, `skills-collection`, `microsoft-skills`, `antigravity-skills`, `awesome-gamedev-agent-skills` | forks | source de compétence | index de découverte de skills |
| `Open-Agents` | fork (TypeScript) | source de compétence | **non exécuté** : runtime Node non installé/buildé ; utilisé comme modèle de runtime d'agents |
| `OmniRoute` | fork (TypeScript) | source de compétence | **non déployé** : passerelle de modèles nécessitant un déploiement et des clés (aucune clé présente) |
| `9router` | fork (JS) | source de compétence | **non déployé** pour la même raison |
| `kilocode` | fork (TypeScript) | source de compétence | **CLI absent du PATH** (vérifié par `python3 -m omni providers`) ; utilisable comme provider si installé |
| `mem0` | fork (Python) | source de compétence | **non installé** ; la mémoire du framework est fichier + rédaction, elle ne dépend pas de mem0 |
| `cognee` | fork (Python) | source de compétence | idem — mémoire graphe non déployée |
| `hindsight` | fork (Python) | source de compétence | idem |
| `LLMLingua`, `LMCache`, `GPTCache` | forks (Python) | source de compétence | techniques d'optimisation référencées, non exécutées |
| `builder` | fork (JS) | source de compétence | génération d'UI, non déployé |
| `ai-engineering-hub`, `awesome-llm-apps`, `Context-Engineering`, `Awesome-Context-Engineering`, `Prompt-Engineering-Guide`, `how-claude-code-works` | forks | source de compétence | références techniques |
| `designer-skills`, `ResumeSkills` | forks | source de compétence | design/UX |
| `xquads-squads` | fork (HTML) | source de compétence | modèle de revue adverse |
| `9router`, `minimind`, `vpn-decryptor`, `Red-DiscordBot`, `Qwen3.8`, `GPTCache`, `video-use`, `cc-skills-golang`, `builder`, `skills`, `skills-`, `ai-agent-skills-collection`, `awesome-claude-code`, `awesome-claude-code-toolkit` | forks | non utilisé | inspectés ; sans rapport direct avec l'orchestration (ou redondants) |

## 3. Ce qui manque pour passer de « source » à « intégré »

| Dépôt | Prérequis |
|---|---|
| `kilocode`, `Open-Agents`, `claude`, `codex`, `gemini`, `aider` | installer le CLI localement puis `export OMNI_PROVIDER_CMD='<cli> -p {prompt}'` |
| `OmniRoute`, `9router` | déployer le service, fournir les clés **par variables d'environnement** (jamais dans le dépôt), implémenter un `Provider` HTTP |
| `mem0`, `cognee`, `hindsight` | installer le paquet + service de stockage ; remplacer `omni/memory.py` par un adaptateur implémentant `write/get/search` |
| `agentskills/skills-ref` | `pip install pytest uv` puis `cd skills-ref && uv run pytest` |

Aucune de ces étapes n'est simulée ici : elles sont hors périmètre tant que les
prérequis ne sont pas disponibles dans l'environnement.

## 4. Intégration GitHub réellement utilisée

| Opération | État | Preuve |
|---|---|---|
| Lecture des 41 dépôts, parents, fichiers `AGENTS.md` | **fonctionne** | `python3 -m omni audit` ; `docs/GITHUB-AUDIT.md` |
| Création de branche + commit sans toucher `main` | **fonctionne** | `test_gitops.py::TestGitWorkflow` (dépôt git réel) |
| Ouverture de PR via `gh` | **fonctionne** | PR de ce dépôt, ouverte par la même commande que celle construite par `omni.gitops.open_pr` |
| Lecture de la protection de branche | **limitée** | `{"state": "insufficient_permission"}` — le token n'a pas `Administration: read` |
| Application de la protection de branche | **bloquée** | nécessite `Administration: write` ; commande exacte imprimée par `python3 -m omni protection <repo> --apply` |
| Fusion de PR | **volontairement hors périmètre** | toujours une décision humaine |

## 5. Portée d'écriture du jeton GitHub (mesurée)

Sonde réelle : création puis suppression d'une référence temporaire sur chaque
dépôt (`POST /git/refs`), 41 dépôts testés.

| Résultat | Dépôts |
|---|---|
| **écriture autorisée** | `agentskills` (1) |
| **lecture seule** (`403 Resource not accessible by integration`) | les 40 autres, y compris `omni-agents-framework` |
| lecture de la protection de branche | refusée sur tous (`Administration: read` absent) |

Sonde rejouée après reconnexion (2026-10-31 11:01 UTC, token neuf expirant à
19:01 UTC) : **1 écriture / 40 lecture seule**, inchangé.

L'installation `arena-ai-coding-agent` déclare pourtant
`repository_selection: "all"` et `contents: write`. Le token effectif, lui, est
restreint à `agentskills` : `POST /git/refs` renvoie `403` sur `mem0` et
`omni-agents-framework` et `201` sur `agentskills`, **avec le même en-tête
`X-Accepted-Github-Permissions: contents=write`**. La restriction vient donc de
la sélection de dépôts de la connexion, pas d'un défaut de code.

Le pipeline d'écriture a été validé de bout en bout là où l'écriture est permise :
commit `76b281f8cb` créé sur une branche jetable, puis branche supprimée.

Conséquence : les correctifs prévus pour les 9 autres dépôts dont le
`AGENTS.md` upstream a été écrasé sont **prêts et planifiés** par
`python3 -m omni overlays` (voir `docs/OVERLAYS-PLAN.md`), mais ne peuvent pas
être poussés avec ce jeton.
Commande d'application dès que l'accès en écriture est accordé :

```bash
python3 -m omni overlays --account blassana280-ux            # plan (lecture seule)
python3 -m omni overlays --account blassana280-ux --apply    # 1 branche + 1 PR par dépôt
```
