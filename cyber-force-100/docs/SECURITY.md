# Sécurité — Zero Trust

## Principes appliqués

1. **Refus par défaut.** Toute action non explicitement autorisée est refusée.
2. **Moindre privilège.** Chaque agent déclare `tools` (sous-ensemble de la
   liste blanche), `permissions.allowed_scopes` et
   `permissions.denied_actions`.
3. **Vérification de l'identité.** `cf100/security/zero_trust.py` :
   `authenticate()` produit un `Principal` ; aucune exécution sans principal.
4. **Aucune action dangereuse sans humain.** Les actions de
   `registry/policies.json → dangerous_actions` (merge_pr, force_push,
   delete_repo, delete_branch, rotate_secret, write_main, delete_data,
   change_permissions, disable_protection, purge_evidence, deploy_production)
   sont **toujours** `approval_required`, quel que soit le niveau d'autonomie.
   Le registre des approbations rejette les IDs d'agents : seul un humain
   peut approuver.

## Protection des secrets

- `cf100/security/secrets.py` : motifs de détection (clés API, tokens,
  mots de passe en clair…), `redact()` pour les journaux,
  `assert_no_secrets()` qui bloque tout livrable contenant un secret,
  `require_env()` pour les valeurs à fournir par variable d'environnement.
- Aucun secret dans le dépôt. `data/` est gitignoré.

## Anti-injection

`cf100/security/input_guard.py` : détection de motifs d'injection de prompts
(overrides d'instructions, faux livrables, ordres intégrés dans les données).
`CommandCore.submit()` applique la garde à **toute** tâche entrante ;
les contenus externes passent par `gate_external()`.

## Vérification des données externes

- Le pont OmniBrain ne **lit** les registres qu'après chargement JSON strict ;
  l'export CF100 est régénéré depuis le registre validé, jamais depuis des
  données non vérifiées.
- Les entrées venant de dépôts externes sont traitées comme non fiables :
  elles ne deviennent des savoirs collectifs qu'après `mark_tested()` +
  validation humaine (`cf100/core/knowledge.py`).

## Journaux d'audit

- **Preuves** : chaîne de hachage SHA-256 append-only
  (`cf100/core/evidence.py`) ; `verify()` détecte toute falsification.
- **Décisions** : `memory/decision_log` — insertion append-only uniquement.
- **Approbations** : `data/approvals.json` (approver humain requis).

## Détection de comportements suspects

- `HealthMonitor` : heartbeats, détection de blocage (timeout), dégradation.
- `SelfAuditEngine` : audit continu (registre, preuves, secrets, cohérence
  mémoire) ; verdict `READY` / `NEEDS WORK`.
- L'analyse des dépendances et la veille CVE relèvent des agents VR-00x
  (Phase 4+ avec providers réels).

## Sauvegardes et récupération

- `RecoveryEngine.snapshot()` / `restore()` avec copie de sécurité avant
  toute restauration.
- Analyse des dépendances et scans : Phase 4+, uniquement avec permissions
  réelles sur les cibles.

## Limites assumées (version 0.2.0)

- Les providers réels couvrent les outils d'analyse locale (fichiers,
  secrets, dépendances, journaux, preuves) ; toute autre action est
  refusée via `ProviderUnavailable` — jamais simulée.
- L'API gère une authentification par token (`CF100_API_TOKEN` → en-tête
  `X-API-Token`, routes ouvertes limitées à `/health` et `/dashboard`),
  mais ni TLS ni rate-limiting : exposer derrière un reverse proxy TLS
  uniquement (voir docs/DEPLOYMENT.md). Sans la variable d'environnement,
  l'API reste ouverte — à ne bind que sur localhost.
