# MISTRAL — benchmarks de validation

Chaque test : méthode, critère de succès, résultat daté, preuve. Jamais de résultat déclaré sans preuve ; comparaison dans le temps.

| # | Test | Méthode | État (v0.1.0, 31/10/2026) |
|---|---|---|---|
| 1 | Récupération mémoire après nouvelle session | nouvelle session → protocole de démarrage → citer l'état réel chargé | **PASS (04/11/2026)** — session 2 : protocole exécuté (KNOWLEDGE.md + 4 fichiers), état réel cité avant action (miroir b0319e0, PR #5, 403) ; mémoire §B vérifiée et corrigée (50 dépôts vs 44 en mémoire) |
| 2 | Conservation des connaissances | retrouver un fait ancien (ex. empreintes OmniBrain) via [memory.md](memory.md) | OPÉRATIONNEL (fichier créé, contenu vérifié) |
| 3 | Apprentissage après erreur | après une erreur, une leçon L-xxx existe et change la méthode | OPÉRATIONNEL (L-001 : auto-test sha256 appliqué 7+ fois) |
| 4 | Réutilisation d'une compétence | ré-exécuter un workflow validé (verrou d'empreinte) | OPÉRATIONNEL (37 dépôts avec le même workflow) |
| 5 | Délégation à un agent GitHub | routage catalogue → adoption de profil → livrable structuré | **PASS (04/11/2026)** — audit sécurité : catalogue → security-senior-secops (security/security-senior-secops.md lu sur GitHub) → profil adopté → rapport structuré (sévérités, SLA, fixes) : [audit-securite.md](audit-securite.md) |
| 6 | Collaboration entre agents | escouade : 2+ profils croisés + vérification indépendante | **PASS (04/11/2026)** — profil #1 secops (constats) + profil #2 appsec (revue adverse) : chaque constat re-vérifié contre les fichiers lus, 1 point ajouté par la revue, 0 constat invalidé — mode adoption de profils (pas de runtime externe) |
| 7 | Détection de vulnérabilités | audit sécurité : workflows, secrets, dépendances | **PASS (04/11/2026)** — T-004 : 0 CRITICAL / 2 MEDIUM / 3 LOW ; réserve forks non indexés documentée : [audit-securite.md](audit-securite.md) |
| 8 | Résolution d'un problème de programmation | implémentation + tests | OPÉRATIONNEL (sha256 en TypeScript pur auto-testé ; composition AGENTS.md vérifiée) |
| 9 | Vérification indépendante d'une réponse | verrou d'empreinte avant/après poussée, relecture des tailles | OPÉRATIONNEL (37/37 branches conformes au plan) |
| 10 | Retour arrière après modification défectueuse | git revert/rebase via branche, jamais main | PROCÉDURE PRÊTE (non déclenchée — aucune défectuosité à ce jour) |

Historique : v0.1.0 (31/10/2026) — état initial consigné. v0.1.2 (04/11/2026) — tests 1, 5, 6, 7 → PASS avec preuves ; restent à exécuter : aucun (test 10 : procédure prête, jamais déclenchée).
