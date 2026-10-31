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
- **Bus d'agents** (`omni/messaging.py`) : boîte aux lettres JSONL par run ;
  expéditeur et destinataire doivent être des agents déclarés ; aucun transport
  réseau implicite.

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
