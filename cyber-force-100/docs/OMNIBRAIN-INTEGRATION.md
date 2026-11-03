# Intégration OmniBrain

OmniBrain (dépôt `blassana280-ux/omni-agents-framework`) est **l'orchestrateur
central** de l'écosystème. Cyber Force 100 s'y raccorde ; il ne le remplace
pas et n'est pas un orchestrateur concurrent.

## Conventions respectées

- Registres JSON (alignés sur `registry/agents.json` /
  `registry/permissions.json` OmniBrain).
- Actions dangereuses : CF100 utilise un **superset** de la liste OmniBrain
  (`merge_pr, force_push, delete_repo, delete_branch, rotate_secret,
  write_main` + `delete_data, change_permissions, disable_protection,
  purge_evidence, deploy_production`), toutes refusées sans validation
  humaine. `OmniBrainBridge.dangerous_action_alignment()` compare les deux
  listes.
- Arbitrage des conflits : preuves > exécution > critères > id (même règle
  que le cœur OmniBrain).
- CF100 **complète** l'agent `omni-security` (relecteur sécurité défensive) ;
  il ne le duplique pas.

## Ce que fait le pont (Phase 1)

`cf100/bridges/omnibrain.py` — `OmniBrainBridge` :

| Méthode | Rôle |
|---|---|
| `omni_agents()` | Charge le registre OmniBrain (`registry/agents.json`) s'il est présent. |
| `overlapping_skills()` | Compare les compétences des 100 agents CF100 avec celles des agents OmniBrain — détection de doublons avant toute création. |
| `export_cf100_for_omni()` | Exporte les 100 agents au format `agents.json` OmniBrain, prêt à importer. |
| `dangerous_action_alignment()` | Rapport d'alignement des listes d'actions dangereuses. |

CLI : `python -m cf100 export-omni` produit `registry/cf100-for-omnibrain.json`.

## Phase 5 (à venir)

- Découverte des compétences OmniBrain en continu.
- Répartition des tâches CF100 ↔ OmniBrain.
- Transmission des résultats et gestion d'erreurs via webhook/file.
- Synchronisation documentée des deux registres.

## Procédure : création du dépôt dédié (si un jour autorisé)

La création de dépôt est actuellement refusée (HTTP 403 — le token GitHub
connecté n'a pas le scope **Administration/Repo creation**). Pour déplacer
CF100 dans un dépôt dédié quand ce sera possible :

1. Sur GitHub : *New repository* → nom `cyber-force-100` → **Private**,
   sans README auto-généré.
2. Cloner localement `omni-agents-framework`, récupérer la branche
   `feature/cyber-force-100-foundation`.
3. `git filter-repo --subdirectory-filter cyber-force-100` (ou copier le
   dossier) vers le nouveau dépôt.
4. Recréer le workflow : le fichier `.github/workflows/cf100-ci.yml` doit
   vivre à la racine **du dépôt d'accueil** — adapter `working-directory`
   (le retirer) après le déménagement.
5. Réouvrir une PR de synchronisation dans `omni-agents-framework` qui
   remplace le dossier par un pointeur vers le nouveau dépôt.
