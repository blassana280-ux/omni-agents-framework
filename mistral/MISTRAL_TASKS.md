# MISTRAL — tâches et objectifs en cours

## En attente de décision (Lassana décide)
- T-001 : 37 PRs de réparation AGENTS.md ouvertes le 31/10/2026 (9 restaurations + 28 rafraîchissements) — à relire puis fusionner par Lassana. Les branches par défaut restent « injected » jusque-là.
- T-002 : omni-agents-framework — conflit potentiel PR #3 (orchestrateur) vs PR #4 (AGENTS.md) : fusionner l'une puis rébase l'autre. La PR #5 (miroir MISTRAL) ne touche aucun fichier existant : aucun conflit.

## Planifiées (MISTRAL)
- T-005 : explorer le connecteur scheduled_tasks pour des évaluations périodiques réelles (aucun faux automatisme).
- T-007 : premier cycle d'apprentissage complet (10 étapes) sur la prochaine tâche importante ; L-007 et L-008 consignées — mesure avant/après à re-vérifier.
- T-008 (issu de T-004) : auditer OmniRoute en détail (24 workflows, dont deploy-vps / docker-publish / electron-release / npm-publish) + lire les 8 workflows agency-agents restants.

## Terminé
- 04/11/2026 (2e session) — T-004 exécuté : audit sécurité CI/CD — ~120 workflows inventoriés (15 dépôts avec workflows), 8 workflows lus intégralement ; verdict 0 CRITICAL / 2 MEDIUM / 3 LOW + 1 point de fiabilité ; rapport [audit-securite.md](audit-securite.md). Réserve : forks non indexés par la recherche GitHub.
- 04/11/2026 (2e session) — T-006 exécuté : benchmarks 1, 5, 6 → PASS avec preuves ([benchmarks.md](benchmarks.md)) ; benchmark 7 couvert par T-004. Mode réel = adoption de profils (pas de runtime externe).
- 04/11/2026 (2e session) — Miroir synchronisé : commit e8b4ca0 (4 fichiers v0.1.2) sur mistral/init-v0.1.0, PR #5 à jour ; contenu distant re-relu (L-008 : vérification via Additional content).
- 04/11/2026 — Intégration skills GitHub : inventaire 50 dépôts, skill Vibe mes-skills-github créé, 5 nouvelles collections intégrées (voir [changelog.md](changelog.md) v0.1.2).
- 03/11/2026 — T-003 résolu : miroir GitHub hébergé en dossier mistral/ de omni-agents-framework (9 fichiers MISTRAL_*.md, branche mistral/init-v0.1.0, commit b0319e0, PR #5) ; create_repository re-testé (403 confirmé stable). Un dépôt dédié reste possible si Lassana le crée manuellement.
- 31/10/2026 — audit des 41 dépôts publics + réparation OmniBrain complète (37 dépôts, 37 PRs) — voir [memory.md](memory.md) section B et [changelog.md](changelog.md).
- 31/10/2026 — création du dossier Knowledge « Mission MISTRAL » (structure v0.1.0 opérationnelle).
