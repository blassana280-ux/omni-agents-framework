# 🛡️ Cyber Force 100

**Plateforme de cybersécurité défensive : 100 agents permanents, 10 divisions, autonomie encadrée, intégrée à OmniBrain.**

> Statut : **Phase 1 — Fondation** (v0.1.0). Voir [docs/PHASES.md](docs/PHASES.md) pour l'état exact de chaque composant (fonctionnel / partiel / en développement / non implémenté).

## Ce que c'est

Cyber Force 100 (CF100) est une force de cybersécurité défensive modulaire :

- **10 divisions × 10 agents** : Cyber Intelligence, Threat Hunters, Vulnerability Research, Defense & Protection, Incident Response, Malware Analysis, Network Security, Application Security, AI Security, Audit & Compliance — chaque agent a un identifiant unique, une mission, des compétences, des outils autorisés, des permissions limitées, des conditions d'activation et un fallback (`registry/divisions/*.json`).
- **Autonomie maximale encadrée** : les tâches à faible risque s'exécutent automatiquement ; toute action destructive ou à fort impact exige une **validation humaine** (jamais auto-accordée) — cf100/security/policy.py, [docs/AUTONOMY.md](docs/AUTONOMY.md).
- **Mémoire persistante à 4 niveaux** : individuelle, collective (écriture réservée aux savoirs validés), technique, historique des décisions (append-only) — SQLite, zéro dépendance obligatoire.
- **Preuves inviolables autant que possible** : journal append-only à chaîne de hachage SHA-256, toute altération est détectée.
- **Zero Trust** : identité vérifiée, refus par défaut, moindre privilège, garde anti-injection de prompts, détection de secrets.
- **Coordination OmniBrain** : CF100 ne remplace jamais l'orchestrateur central (dépôt `omni-agents-framework`) ; il s'y raccorde — [docs/OMNIBRAIN-INTEGRATION.md](docs/OMNIBRAIN-INTEGRATION.md).

## Démarrage rapide

```bash
# aucune dépendance obligatoire pour le cœur
python -m cf100 validate   # valide le registre : 10 divisions, 100 agents
python -m cf100 audit      # auto-audit : registre + preuves + secrets
python -m cf100 list       # affiche les 100 agents par division

# tests
pip install -e ".[dev]"
pytest

# API (optionnelle)
pip install -e ".[api]"
python -m cf100 serve       # http://127.0.0.1:8100
```

## Structure

```
cyber-force-100/
├── cf100/                 # package Python (stdlib-only)
│   ├── agents/            # registre, cycle de vie, santé, dynamiques
│   ├── core/              # command, décision, prédiction, orchestration,
│   │                      # remédiation, conflits, auto-audit, récupération,
│   │                      # évolution des savoirs, preuves
│   ├── security/          # politiques, zero trust, secrets, anti-injection
│   ├── memory/            # 4 niveaux persistants (SQLite)
│   ├── bridges/           # pont OmniBrain (+ Arena en Phase 5)
│   └── api/               # FastAPI (optionnelle)
├── registry/
│   ├── divisions/         # 10 fichiers × 10 agents = 100 agents déclarés
│   └── policies.json      # outils, risques, actions dangereuses
├── tests/                 # pytest — invariants réels, jamais décoratifs
└── docs/                  # architecture, sécurité, autonomie, phases
```

## Règles non négociables

1. **Défensif uniquement** — pas d'exploit, pas de scan de tiers, pas de collecte de credentials, uniquement les systèmes pour lesquels les autorisations existent.
2. **Jamais de validation auto-accordée** — `merge_pr`, `delete_data`, `write_main`, etc. exigent une approbation humaine explicite et journalisée.
3. **Jamais de travail simulé** — un agent sans provider échoue explicitement ; aucun résultat n'est inventé.
4. **Aucune écriture directe sur `main`** — branche dédiée + Pull Request, fusion décidée par Lassana.
5. **Aucun secret dans le dépôt** — variables d'environnement uniquement.

## Licence

Propriété de Lassana Bah — usage privé. République du Mali / Allemagne, 2026.
