# OMNIBRAIN — spécification de l'orchestrateur central

> **Ce fichier est la source de vérité OmniBrain.**
> Il remplace la référence historique `blassana280-ux/optimiser-mes-agents-IA`
> → `specialized/specialized-omnibrain-orchestrator-agent.md`, qui **n'a pas pu
> être vérifiée** : l'API GitHub répond `403 Resource not accessible by
> integration` et le dépôt n'apparaît ni dans la liste des dépôts du compte ni
> dans la recherche. Aucun outil présent n'a pu lire ce fichier. Il ne doit donc
> plus être cité comme existant.
>
> L'orchestrateur opérationnel est celui de ce dépôt : `omni/orchestrator.py`,
> accompagné de `registry/` et de `tests/`.

## 1. Rôle

OmniBrain est le cerveau central : il ne produit pas le travail à la place des
agents, il **classe, sélectionne, distribue, contrôle, arbitre et assemble**.

## 2. Algorithme effectif

```
demande
  └─> 1. CLASSER          routing.classify()      → simple | medium | complex
      2. SÉLECTIONNER     routing.select_agent()  → un agent par spécialité
      3. PLANIFIER        routing.plan()          → tâches + vagues + briefs
      4. DISPATCHER       orchestrator._run_wave()→ ThreadPoolExecutor, 1 vague = N agents
      5. SURVEILLER       _handle_failures()      → retry → réaffectation → escalade
      6. CORRIGER         _correction_loop()      → critères manquants → nouveau brief
      7. ARBITRER         _arbitrate()            → résultats contradictoires tranchés
      8. VALIDER          validation.check()      → 6 gates
      9. ASSEMBLER        orchestrator.deliverable() → un seul livrable
     10. TRACER           trace.jsonl + run.json  → tout est rejouable
```

### 2.1 Classement

Classification **déterministe** (mots-clés pondérés par spécialité, dans
`registry/routing.json`) : auditable, testable hors ligne, jamais inventée par un
modèle.

- `simple` : 1 spécialité → 1 agent ;
- `medium` : 2–3 spécialités → 1 à 3 agents ;
- `complex` : marqueur explicite (`escouade`, `de bout en bout`, `end-to-end`,
  `fullstack`…) → jusqu'à 8 agents.

### 2.2 Vagues

Une vague = ensemble de tâches sans dépendance mutuelle, exécuté en parallèle
réel (`ThreadPoolExecutor`). Les tâches de revue (`code-review`, `testing-qa`)
dépendent de tout le reste : elles tournent dans une vague ultérieure et notent
un livrable réel, pas une intention. La durée mesurée de chaque vague est
enregistrée (`wall_s`) — c'est la preuve du parallélisme, pas une affirmation.

### 2.3 Gestion d'échec

1. **retry** avec le même agent (`retries`, défaut 1) ;
2. **réaffectation** à un agent de secours déclaré (`fallbacks` du routage) ;
3. **escalade** : message sur le bus + événement `escalate`, verdict `NEEDS_WORK`.

Aucun échec n'est masqué : le run continue mais le verdict reste bloquant.

### 2.4 Arbitrage

Pour chaque sujet revendiqué différemment par deux tâches, la règle est
explicite et ordonnée :

```
nombre de preuves > exécution réelle > critères satisfaits > id de tâche
```

Égalité parfaite ⇒ `resolved=false`, gate `arbitration` en échec, verdict
`NEEDS_WORK`. OmniBrain ne “choisit” pas au hasard.

### 2.5 Boucle de correction

Un livrable dont un critère d'acceptation n'est pas satisfait déclenche une
`Correction` : nouveau brief contenant les critères manquants, message
`correction` sur le bus, nouvelle tentative numérotée. Nombre de tours borné
(`correction_rounds`). Un livrable incomplet après correction reste
`NEEDS_WORK`.

## 3. Les six gates

| Gate | Ce qu'elle vérifie | Échec ⇒ |
|---|---|---|
| `completeness` | toutes les tâches livrées, tous les critères satisfaits | `NEEDS_WORK` |
| `evidence` | toute tâche `ok` porte au moins une preuve | `NEEDS_WORK` |
| `execution` | la tâche a réellement été exécutée par un provider | `NEEDS_WORK` |
| `arbitration` | aucune contradiction non tranchée | `NEEDS_WORK` |
| `secrets` | aucun secret dans le livrable | `NEEDS_WORK` |
| `trace` | chaque tâche a ses événements `dispatch` et `result` | `NEEDS_WORK` |

`READY` n'est possible que si les six passent.

## 4. Limites de chaque agent

Chaque profil de `registry/agents.json` porte un champ `boundaries` injecté dans
le brief, et un jeu d'outils explicite dans `registry/permissions.json` :

- `omni-security` : défensif uniquement — pas d'exploit, pas de collecte de
  credentials, pas de scan de tiers ;
- `omni-gitops` : jamais de commit sur `main`/`master`, jamais de force-push,
  jamais de merge sans confirmation humaine ;
- `omni-reviewer` : ne relit jamais son propre travail, verdict par défaut
  `NEEDS WORK` ;
- `omnibrain` : délègue, n'usurpe pas l'identité d'un spécialiste, ne prétend
  jamais qu'un agent a tourné sans provider.

Actions irréversibles (`merge_pr`, `force_push`, `delete_repo`,
`delete_branch`, `rotate_secret`, `write_main`) : **deny** sans confirmation
humaine explicite, même pour un agent autorisé.

## 5. Mémoire et communication

- **Mémoire partagée** (`omni/memory.py`) : portées `run` et `shared` ;
  écriture en `shared` réservée aux agents explicitement autorisés ; TTL
  optionnel ; toute valeur est **rédigée** (clés API, tokens, clés privées)
  avant persistance.
- Les clés des portées autres que `shared` incluent l'identifiant du run :
  `scope::run_id::key`. Un run ne peut donc ni lire, ni rechercher, ni écraser
  les entrées privées d'un autre run. La portée `shared` reste globale et
  accessible selon les permissions explicites.
- À l'ouverture, les anciennes clés non partagées sont migrées sous le
  `run_id` enregistré dans chaque entrée, sous verrou ; une collision rend
  l'ouverture impossible plutôt que d'écraser silencieusement des données.
- Chaque modification est protégée par un verrou de fichier inter-processus et
  un verrou de thread, puis écrite par remplacement atomique avec `fsync`.
  Le fichier mémoire et son verrou reçoivent des permissions POSIX `0600`.
- Un JSON invalide ou un schéma inattendu déclenche
  `MemoryCorruptionError` : le contenu existant n'est jamais silencieusement
  remplacé par une mémoire vide.
- Les TTL doivent être des entiers strictement positifs. Les adresses mémoire
  ne peuvent pas contenir de chaînes ressemblant à des identifiants secrets.
- **Bus d'agents** (`omni/messaging.py`) : boîte aux lettres JSONL par run ;
  expéditeur et destinataire doivent être des agents déclarés ; sujet, corps et
  payload sont rédigés avant l'écriture et à la lecture ; les écritures d'un
  même bus sont sérialisées entre threads ; fichier limité à POSIX `0600`.
- **Traces** (`omni/trace.py`) : les champs sont rédigés avant d'entrer en
  mémoire ou dans le JSONL ; le fichier est créé avec des permissions POSIX
  `0600`.
- **État de run** (`omni/orchestrator.py`) : le snapshot JSON complet est
  rédigé, écrit dans un fichier temporaire privé, synchronisé puis remplacé
  atomiquement.
- **Exécution provider** (`omni/executor.py`) : chaque brief fichier est
  créé avec un nom aléatoire dans le workspace, en permissions POSIX `0600`,
  puis supprimé dans un bloc `finally` après la fin ou l'échec du processus.
  Les sorties stdout/stderr et erreurs sont rédigées avant d'être retournées.
- **Ingestion provider** (`omni/models.py`) : même un provider personnalisé
  passe par une rédaction centrale des résumés, preuves, artefacts, claims et
  erreurs avant d'entrer dans le résultat du run.
- **Livrable final** : le document assemblé est rédigé une dernière fois avant
  d'être retourné ou affiché.
- Le gate `secrets` inspecte la demande, les résultats complets (preuves,
  claims, erreurs, résumés, artefacts) et les événements de trace ; il bloque
  tout contenu ressemblant à un identifiant secret.

## 5 bis. Réparation des overlays du compte

`omni/overlays.py` (+ `python3 -m omni overlays`) détecte les dépôts dont le
`AGENTS.md` upstream a été écrasé, récupère le contenu d'origine et le restaure
**à l'identique**, puis ajoute la couche locale dans une section séparée et
marquée (`<!-- omnibrain-overlay:v2 -->`). La composition est idempotente et
testée (`tests/test_overlays.py`). L'application exige un accès en écriture ; un
403 est rapporté comme `blocked`, jamais comme un succès.

## 6. Ce qu'OmniBrain ne fait pas

- Il n'invente pas de compétence : spécialité non couverte ⇒ `MissingSpecialty`
  + suggestions issues du registre des skills (scénario 4 des tests).
- Il n'affirme pas qu'un agent a travaillé sans provider configuré.
- Il ne modifie pas la protection de branche sans le scope GitHub
  `Administration` (vérifié : le token actuel ne l'a pas).
- Il ne fusionne pas de PR de lui-même.


## 7. Provider Mistral

`MistralProvider` utilise l'API officielle Chat Completions sans SDK tiers. La sélection est explicite (`OMNI_PROVIDER=mistral`) et l'inférence payante reste verrouillée par défaut (`OMNI_MISTRAL_ALLOW_PAID=1` doit être défini explicitement pour le run autorisé). La clé vient de `MISTRAL_API_KEY_FILE` privé, ou d'une variable d'environnement protégée pour un environnement hébergé ; le fichier est prioritaire et doit être régulier, sans lien symbolique et en mode POSIX `0600` ou plus strict. `providers --verify mistral` est local et n'envoie aucune requête. Les réponses sont structurées en JSON. Les preuves, critères, claims et artefacts générés par le modèle sont conservés uniquement comme déclarations explicitement non vérifiées ; `met_criteria` et les artefacts effectifs restent vides, le statut demeure `incomplete`, et un run Mistral seul ne peut donc pas obtenir `READY`. Une validation indépendante ou humaine est nécessaire. Les clés exactes sont rédigées et aucun retry HTTP n'est effectué. Le provider n'ajoute aucun outil shell/GitHub/navigateur.
