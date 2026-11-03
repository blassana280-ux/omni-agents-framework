# Architecture — Cyber Force 100

## Vue d'ensemble

```
                        ┌─────────────────────────────┐
                        │        Command Core         │
                        │  (classification, garde,    │
                        │   décision, dispatch)       │
                        └──────────┬──────────────────┘
                                   │
      ┌────────────────────────────┼─────────────────────────────┐
      │                            │                             │
┌─────▼──────┐              ┌──────▼───────┐              ┌──────▼──────┐
│ Orchestrator│              │ Agent Registry│             │ OmniBrain   │
│ (routage,   │              │ (10×10 + DYN) │             │ Bridge      │
│ fallbacks,  │              └──────┬───────┘             │ (lecture/   │
│ vagues)     │                     │                      │  export)    │
└─────┬───────┘                     │                      └─────────────┘
      │                     ┌───────▼────────┐
      │                     │  100 CyberAgents│
      │                     │  + dynamiques   │
      │                     └───────┬────────┘
      │                             │
┌─────▼──────────┐   ┌──────────────▼──┐   ┌──────────────────┐
│ Security Policy │   │ Memory Tiers    │   │ Evidence Engine   │
│ (risque, gates, │   │ (4 niveaux,     │   │ (chaîne SHA-256,  │
│ approbations)   │   │  SQLite)        │   │  append-only)     │
└─────────────────┘   └─────────────────┘   └──────────────────┘
```

## Couches

| Couche | Modules | Rôle |
|---|---|---|
| **Agents** | `cf100/agents/` | Spécifications (`models.py`), registre + invariants (`registry.py`), cycle de vie (`base.py`), agents dynamiques (`dynamic.py`), santé (`health.py`). |
| **Sécurité** | `cf100/security/` | Moteur de politiques (`policy.py`), Zero Trust (`zero_trust.py`), secrets (`secrets.py`), garde anti-injection (`input_guard.py`). |
| **Mémoire** | `cf100/memory/` | Stockage SQLite append-only (`store.py`), 4 niveaux avec cloisonnement (`tiers.py`). |
| **Cœur** | `cf100/core/` | Commandement (`command.py`), décision adaptative (`decision.py`), prédiction EWMA (`predictive.py`), orchestration (`orchestrator.py`), conflits (`conflict.py`), remédiation contrôlée (`remediation.py`), auto-audit (`selfaudit.py`), récupération (`recovery.py`), évolution des savoirs (`knowledge.py`), preuves (`evidence.py`). |
| **Ponts** | `cf100/bridges/` | OmniBrain : lecture des registres du dépôt `omni-agents-framework`, détection de compétences chevauchantes, export au format OmniBrain. |
| **API** | `cf100/api/` | FastAPI optionnelle (`/health`, `/divisions`, `/agents`, `/evidence`, `POST /tasks`). |

## Flux d'une tâche

1. **CommandCore.submit(task)** → garde anti-injection sur le texte de la tâche.
2. Classification déterministe (`simple` / `medium` / `complex`).
3. **DecisionEngine** propose un plan (`ActionPlan` : actions, risque max, division cible).
4. **PolicyEngine.evaluate** → `allow` / `deny` / `approval_required`
   (plafond d'autonomie de l'agent + classe de risque de chaque action).
5. Si `allow` → **Orchestrator** sélectionne des agents compétents, exécute,
   gère fallbacks et vagues parallèles.
6. Chaque étape est scellée dans l'**EvidenceEngine** ; les conflits de
   conclusions passent par le **ConflictResolutionEngine** (preuves >
   exécution > critères > id, aligné sur l'arbitrage OmniBrain).
7. Les résultats alimentent la **mémoire technique** et l'apprentissage
   (les poids ne bougent que sur résultats **validés**).

## Registre

- 10 divisions (`DIV-001` … `DIV-010`), codes CI, TH, VR, DP, IR, MA, NS, AS, AI, AC.
- Agents : `<CODE>-NNN` (ex. `TH-004`), agents dynamiques `DYN-<slug>-<hash>`.
- `validate_registry()` impose : 10 divisions, 10 agents par division, 100
  total, ids/noms uniques, outils ⊆ liste blanche `registry/policies.json`,
  fallback existant, `denied_actions` ≠ outils requis.

## Choix techniques (et pourquoi)

- **Python stdlib-only pour le cœur** : aucun service externe indispensable ;
  FastAPI/pytest en extras. La plateforme fonctionne hors ligne.
- **JSON pour les registres** : aligné sur les conventions OmniBrain
  (`registry/agents.json`, `registry/permissions.json`), diffable, sans
  dépendance YAML.
- **SQLite pour la mémoire** : fiable, portable, gitignorable (`data/`).
- **Chaîne de hachage pour les preuves** : altération détectable sans
  infrastructure externe.
- **Pas de file d'attente ni de broker (Redis/Qdrant) en Phase 1** : le besoin
  n'est pas encore démontré ; `config.py` laisse les portes ouvertes via `CF100_*`.

## Déploiement visé

- CI GitHub Actions (`.github/workflows/cf100-ci.yml` à la racine du dépôt
  hôte) : validation du registre, auto-audit, pytest.
- Exécution locale ou serveur dédié ; l'API reste optionnelle.
