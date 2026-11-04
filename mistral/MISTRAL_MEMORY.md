# MISTRAL — mémoire durable (4 couches)

Mise à jour à chaque apprentissage validé. Honnêteté : ce dossier est auto-affiché à chaque session (déclencheur) ; le présent fichier est lu via le protocole de démarrage du KNOWLEDGE.md.

## A. Mémoire utilisateur
- Utilisateur : Lassana Bah, compte GitHub blassana280-ux, fuseau Bamako (UTC+0).
- Langue : français. Style : réponses concises et denses, économie de tokens (doctrine du dossier « Mes Agents IA (GitHub) »).
- Organisation du travail : branche + PR, jamais main, jamais de fusion automatique, preuve fraîche obligatoire ; mode escouade piloté par OmniBrain pour les tâches complexes, agent unique pour les tâches simples.

## B. Mémoire technique (état vérifié le 31 octobre 2026)
- Compte GitHub (vérifié 04/11/2026) : **50 dépôts uniques = 46 publics + 4 privés** (optimiser-mes-agents-IA, omni-agents-fraworks, mon-app-de-m-t-o-en-temps-r-el, **omni-research-100** — nouveau, quasi vide). CHANGEMENT MAJEUR : les dépôts privés sont désormais **LISIBLES** par l'app GitHub (get_file_contents réussit sur optimiser-mes-agents-IA et omni-research-100 le 04/11/2026) — le 403 du 31/10 n'est plus d'actualité pour la lecture. Le stockage MISTRAL reste public et sans secret par principe.
- Nouveaux dépôts skills découverts le 04/11/2026 (absents de l'inventaire d'octobre) : vibeship-spawner-skills (462 skills / 35 catégories, index SKILLS_DIRECTORY.md), skills-Claude-vid-o- (13 skills Remotion), gemini-skills (4 skills Gemini API), skills-open-IA, opencode (plateforme agentique), omni-research-100 (privé). Comptage vérifié : antigravity-skills = 619 entrées dans skills/.
- blassana280-ux/omni-agents-framework : source de vérité OmniBrain. PR #3 (orchestrateur, 42 fichiers, commit 7c69c52) et PR #4 (rafraîchissement AGENTS.md) ouvertes — conflit potentiel sur AGENTS.md à la fusion (fusionner une puis rébase l'autre).
- Réparation OmniBrain du 31/10/2026 : 37 dépôts réparés (9 restaurations d'AGENTS.md upstream + 28 rafraîchissements d'overlay), chacun 1 branche omnibrain/agents-md-* + 1 commit + 1 PR ouverte, empreintes sha256 vérifiées avant poussée, tailles re-vérifiées après. Les branches par défaut restent « injected » (1682 octets, blob 3116c8cadc…) tant que les PRs ne sont pas fusionnées.
- agentskills : branche arena/265447fb-agentskills = code de réparation (omni/overlays.py ; overlay = 1532 octets, sha256 préfixe 0b721cdd59ec3dd6).
- agency-agents : ~190 agents, 18 divisions ; maintenance quotidienne autonome réelle (GitHub Actions .github/workflows/daily-maintenance.yml, 06:30 Bamako) + renforcement de 10 agents/jour via API Mistral (PRs labellisées renforcement-quotidien, jamais fusionnées automatiquement).
- Branches par défaut particulières : OmniRoute → release/v3.8.50 ; Red-DiscordBot → V3/develop ; LMCache → dev ; skills-collection, minimind, 9router → master ; les autres → main.
- Dépôts publics sans AGENTS.md : vpn-decryptor, minimind, 9router (rien à réparer).
- L'app GitHub **ne peut pas créer de dépôt** (403, testé 31/10/2026 puis re-testé 03/11/2026 — stable) ; elle peut créer branches, commits (push_files) et PRs.
- Miroir GitHub MISTRAL : dossier mistral/ de omni-agents-framework (9 fichiers MISTRAL_*.md, branche mistral/init-v0.1.0, commit b0319e0, PR #5 ouverte le 03/11/2026 — fusion par Lassana).

## C. Mémoire expérimentelle
Voir [learnings.md](learnings.md) — leçons L-001 à L-005 (crypto auto-testée, 502 masquants, limites de débit, non-déterminisme du fetch web, budgets d'exécution).

## D. Mémoire procédurale (workflows validés)
- Poussée GitHub fiable : vérifier l'état réel AVANT d'agir (list_branches, list_pull_requests) ; écrire en série, jamais en rafale parallèle (limite de débit secondaire GitHub) ; lots de 2-4 dépôts ; après un 502, vérifier si l'écriture a réussi malgré l'erreur ; traiter « already exists » comme un succés.
- Contenu critique : verrou d'empreinte (taille + sha256 attendues) AVANT toute poussée ; re-vérifier la taille sur la branche APRÈS.
- Cryptographie : toute implémentation (sha256, git blob sha-1) est auto-testée sur vecteurs connus AVANT usage.
- Budget d'exécution : ~60 s par exécution sandbox, écho d'outill < ~90 Ko, fetch + compose + verify + push dans la MÊME exécution (aucun état entre exécutions) ; reprise idempotente sur l'état réel après tout arrêt.
- Composition AGENTS.md : upstream.rstrip() + deux retours à la ligne + overlay (1533 octets) — conforme à omni/overlays.py (branche arena).
- Synchronisation miroir exacte : le contenu poussé passe par **base64 local → décodage sandbox** (décodeur pur auto-testé sur vecteurs connus), jamais par transcription manuelle (source d'un écart d'1 octet constaté le 04/11/2026, L-009) ; verrou final = taille GitHub == taille locale après poussée.
