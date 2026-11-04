# MISTRAL — audit sécurité CI/CD (T-004), exécuté le 04/11/2026

Auditeur : profil **Senior SecOps Engineer** (agency-agents/security/security-senior-secops.md, adopté). Revue adverse : profil **security-appsec-engineer** (2e profil, vérification indépendante de chaque constat).
Périmètre : workflows GitHub Actions des 50 dépôts (46 publics + 4 privés). Méthode : recherche de motifs (pull_request_target, write-all, secrets:inherit, ghp_, AKIA, MISTRAL_API_KEY) + lecture intégrale des 8 workflows les plus critiques + inventaire des dossiers .github/workflows.

## Verdict global
- **0 CRITICAL · 2 MEDIUM · 3 LOW · 1 point de fiabilité** — aucun secret exposé, aucun pull_request_target, aucune permission write-all.
- Réserve d'honnêteté : l'index de recherche GitHub **n'indexe pas les forks sans étoiles** — les « aucun résultat » des recherches ne prouvent rien pour le contenu des forks ; seuls les fichiers lus font foi. ~100 workflows amont non lus (OmniRoute 24, kilocode 35, opencode 22, Red-DiscordBot 10, agency-agents 8).

## Constats

### F1 [MEDIUM, SLA 1 semaine] — Fusion automatique quotidienne d'un dépôt tiers sur main, sans revue
- **Localisation** : agency-agents/.github/workflows/sync-upstream.yml — jobs « Fusion amont (auto, fallback -X ours) » puis « Push du resultat » → `git push origin main` sur cron `30 6 * * *`.
- **Risque concret** : si l'amont msitarzewski/agency-agents est compromis, son contenu atterrit automatiquement sur main sans revue humaine — et daily-maintenance.yml **exécute ensuite les scripts du dépôt** (node scripts/agent-health.mjs, bash scripts/*.sh) : le code amont fusionné le matin s'exécute le jour même.
- **Fix** : (a) remplacer le push direct par une PR automatique (`gh pr create`) fusionnée après scan gitleaks/semgrep bloquant, ou (b) ajouter un job de scan sécurité bloquant avant le push.

### F2 [MEDIUM, SLA 1 semaine] — cf100-ci.yml sans bloc permissions explicite
- **Localisation** : omni-agents-framework/.github/workflows/cf100-ci.yml — aucun bloc `permissions:` → hérite des défauts du dépôt/token.
- **Risque** : si le défaut est permissif, le job a plus de droits que nécessaire (principe du moindre privilège violé).
- **Fix** : ajouter `permissions: contents: read` au niveau workflow.
- Atténuant : déclencheurs sûrs (schedule + push/PR filtrés par chemins, pas de pull_request_target).

### F3 [LOW] — Actions épinglées par tag, non par SHA
- Tous les workflows lus : `actions/checkout@v4`, `setup-python@v5`, etc. Tags mutables.
- **Fix** : épingler par SHA de release, en priorité pour toute action tierce. Faible ici (actions officielles uniquement).

### F4 [LOW] — daily-maintenance.yml : commits automatiques directs sur main
- Étape 7 : commit + `git push origin "$GITHUB_REF_NAME"` (main) quotidien ; étape 8 : `--force-with-lease` sur branche renforcement (PR jamais fusionnée auto — conforme).
- Choix de design documenté (rapports versionnés). Contourne la doctrine « jamais main » : à assumer explicitement ou déplacer en PR auto.

### F5 [LOW] — antigravity-skills ci.yml : GITHUB_TOKEN dans une URL git (run:)
- `git remote set-url origin https://x-access-token:${{ secrets.GITHUB_TOKEN }}@...` — risque de fuite en log en cas d'erreur git (masqué par GitHub par défaut). Guarded `push` + `main` only. LOW.
- **Fix** : credential helper / `GH_TOKEN` dans l'environnement.

### F6 [FIABILITÉ] — Deux workflows concurrents à 06:30 sur le même dépôt (revue adverse)
- daily-maintenance.yml et sync-upstream.yml partagent le cron `30 6 * * *` ; le premier fait `git pull --rebase` + push sur main pendant que le second pousse aussi sur main → concurrence possible (rebase conflicts, runs rouges ponctiques).
- **Fix** : décaler sync-upstream à `30 7 * * *`.

## Points sains (preuves)
- Permissions explicites et restreintes dans agency-agents (contents/issues/PR write), gamedev ci.yml (`contents: read`), pages.yml (`pages: write` + `id-token: write` — standard Pages).
- MISTRAL_API_KEY : uniquement via `${{ secrets.* }}`, jamais affiché, avec garde d'absence (étape ignorée si absent).
- Aucun secret codé en dur dans les fichiers lus ; ghp_/AKIA : 0 résultat dans l'index (réserve forks ci-dessus).
- Forks (Red-DiscordBot, kilocode, opencode, OmniRoute…) : les secrets amont ne se copient pas dans un fork — les workflows de publication n'ont d'effet que si des secrets y sont ajoutés manuellement.

## Revue indépendante (profil #2 — appsec, mode adverse)
- F1 confirmé : l'exécution différée des scripts du dépôt par daily-maintenance aggrave bien le risque de supply chain. Accord.
- F2 confirmé : absence du bloc permissions vérifiée dans le contenu lu. Accord.
- F3/F5 confirmés LOW avec atténuantes (actions officielles, masquage par défaut du token). Accord.
- Point ajouté par la revue : F6 (cron concurrents) — fiabilité plus que sécurité, validé contre les deux fichiers lus.
- Aucun constat de la passe 1 invalidé.

## Suite recommandée (priorité)
1. Auditer OmniRoute en détail (24 workflows dont deploy-vps.yml, docker-publish, electron-release, npm-publish — sensibles si secrets VPS/NPM attachés).
2. Appliquer F1, F2, F6 (fixes ci-dessus, chacun = 1 commit + 1 PR).
3. Lire les 8 workflows agency-agents restants (lint-agents, regen-manifest, repair-ci, check-tools…).
