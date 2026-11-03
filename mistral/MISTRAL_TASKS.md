# MISTRAL — tâches et objectifs en cours

## En attente de décision (Lassana décide)
- T-001 : 37 PRs de réparation AGENTS.md ouvertes le 31/10/2026 (9 restaurations + 28 rafraîchissements) — à relire puis fusionner par Lassana. Les branches par défaut restent « injected » jusque-là.
- T-002 : omni-agents-framework — conflit potentiel PR #3 (orchestrateur) vs PR #4 (AGENTS.md) : fusionner l'une puis rébase l'autre. La PR du miroir MISTRAL (dossier mistral/) ne touche aucun fichier existant : aucun conflit.

## Planifiées (MISTRAL)
- T-004 : audit sécurité des 41 dépôts publics — workflows GitHub (permissions, pull_request_target), secrets exposés, dépendances ; rapport à produire.
- T-005 : explorer le connecteur scheduled_tasks pour des évaluations périodiques réelles (aucun faux automatisme).
- T-006 : exécuter les benchmarks 1, 5 et 6 (voir MISTRAL_BENCHMARKS.md) lors de la première nouvelle session — récupération mémoire, délégation, collaboration.
- T-007 : premier cycle d'apprentissage complet (10 étapes) sur la prochaine tâche importante ; consigner L-007 et suivantes dans MISTRAL_LEARNINGS.md.

## Terminé
- 03/11/2026 — T-003 résolu : miroir GitHub hébergé en dossier mistral/ de omni-agents-framework (branche mistral/init-v0.1.0 + PR, jamais main). create_repository re-testé : 403 confirmé stable. Un dépôt dédié reste possible si Lassana crée le dépôt manuellement (contenu déplaçable par branche + PR).
- 31/10/2026 — audit des 41 dépôts publics + réparation OmniBrain complète (37 dépôts, 37 PRs) — voir MISTRAL_MEMORY.md section B et MISTRAL_CHANGELOG.md.
- 31/10/2026 — création du dossier Knowledge « Mission MISTRAL » (structure v0.1.0 opérationnelle).
