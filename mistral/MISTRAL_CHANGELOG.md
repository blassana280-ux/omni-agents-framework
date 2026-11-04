# MISTRAL — changelog

## v0.1.3 — 4 novembre 2026 (2e session)
- Miroir synchronisé : commit e8b4ca0 (MISTRAL_SKILLS/MEMORY/LEARNINGS/CHANGELOG v0.1.2) sur mistral/init-v0.1.0 — PR #5 à jour ; contenu distant re-relu (leçon L-008 : la vérification passe par le contenu « Additional content », la valeur sandbox ne contient pas le fichier).
- T-004 exécuté : audit sécurité CI/CD en mode escouade (profil secops + revue adverse appsec) — ~120 workflows inventoriés (15 dépôts avec workflows), 8 lus intégralement ; verdict 0 CRITICAL / 2 MEDIUM / 3 LOW + 1 fiabilité ; rapport mistral/audit-securite.md (rapport local : audit-securite.md). Réserve : forks non indexés par la recherche GitHub.
- T-006 exécuté : benchmarks 1, 5, 6, 7 → PASS avec preuves (benchmarks.md) — mode réel = adoption de profils, pas de runtime externe.
- T-008 créée : audit OmniRoute (24 workflows) + 8 workflows agency-agents restants.

## v0.1.2 — 4 novembre 2026
- Intégration des collections de skills GitHub : inventaire frais de 50 dépôts uniques (46 publics + 4 privés, recherche fork:false + fork:true dédupliquée) ; 5 nouveaux dépôts découverts (vibeship-spawner-skills 462 skills/35 catégories, skills-Claude-vid-o- 13 skills Remotion, gemini-skills, skills-open-IA, opencode) + omni-research-100 (privé, nouveau).
- Accès privé rétabli : get_file_contents réussit sur les dépôts privés (403 du 31/10 obsolète pour la lecture) — memory.md §B et learnings.md L-007 mis à jour.
- Création du skill Vibe `mes-skills-github` : routage par domaine vers ~20 collections de skills + protocole de lecture paresiveuse (get_file_contents, jamais open_url pour du contenu de dépôt). Feuille de route « intégration des collections » → terminée.
- Aucune écriture GitHub ce jour (aucune branche/PR) : travail de lecture + intégration locale uniquement.

## v0.1.1 — 3 novembre 2026
- create_repository re-testé : 403 « Resource not accessible by integration » confirmé stable.
- Miroir GitHub initialisé : dossier mistral/ de omni-agents-framework — 9 fichiers MISTRAL_*.md (23 572 octets), branche mistral/init-v0.1.0, commit b0319e0, PR #5 ouverte ; contenu relu intégralement via l'API authentifiée pour vérification. Aucun commit direct sur main, aucune fusion automatique.
- Inventaire des agents mis à jour (pièges outillage corrigés, section « Sync du 31 oct. 2026 »).

## v0.1.0 — 31 octobre 2026
- Audit complet de l'environnement GitHub : 44 dépôts (41 publics, 3 privés), état AGENTS.md vérifié sur les 41 publics le même jour.
- Création du dossier Knowledge « Mission MISTRAL » : KNOWLEDGE.md (identité + protocole de démarrage), memory.md (4 couches), skills.md, learnings.md (L-001 à L-006), architecture.md, tasks.md, agents-registry.md, benchmarks.md, changelog.md.
- Registre d'agents réel : disponibilité vérifiée statut honnête par entrée (profils lisibles vs services actifs — aucun service actife prétendu).
- 6 leçons issues de la mission OmniBrain du 31/10/2026 (dont L-006 : signalement du refus 403 de création de dépôt).
- 10 benchmarks définis : 5 opérationnels, 5 à vérifier (tests 1, 5, 6, 7).
- Miroir GitHub : BLOQUÉ (create_repository → 403 « Resource not accessible by integration ») — hébergement en attente de décision de Lassana ; le dossier Knowledge est la source opérationnelle.
- Contexte hérité : mission OmniBrain du 31/10/2026 — 37 dépôts réparés, 37 PRs ouvertes, 0 fusion.
