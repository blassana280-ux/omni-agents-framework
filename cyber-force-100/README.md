# 🛡️ Cyber Force 100

**Plateforme de cybersécurité défensive : 100 agents permanents, 10 divisions, autonomie encadrée, intégrée à OmniBrain.**

> Statut : **Phases 1→8 livrées** (v0.2.0), CI verte à chaque push
> ([onglet Actions](https://github.com/blassana280-ux/omni-agents-framework/actions)).
> Voir [docs/PHASES.md](docs/PHASES.md) pour l'état exact de chaque composant
> (fonctionnel / partiel / en développement / non implémenté).

## Ce que c'est

Cyber Force 100 (CF100) est une force de cybersécurité défensive modulaire :

- **10 divisions × 10 agents** : Cyber Intelligence, Threat Hunters, Vulnerability Research, Defense & Protection, Incident Response, Malware Analysis, Network Security, Application Security, AI Security, Audit & Compliance — chaque agent a un identifiant unique, une mission, des compétences, des outils autorisés, des permissions limitées, des conditions d'activation et un fallback (`registry/divisions/*.json`).
- **Autonomie maximale encadrée** : les tâches à faible risque s'exécutent automatiquement ; toute action destructive ou à fort impact exige une **validation humaine** (jamais auto-accordée) — cf100/security/policy.py, [docs/AUTONOMY.md](docs/AUTONOMY.md).
- **Exécution réelle, jamais simulée** : les providers stdlib (`cf100/providers/stdlib.py`) effectuent de vraies analyses (lecture + SHA-256, secrets, dépendances, journaux, vérification de preuves) ; toute action sans implémentation réelle est refusée (`ProviderUnavailable`).
- **Boucle de supervision** : `MissionSupervisor` enchaîne des vagues de missions, contrôle la santé entre les vagues et n'apprend **que sur des preuves intègres** — un journal falsifié ne modifie jamais les poids décisionnels.
- **Mémoire persistante à 4 niveaux** : individuelle, collective (écriture réservée aux savoirs validés), technique, historique des décisions (append-only) — SQLite, zéro dépendance obligatoire.
- **Preuves inviolables autant que possible** : journal append-only à chaîne de hachage SHA-256 ; altération ET troncature détectées.
- **Zero Trust** : identité vérifiée, refus par défaut, moindre privilège, garde anti-injection de prompts, détection de secrets.
- **Coordination OmniBrain** : pont de lecture/export au format OmniBrain + **file bidirectionnelle** (`OmniQueue`/`OmniCoordinator` : inbox/outbox JSONL avec acks, refus d'injection retournés explicitement) — [docs/OMNIBRAIN-INTEGRATION.md](docs/OMNIBRAIN-INTEGRATION.md).
- **Tableau de bord** : `/dashboard` — HTML/CSS/JS vanilla sans CDN, et API FastAPI authentifiable par token (`CF100_API_TOKEN` → `X-API-Token`).

## Démarrage rapide

```bash
# aucune dépendance obligatoire pour le cœur
python -m cf100 validate   # valide le registre : 10 divisions, 100 agents
python -m cf100 audit      # auto-audit : registre + preuves + secrets
python -m cf100 list       # affiche les 100 agents par division
python -m cf100 evaluate   # rapport d'évaluation des agents
python -m cf100 demo       # mission réelle de démonstration (données
                           #   temporaires étiquetées, preuves vérifiées)

# tests
pip install -e ".[dev]"
pytest

# API (optionnelle) — définir CF100_API_TOKEN avant toute exposition
pip install -e ".[api]"
python -m cf100 serve       # http://127.0.0.1:8100
```

Docker : voir [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) (image slim,
utilisateur non privilégié, healthcheck, modes CLI/API/conteneur).

## Structure

```
cyber-force-100/
├── cf100/                 # package Python (stdlib-only)
│   ├── agents/            # registre, cycle de vie, santé, dynamiques
│   ├── core/              # command, décision, prédiction, orchestration,
│   │                      # supervision, évaluation, remédiation, conflits,
│   │                      # auto-audit, récupération, savoirs, preuves
│   ├── providers/         # exécution RÉELLE stdlib (jamais simulée)
│   ├── security/          # politiques, zero trust, secrets, anti-injection
│   ├── memory/            # 4 niveaux persistants (SQLite)
│   ├── bridges/           # OmniBrain : pont + file bidirectionnelle
│   └── api/               # FastAPI (optionnelle) + dashboard embarqué
├── registry/
│   ├── divisions/         # 10 fichiers × 10 agents = 100 agents déclarés
│   └── policies.json      # outils, risques, actions dangereuses
├── tests/                 # pytest — invariants réels, jamais décoratifs
├── Dockerfile             # image python:3.11-slim, user non privilégié
└── docs/                  # architecture, sécurité, autonomie, phases,
                           # déploiement, intégration OmniBrain
```

## Règles non négociables

1. **Défensif uniquement** — pas d'exploit, pas de scan de tiers, pas de collecte de credentials, uniquement les systèmes pour lesquels les autorisations existent.
2. **Jamais de validation auto-accordée** — `merge_pr`, `delete_data`, `write_main`, etc. exigent une approbation humaine explicite et journalisée.
3. **Jamais de travail simulé** — un agent sans provider échoue explicitement ; un outil sans implémentation réelle lève `ProviderUnavailable` ; aucun résultat n'est inventé.
4. **Apprentissage sous condition de preuve** — les poids décisionnels ne bougent que sur un cycle dont la chaîne de preuves est vérifiée intègre.
5. **Aucune écriture directe sur `main`** — branche dédiée + Pull Request, fusion décidée par Lassana.
6. **Aucun secret dans le dépôt** — variables d'environnement uniquement.

## Licence

Propriété de Lassana Bah — usage privé. République du Mali / Allemagne, 2026.
