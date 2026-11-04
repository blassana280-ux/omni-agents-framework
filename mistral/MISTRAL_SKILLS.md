# MISTRAL — compétences disponibles

## Compétences intégrées (environnement Vibe, vérifiées le 31/10/2026)
- Travail : rich-ui (visualisations, checklists), canvas / canvas-react (artefacts, apps React), doc-coauthoring, document-review, internal-comms, meeting-prep, stakeholder-translator, structured-extraction, challenge-my-thinking, deep-research, research-synthesis, decrypt-vpn-configs, knowledge-* (mémoire durable).
- **mes-skills-github** (créé 04/11/2026) : routage vers les collections de skills GitHub de Lassana (~20 dépôts, plusieurs milliers de skills) + lecture paresiveuse via l'app GitHub. C'est l'intégration opérationnelle des compétences externes.
- Connecteurs : github_app, slack, notion, linear, gmail, outlook, google_drive, google_calendar, sharepoint, box, stripe, bigquery, mistral_mcp, web_search, image_generation, uploads, file_system, scheduled_tasks (à explorer — tâche T-005).
- Capacité d'exécution : sandbox TypeScript (ES2015-ES2022, sans fs ni réseau direct), implémentations pures testables (sha256 et git blob sha-1 vérifiés octet par octet le 31/10/2026).

## Compétences à développer (feuille de route)
- Audit sécurité systématique (workflows GitHub, permissions, secrets, dépendances) — tâche T-004.
- Évaluations périodiques réelles via scheduled_tasks — tâche T-005.
- ~~Intégration profonde des collections de skills GitHub~~ **FAIT le 04/11/2026** via le skill `mes-skills-github` : routage par domaine + lecture paresseuse. Nouveaux dépôts intégrés ce jour : vibeship-spawner-skills (462 skills / 35 catégories), antigravity-skills (619 skills), skills-Claude-vid-o- (13 skills Remotion), gemini-skills, skills-open-IA, opencode, optimiser-mes-agents-IA (privé, désormais lisible).

## Routage agents/skills
Pour choisir un agent ou un skill : consulter le dossier Knowledge « Mes Agents IA (GitHub) » (catalogue-agents.md, catalogue-skills-externes.md, routages par tâche). Ne pas recréer ici ce qui y est déjà catalogué — ce fichier ne conserve que l'état et les gains propres à MISTRAL.
