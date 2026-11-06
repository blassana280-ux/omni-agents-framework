# Registre des capacités OmniBrain — Architecture d'intégration

> Branche : feature/omnibrain-capability-expansion — Mission OMNIBRAIN GITHUB
> CAPABILITY EXPANSION (06/11/2026). Fusion dans main = décision de Lassana.

## 1. Positionnement

Le dépôt dispose déjà de trois registres (agents, skills, routing). Cette
mission ajoute le chaînon manquant : un **registre des capacités** qui
indexe les projets open source du monde entier, leurs licences, leurs points
d'entrée et leur statut d'intégration — puis un **module Python** et un
**journal de résultats** pour les exploiter.

Le registre des capacités ne remplace rien : les skills existants (29)
restent la source de vérité des commandes ; le registre des capacités
décrit les briques externes que les agents peuvent charger à la demande.

## 2. Cycle de vie d'une capacité

```text
indexed     → repéré, licence et amont vérifiés, NON encore forké (attente)
forked      → fork présent dans blassana280-ux, pas encore testé
verified    → forké + tests exécutés avec succès + preuve enregistrée
deprecated  → retiré de la rotation active, conservé pour l'historique
```

Un projet externe n'entre **jamais** directement en statut verified : il
passe par indexed, puis forked, puis verified après exécution réelle des
tests. La validation refuse tout raccourci (voir section 4).

## 3. Schéma d'une capacité

Chaque entrée de registry/capabilities.json porte les champs exigés par la
mission :

| Champ | Contenu |
|---|---|
| id / title / domain / specialties | identifiant stable, domaine, spécialités routables |
| description | ce que la brique apporte à OmniBrain |
| source | upstream (dépôt d'origine), fork (dépôt miroir), docs |
| license | spdx, source de vérification, notes |
| risk | niveau, points surveillés, exécution par défaut refusée |
| execution_policy | external-manual-only (capacité externe) / internal (composant du dépôt) |
| prerequisites | dépendances système minimales |
| permissions_needed | permissions GitHub réellement requises |
| dependencies | briques internes et externes attendues |
| entry_points | points de chargement à la demande (repo, path, purpose) |
| integration | status, reason, evidence, verified_at |
| tests | nom, type, status (pass/fail/not-run) |

## 4. Barrières de sécurité et de validation

- **Licences** : allow-list explicite, identique au champ licenses_allowed du
  registre (MIT, Apache-2.0). Les composants commerciaux sont exclus de fait : langfuse
  ee/ et litellm enterprise/ sont interdits de copie et jamais référencés
  comme points d'entrée.
- **Secrets** : le module de validation rejette les jetons GitHub, clés
  sk-…, AWS AKIA… détectés dans le registre ; le journal rédacte
  systématiquement toute valeur secrète avant écriture disque.
- **Exécution** : toute capacité externe a execution_policy
  external-manual-only ; le code amont n'est jamais exécuté aveuglément, seulement lu,
  indexé et routé.
- **Statuts** : forked exige une référence de fork ; verified exige des
  preuves ET au moins un test au statut pass. La validation est exécutée
  par CI à chaque changement.

## 5. Bloqueur actuel : fork 403

L'intégration GitHub disponible (github_app) ne possède pas le scope de
création de dépôts : fork_repository renvoie 403 "Resource not accessible
by integration". Les 10 capacités externes sont donc en statut indexed :
amont vérifié (licence, activité, points d'entrée), fork en attente.

Deux déblocages possibles : (a) octroyer le scope Administration de
dépôts à l'intégration ; (b) lancer manuellement les 10 forks depuis
l'interface GitHub (liste exacte dans registry/capabilities.json, champ
source.upstream).

## 6. Capacités indexées (10 externes + 3 internes)

| Capacité | Domaine | Amont | Licence | Statut |
|---|---|---|---|---|
| browser-use-agentic | browser-automation | browser-use/browser-use | MIT | indexed |
| playwright-deterministic | browser-automation | microsoft/playwright | Apache-2.0 | indexed |
| gpt-researcher-deepsearch | research-deep | assafelovic/gpt-researcher | Apache-2.0 | indexed |
| langgraph-reasoning | reasoning-planning | langchain-ai/langgraph | MIT | indexed |
| promptfoo-evals | tests-benchmarks | promptfoo/promptfoo | MIT | indexed |
| langfuse-observability | observability | langfuse/langfuse | MIT | indexed |
| litellm-routing | multi-llm-routing | BerriAI/litellm | MIT | indexed |
| duckdb-analytics | data-analysis | duckdb/duckdb | MIT | indexed |
| whisper-transcription | multimedia-audio | openai/whisper | MIT | indexed |
| threejs-rendering | multimedia-3d | mrdoob/three.js | MIT | indexed |
| omnibrain-gitops | platform | interne (ce dépôt) | interne | verified |
| cf100-defensive-platform | cybersecurity | interne (ce dépôt) | interne | verified |
| omnibrain-orchestrator | platform | interne (ce dépôt) | interne | verified |

Aucun doublon : les domaines multi-agents, mémoire persistante,
cybersécurité défensive, game-dev, vidéo et documentation étaient déjà
couverts par les forks existants (Open-Agents, kilocode, mem0, cognee,
video-use, ai-engineering-hub…) et n'ont pas été re-forkés.

## 7. Utilisation

Ligne de commande (aucune dépendance hors stdlib) :

```bash
python -m omni.capabilities --validate     # barrières complètes, exit 1 si problème
python -m omni.capabilities --list        # tableau des capacités
python -m omni.capabilities --status     # rapport par statut + forks en attente
python -m omni.capabilities --pending     # capacités indexed à forker
python -m omni.capabilities --search navigateur
```

API Python :

```python
from omni.capabilities import CapabilityRegistry, CapabilityLedger
from omni.registry import Registry

registry = Registry.load()
caps = CapabilityRegistry.load()
cap = caps.capabilities["browser-use-agentic"]
points = caps.entry_points(cap.id)              # chargement à la demande
agents = caps.suggest_agents(cap.id, registry)  # routage spécialiste
```

Journal des résultats et erreurs : ledger/capability-results.jsonl, une
ligne JSON par exécution, secrets rédactés, consultable par capacité.

## 8. Tests

tests/test_capabilities.py — 29 tests unittest, 5 classes (dont 3 tests CLI : formes --validate/validate, détection de problèmes, action inconnue) : registre livré
(champs mission, licences, comptes), barrières de validation (défauts
injection-réponse), découverte et routage (recherche, domaines, points
d'entrée, agents suggérés, dépendances), journal des résultats
(round-trip, filtrage, rédaction de secrets).

CI : .github/workflows/omni-ci.yml déclenche unittest + validation sur
toute modification de omni/, registry/, tests/ ou Makefile, en push main
et sur les PR.
