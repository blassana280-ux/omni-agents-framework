# Déploiement — Cyber Force 100

## Pré-requis

- Python ≥ 3.10 (3.11 recommandé, tel que testé par la CI) ;
- pour l'API uniquement : `pip install ".[api]"` (fastapi, uvicorn) ;
- pour les tests : `pip install ".[dev]"` (pytest, httpx) ;
- aucun service externe : registres JSON, mémoire SQLite, preuves JSONL.

## Modes d'exécution

### 1. CLI (défaut, le plus simple)

```bash
python -m cf100 validate    # invariants du registre (10×10)
python -m cf100 audit       # auto-audit (registre, preuves, secrets)
python -m cf100 evaluate    # rapport d'évaluation (data/evaluation.json)
python -m cf100 demo        # mission de démonstration réelle (données
                            #   temporaires étiquetées, rien de persisté)
python -m cf100 list TH      # inspecter une division
```

### 2. API locale

```bash
CF100_API_TOKEN="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python -m cf100 serve            # 127.0.0.1:8100
curl -H "X-API-Token: $CF100_API_TOKEN" http://127.0.0.1:8100/agents
```

**Sans `CF100_API_TOKEN`, l'API est ouverte** : ne l'exposez jamais au-delà
de localhost dans ce mode. Avec le token, toutes les routes sauf
`/health` et `/dashboard` exigent l'en-tête `X-API-Token` (statut 401 sinon).

### 3. Docker

```bash
cd cyber-force-100/
docker build -t cf100:0.2.0 .
docker run --rm -p 8100:8100 \
  -e CF100_API_TOKEN=... \
  -v cf100-data:/app/data \
  cf100:0.2.0
```

L'image est `python:3.11-slim`, s'exécute en utilisateur non privilégié
`cf100`, avec healthcheck sur `/health`. Les données (mémoire, preuves,
approbations) vivent dans `/app/data` : montez un volume pour la
persistance.

### 4. CI GitHub Actions (déjà en place)

`.github/workflows/cf100-ci.yml` (à la racine du dépôt hôte) exécute à
chaque push/PR touchant `cyber-force-100/**` : installation, validation du
registre, auto-audit, suite pytest complète — puis **met les agents en
marche** : mission réelle de démonstration (`python -m cf100 demo`,
données temporaires étiquetées, rien de persisté) et évaluation des
100 agents (`python -m cf100 evaluate`), résultats publiés dans le
résumé du run (onglet Summary) et en annotations visibles publiquement.
Le CI est la preuve d'exécution de référence — consultez l'onglet
Actions du dépôt.

**Mise en marche quotidienne** : le workflow est aussi déclenché par
`schedule` tous les jours à **08:00 UTC (08:00 GMT, heure du Mali)** —
les agents partent en mission automatiquement chaque matin, sans
intervention. GitHub Actions peut ajouter quelques minutes de délai au
déclenchement planifié.

## Sauvegardes et récupération

- `RecoveryEngine.snapshot(label)` copie la mémoire SQLite de façon
  horodatée dans `data/snapshots/` ;
- `RecoveryEngine.restore(path)` restaure avec **copie de sûreté
  préalable** du fichier courant (`memory.pre-restore-*.db`) ;
- le journal de preuves est append-only : il ne se restaure pas, il
  s'archive (toute réécriture casserait la chaîne, ce qui est le but).

```bash
python - <<'PY'
from cf100.core.evidence import EvidenceEngine
from cf100.core.recovery import RecoveryEngine
r = RecoveryEngine(evidence=EvidenceEngine())
r.snapshot("avant-maintenance")
print(r.list_snapshots())
PY
```

## Checklist sécurité avant toute exposition

1. `CF100_API_TOKEN` défini (jamais codé en dur, jamais commité) ;
2. API derrière un reverse proxy TLS (l'API ne gère pas TLS elle-même) ;
3. dossier `data/` monté en volume et **exclu du dépôt** (gitignore en place) ;
4. `python -m cf100 audit` vert (registre + preuves + scan secrets) ;
5. `GET /evidence/verify` répond `{"ok": true}` ;
6. aucune action de `dangerous_actions` exécutée sans approbation humaine
   enregistrée dans `data/approvals.json` ;
7. plan de sauvegarde : snapshots réguliers + archivage du journal de
   preuves.

## Limites assumées (version 0.2.0)

- Les providers réels couvrent les outils d'analyse locale (lecture de
  fichier, analyse statique, secrets, dépendances, journaux, vérification
  de preuves) ; les autres actions restent refusées faute d'implémentation
  réelle (`ProviderUnavailable`) — jamais simulées.
- L'API ne gère ni TLS ni rate-limiting : déléguez au reverse proxy.
- Le déploiement d'actions d'impact (remédiation de production) reste
  hors périmètre : toute action `dangerous_actions` exige une validation
  humaine enregistrée, sans exception.
