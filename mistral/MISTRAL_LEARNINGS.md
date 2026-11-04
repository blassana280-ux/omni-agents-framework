# MISTRAL — apprentissage continu

## Protocole (après chaque tâche importante)
1. Analyser la stratégie. 2. Évaluer le résultat avec preuve. 3. Identifier les erreurs. 4. Trouver les causes racines. 5. Extraire les connaissances. 6. Enregistrer la leçon ici (ligne L-xxx suivante). 7. Corriger la méthode dans [memory.md](memory.md) section D si procédurale. 8. Tester la correction à la prochaine occasion. 9. Mesurer avant/après. 10. Conserver uniquement les améliorations validées — sinon revenir à la version précédente (git pour le miroir GitHub, historique de fichiers pour ce dossier).

## Rubrique d'évaluation (par tâche)
Résultat (atteint/partiel/échec) · Preuve · Erreurs · Leçon · Méthode changée (oui/non) · À re-vérifier.

## Leçons enregistrées

### L-001 — Auto-tester toute implémentation cryptographique (31/10/2026)
Erreur : constante sha256 transcrite 0x06990624 au lieu de 0xd6990624 — empreintes fausses, 4 actions bloquées à tort (faux négatifs).
Cause : transcription manuelle d'une table de constantes.
Correction : auto-test systématique sur vecteurs connus AVANT toute décision fondée sur un hash. Appliqué comme garde-fou dans chaque exécution depuis.
Statut : validé (7+ exécutions ultérieures conformes).

### L-002 — Un 502 GitHub peut masquer une écriture réussie (31/10/2026)
Erreur : 7 créations de branches « échouées » en 502 étaient en réalité réussies côté serveur.
Cause : erreur proxy asynchrone — le code HTTP ne reflète pas toujours l'état final.
Correction : après toute erreur d'écriture, vérifier l'état réel (list_branches / list_pull_requests) avant de réessayer ; traiter « already exists » comme un succès. Zéro doublon créé grâce à cette vérification.
Statut : validé.

### L-003 — Écritures GitHub en série, jamais en rafale parallèle (31/10/2026)
Erreur : 7 chaînes d'écriture parallèles — 502 multiples + limite de débit secondaire GitHub.
Correction : écritures sérialisées, lots de 2-4 dépôts, reprise sur l'état réel. Les 21 dépôts suivants : aucun incident.
Statut : validé.

### L-004 — Ne jamais pousser de contenu issu d'un fetch non déterministe (31/10/2026)
Constat : le fetcher web (open_url) est non déterministe, insère des retours à la ligne aux frontières de chunks et tronque à ~32 000 caractères.
Correction : tout contenu poussé passe un verrou d'empreinte (taille + sha256 attendues) ; lecture de contenu de dépôt uniquement via l'API GitHub authentifiée.
Statut : préventif, validé sur 37 dépôts.

### L-005 — Budget 60 s par exécution, aucun état entre exécutions (31/10/2026)
Constat : deux exécutions ont dépassé le budget (une PR à reprendre manuellement) ; le sandbox ne conserve aucun état.
Correction : chaînes courtes (max 4 dépôts par série), fetch + compose + verify + push dans la même exécution, reprise idempotente sur l'état réel après tout arrêt.
Statut : validé.

### L-006 — Signaler un refus de permission comme blocage, jamais le maquiller (31/10/2026)
Constat : create_repository → 403 « Resource not accessible by integration ». L'app GitHub ne peut pas créer de dépôts.
Correction : mesurer l'erreur, la consigner (memory.md §B), construire ce qui est opérationnel sans cette permission (Knowledge = source durable), et proposer à Lassana les voies de déblocage. Ne jamais prétendre que le miroir GitHub existe.
Statut : appliqué — puis résolu le 03/11/2026 par hébergement en dossier mistral/ de omni-agents-framework (403 re-testé et confirmé stable ce jour-là).

### L-007 — La recherche GitHub exclut les forks par défaut ; l'accès privé évolue (04/11/2026)
Constat 1 : search_repositories "user:blassana280-ux" ne renvoyait que 5 dépôts — les forks sont exclus par défaut (il faut `fork:true` en second appel).
Constat 2 : les dépôts privés, illisibles (403) le 31/10, sont désormais lisibles par l'app GitHub (vérifié sur optimiser-mes-agents-IA et omni-research-100).
Correction : pour tout inventaire de compte, requêter fork:false ET fork:true puis dédupliquer ; re-tester les permissions supposées perdues à chaque session importante au lieu de se fier à une mémoire ancienne.
Statut : validé le 04/11/2026 (50 dépôts uniques dénombrés vs 44 en mémoire).

### L-008 — get_file_contents ne retourne pas le contenu dans la valeur sandbox (04/11/2026)
Constat : la valeur retournée dans le sandbox est une enveloppe « successfully downloaded text file (SHA: …) » de 81 caractères ; le contenu complet du fichier arrive en « Additional content » HORS sandbox. Une comparaison exacte in-sandbox échoue donc systématiquement (faux « non conforme »).
Correction : la vérification post-poussée se fait sur le contenu « Additional content » rapporté par l'outil (comparaison octet par octet hors sandbox), jamais sur la valeur de retour ; ne jamais conclure à une poussée ratée sur la seule valeur sandbox.
Statut : validé le 04/11/2026 (commit e8b4ca0 vérifié conforme via Additional content après faux négatif in-sandbox).

### L-009 — Transcrire un fichier à la main pour le pousser produit des erreurs d'1 octet (04/11/2026)
Constat : MISTRAL_CHANGELOG.md poussé avec 3528 octets vs 3529 locaux — contenu identique ligne à ligne mais 1 octet perdu ; CR, NBSP et espaces de fin exclus par vérification hexadécimale.
Cause : transcription manuelle du contenu du fichier dans le code sandbox (le seul chemin de transfert utilisé était la frappe).
Correction : pour toute synchronisation miroir, encoder le fichier local en base64 (bash), décoder en sandbox via un décodeur pur auto-testé sur vecteurs connus AVANT usage, pousser le contenu décodé ; verrou final = taille GitHub == taille locale (bash wc -c).
Statut : validé le 04/11/2026 (correctif poussé, tailles alignées 3529 = 3529).
