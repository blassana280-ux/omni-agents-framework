# Rapport final — réparation et intégration OmniBrain

Date : 2026-10-30. Portée : compte `blassana280-ux`.
Toutes les affirmations ci-dessous ont été produites par une commande réelle ; les
éléments non vérifiables sont marqués comme tels.

---

## 1. Dépôts inspectés — 41

Inventaire complet (nom, fork, parent, branche par défaut, `AGENTS.md` local et
upstream) : `docs/GITHUB-AUDIT.md`. Reproduction :

```bash
python3 -m omni audit --account blassana280-ux --out audit.json
```

Dépôts explicitement demandés dans la mission : `Open-Agents`,
`omni-agents-framework`, `agency-agents`, `agent-skills`, `agentskills`,
`agent-skills-index`, `OmniRoute`, `kilocode`, `9router`, `mem0`, `cognee` — tous
présents et inspectés. La liste n'était pas exhaustive : 30 autres dépôts ont été
couverts.

`blassana280-ux/optimiser-mes-agents-IA` : **absent de la liste accessible et
inaccessible par API** (`403`). Voir §3.

## 2. Problèmes identifiés

| # | Problème | Preuve |
|---|---|---|
| 1 | Référence OmniBrain cassée vers un dépôt non vérifiable | `GET /repos/...` → 403 ; absent de `GET /user/repos` et de la recherche |
| 2 | `AGENTS.md` upstream écrasé dans 10 dépôts | blob injecté `3116c8cadc` (1 682 o) vs 1 960 o upstream pour `agentskills`, etc. |
| 3 | Overlay identique poussé dans 38 dépôts | même blob `3116c8cadc` partout |
| 4 | Aucun orchestrateur exécutable malgré les règles annoncées | `omni-agents-framework` ne contenait qu'un `AGENTS.md` (1 fichier) |
| 5 | Aucun registre d'agents, de compétences, de permissions | vérifié : dépôt d'un seul fichier |
| 6 | Aucun test vérifiable | idem |
| 7 | Jeton GitHub en écriture sur **1 seul** dépôt | sonde `POST /git/refs` sur 41 dépôts |
| 8 | Protection de branche illisible/appliquable | `403` sur `/branches/main/protection` |
| 9 | Aucun fournisseur IA configuré dans l'environnement | `python3 -m omni providers` |
| 10 | Dépôts tiers clonés en forks **sans** intégration réelle | aucun code de `mem0`, `cognee`, `kilocode`, `OmniRoute`, `Open-Agents`, `9router` n'est exécuté |

## 3. La référence cassée

`specialized/specialized-omnibrain-orchestrator-agent.md` **n'a jamais pu être lu** :
le dépôt censé le contenir renvoie `403 Resource not accessible by integration`
(lecture comme `git ls-remote`). Il n'est pas non plus listé par le compte.

Conclusion honnête : **référence invérifiable**, donc invalide comme source de
vérité. Remplacement effectué : `omni-agents-framework/OMNIBRAIN.md` +
`omni/orchestrator.py` + `registry/` + `tests/`, tous exécutés et testés.

## 4. Fichiers modifiés

### `agentskills` (branche `arena/265447fb-agentskills`, PR #4)

- `AGENTS.md` — restauré (1 960 o upstream identiques, vérifié par `diff`) + section
  OmniBrain séparée, avec priorité explicite à l'upstream.
- `omnibrain/` — 42 fichiers : orchestrateur, registres, 69 tests, docs, patch
  d'historique (`omnibrain/patches/0001-omnibrain-orchestrator.patch`).

### `omni-agents-framework` (branche locale `omni/orchestrator-v1`, non poussée)

Clone local `/home/user/omni-agents-framework`, 2 commits, identiques au contenu de
`omnibrain/`. Push refusé : `remote: Permission ... denied` (403).

## 5. Agents et compétences intégrés

- **20 profils d'agents** (`registry/agents.json`), chacun avec `provenance`
  documentée et `boundaries` :
  `omni-frontend`, `omni-web`, `omni-backend`, `omni-architect`, `omni-android`,
  `omni-data`, `omni-research`, `omni-security`, `omni-qa`, `omni-debugger`,
  `omni-perf`, `omni-devops`, `omni-gitops`, `omni-designer`, `omni-ai`,
  `omni-automation`, `omni-reviewer`, `omni-librarian`, `omni-generalist`
  (secours), `omnibrain` (orchestrateur).
- **18 spécialités** routées, dont les 17 exigées + `orchestration`.
- **30 sources de compétences** (`registry/skills.json`) : 3 `path-verified`
  (`agentskills` spec/validator/CONTRIBUTING, gitops local), 27 `repo-exists`,
  0 « inventée ».
- Réutilisation : `agency-agents` (rôles), `designer-skills`, `builder`,
  `xquads-squads` (revue adverse), `agent-skills-index` + `awesome-agent-skills`
  (recherche de skills), `mem0`/`cognee` (modèles de mémoire), `LLMLingua`/
  `LMCache`/`GPTCache` (performance), `kilocode`/`Open-Agents`/`OmniRoute`/
  `9router` (écosystème agents). Créations nouvelles uniquement là où rien
  n'existait : `omni-android`, `omni-security`, `omni-debugger`, `omni-devops`,
  `omni-generalist`.

## 6. Intégrations réellement fonctionnelles

| Intégration | État | Preuve |
|---|---|---|
| Orchestrateur (classement, vagues, gates) | fonctionne | 69 tests OK |
| Parallélisme réel | fonctionne | `wall_s` < `serial_s` mesuré (trace de vague) |
| Git local (branche + commit sans toucher `main`) | fonctionne | dépôt temporaire réel |
| PR GitHub via `gh` | fonctionne | cette PR |
| Audit du compte (lecture) | fonctionne | 41 dépôts scannés |
| Réparation des overlays (plan) | fonctionne | 10 `restore+overlay` + 28 `refresh` calculés |
| Réparation des overlays (application) | **bloquée** | `403` en écriture |
| Protection de branche | **bloquée** | `Administration` absent |
| Exécution par un agent IA | **non configurée** | aucun CLI, `OMNI_PROVIDER_CMD` vide |
| `mem0`/`cognee`/`kilocode`/`OmniRoute`/`Open-Agents`/`9router` | **sources de compétences, non exécutés** | voir `docs/INTEGRATIONS.md` |

## 7. Tests exécutés

```
python3 -m unittest discover -s tests -t .
Ran 69 tests in 4.33s
OK (skipped=1)
```

Le test ignoré est la sonde réseau opt-in (`OMNI_LIVE=1`) — exécutée séparément :

```
OMNI_LIVE=1 python3 -m unittest tests.test_gitops.TestLiveGitHubProbe -v
ok — {'state': 'insufficient_permission', 'detail': 'token cannot read branch protection'}
```

Correspondance avec les 10 scénarios exigés :

| # | Scénario | Test |
|---|---|---|
| 1 | Demande simple → agent spécialisé | `test_simple_request_selects_one_specialist` |
| 2 | Demande complexe → escouade | `test_complex_request_forms_squad` |
| 3 | Exécution parallèle | `test_wave_is_parallel_not_sequential` |
| 4 | Compétence manquante → recherche | `test_missing_skill_suggests_existing_skills` |
| 5 | Échec → reprise/réaffectation | `TestFailureRecovery` (3 tests) |
| 6 | Résultats contradictoires → arbitrage | `TestArbitration` (2 tests) |
| 7 | Livrable incomplet → correction | `TestCorrectionLoop` (2 tests) |
| 8 | Branche + Pull Request | `TestGitWorkflow` + `TestPullRequestCommands` (6 tests) |
| 9 | Protection de la branche principale | `TestBranchProtectionProbe` (4 tests) + live |
| 10 | Traçabilité agents/outils/résultats | `TestTraceability` (2 tests) |

Aucun test n'est déclaré réussi sans exécution : `docs/TEST-RESULTS.md` contient la
sortie brute.

## 7 bis. Reconnexion GitHub — re-vérification (2026-10-31 11:01 UTC)

Le compte a été reconnecté. Nouveau contrôle, même protocole :

- **token fraîchement émis** (expiration `2026-10-31 19:01:34 UTC`, soit +8 h) ;
- **nouvelle sonde sur les 41 dépôts** : `1` en écriture (`agentskills`), `40` en
  lecture seule — identique à l'état d'avant reconnexion.

Cause identifiée, au-delà du symptôme :

| Constat | Preuve |
|---|---|
| L'application `arena-ai-coding-agent` est bien installée avec `repository_selection: "all"` et la permission `contents: write` | `GET /user/installations` → installation `167372294`, `app_id 4187077` |
| Le **token effectif** est malgré tout restreint à `agentskills` | même appel `POST /git/refs`, même en-tête `X-Accepted-Github-Permissions: contents=write` → `403` sur `mem0` et `omni-agents-framework`, `201` sur `agentskills` |
| Ce n'est pas un problème de fourche ni d'archive | `isArchived: false` sur les 41 ; `omni-agents-framework` est natif et refuse aussi |
| Notre pipeline d'écriture fonctionne | commit `76b281f8cb` créé sur une branche jetable d'`agentskills`, puis branche supprimée (réf absente après coup) |
| Le patch de promotion s'applique proprement | clone neuf de `omni-agents-framework` + `git am` → 69 tests verts |

Conclusion : l'autorisation doit être élargie **au niveau de la connexion GitHub
d'Arena** (sélection de dépôts), pas du code. Le reste est prêt :
`scripts/finish-repair.sh` exécute préflight, publication et réparation en une
commande ; `docs/OVERLAYS-PLAN.md` liste les 38 actions avec leurs empreintes.

## 8. Branches et Pull Requests

| Dépôt | Branche | PR |
|---|---|---|
| `agentskills` | `arena/265447fb-agentskills` | **#4** — https://github.com/blassana280-ux/agentskills/pull/4 |
| `omni-agents-framework` | `omni/orchestrator-v1` (locale) | non ouverte — écriture refusée (403) ; patch fourni |

## 9. Éléments encore bloqués

1. **Écriture GitHub** sur 40 des 41 dépôts → aucune PR possible ailleurs.
   Reconnexion testée le 2026-10-31 : token neuf, périmètre inchangé.
   Action requise : dans GitHub → *Settings → Applications → Arena → Configure →
   Repository access*, choisir **All repositories** (ou ajouter
   `omni-agents-framework` et les 9 dépôts de `docs/OVERLAYS-PLAN.md`), puis
   reconnecter. Vérification ensuite : `bash omnibrain/scripts/finish-repair.sh`
   (préflight `DRY_RUN=1` d'abord).
2. **Les 9 autres `AGENTS.md` écrasés** → réparation prête, application bloquée.
   `python3 -m omni overlays --account blassana280-ux --apply`.
3. **Protection de branche** → scope `Administration` absent.
4. **Exécution par un agent IA** → installer un CLI et définir `OMNI_PROVIDER_CMD`.
5. **`mem0`/`cognee`/`hindsight`** → non installés ; adaptateur `memory` à écrire.
6. **`OmniRoute`/`9router`** → non déployés ; nécessitent un service et des clés
   (jamais dans le dépôt).

## 10. Prochaines améliorations prioritaires

1. Accorder l'écriture GitHub, puis appliquer `omni overlays --apply` sur les 9
   dépôts et promouvoir `omnibrain/` vers `omni-agents-framework` (`git am`).
2. Brancher un provider réel (`claude`/`codex`/`kilo`) et refaire tourner les
   scénarios 1–7 en exécution réelle ; les gates `execution` passeront alors à PASS.
3. Remplacer le classifieur déterministe par un classifieur LLM **avec repli**
   déterministe conservé (le déterminisme reste la garantie auditable).
4. Écrire l'adaptateur `mem0`/`cognee` derrière l'interface `SharedMemory`.
5. Activer la protection de branche sur `main` de chaque dépôt natif et y exiger
   la CI `unittest`.
6. Ajouter un provider HTTP pour `OmniRoute`/`9router` avec clés en variables
   d'environnement et limitation de coût.
