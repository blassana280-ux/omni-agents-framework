# MISTRAL — benchmarks de validation

Chaque test : méthode, critère de succès, résultat daté, preuve. Jamais de résultat déclaré sans preuve ; comparaison dans le temps.

| # | Test | Méthode | État (v0.1.0, 31/10/2026) |
|---|---|---|---|
| 1 | Récupération mémoire après nouvelle session | nouvelle session → protocole de démarrage → citer l'état réel chargé | MÉCANISME CRÉÉ (dossier Knowledge « Mission MISTRAL ») — à vérifier à la première nouvelle session |
| 2 | Conservation des connaissances | retrouver un fait ancien (ex. empreintes OmniBrain) via MISTRAL_MEMORY.md | OPÉRATIONNEL (fichier créé, contenu vérifié) |
| 3 | Apprentissage après erreur | après une erreur, une leçon L-xxx existe et change la méthode | OPÉRATIONNEL (L-001 : auto-test sha256 appliqué 7+ fois) |
| 4 | Réutilisation d'une compétence | ré-exécuter un workflow validé (verrou d'empreinte) | OPÉRATIONNEL (37 dépôts avec le même workflow) |
| 5 | Délégation à un agent GitHub | routage catalogue → adoption de profil → livrable structuré | PARTIEL (mode réel = adoption de profil ; pas de runtime externe) |
| 6 | Collaboration entre agents | escouade : 2+ profils croisés + vérification indépendante | PARTIEL (méthode définie, première exécution à venir) |
| 7 | Détection de vulnérabilités | audit sécurité : workflows, secrets, dépendances | NON ENCORE EXÉCUTÉ (tâche T-004) |
| 8 | Résolution d'un problème de programmation | implémentation + tests | OPÉRATIONNEL (sha256 en TypeScript pur auto-testé ; composition AGENTS.md vérifiée) |
| 9 | Vérification indépendante d'une réponse | verrou d'empreinte avant/après poussée, relecture des tailles | OPÉRATIONNEL (37/37 branches conformes au plan) |
| 10 | Retour arrière après modification défectueuse | git revert/rebase via branche, jamais main | PROCÉDURE PRÊTE (non déclenchée — aucune défectuosité à ce jour) |

Historique : v0.1.0 (31/10/2026) — état initial consigné ; tests 1, 5, 6, 7 à exécuter.
