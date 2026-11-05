# Mission CONNECT MISTRAL — état réel (session du 05/11/2026, agent VIDE)

Mission : connecter réellement le fournisseur Mistral AI à l'écosystème OmniBrain, sans exposer aucune clé API. Reprise du travail « Arena ». Cette fiche est le point de continuité : toute session future la relit d'abord.

## 1. Audit (Phase 1) — constats vérifiés le 05/11/2026

- **« OmniBrain SUPREME 1.3.0 » : INTROUVABLE.** Recherche code `SUPREME` / `MISTRAL_API_KEY_FILE` / `"providers --connect"` sur le compte : 0 résultat (index GitHub, branche par défaut uniquement — réserve : forks non indexés). Aucune branche, PR ou fichier ne porte ce nom. La version citée dans la mission n'existe pas dans le dépôt : l'intégration vise donc le système **réel** existant.
- **PR #5** ([miroir MISTRAL v0.1.0](https://github.com/blassana280-ux/omni-agents-framework/pull/5)) : FUSIONNÉE le 04/11/2026 — c'est le miroir de configuration MISTRAL EVOLUTION MAX, pas un système de providers. Dernières sync : PR #9 (v0.1.4) et PR #10 (v0.1.5), fusionnées.
- **Système de gestion des fournisseurs réel** : `OmniRouteLite/` (passerelle Node zéro dépendance, PR #1 fusionnée) — providers dans `config.json` dont `mistral` (baseUrl `https://api.mistral.ai`), mais clé en clair dans le JSON et **aucune** commande `providers`, ni `MISTRAL_API_KEY`, ni `MISTRAL_API_KEY_FILE` supportés. `OmniRouteMobile/` : app Android Kotlin (clés en SharedPreferences privé).
- **Éléments déjà fonctionnels (non réécrits)** : routage priority/round-robin, fallback, cache, compression, dashboard, adaptateur anthropic, provider mock, 8 tests E2E (`test.js`).

## 2. Intégration sécurisée livrée (Phase 2) — branche `feature/mistral-connect-securise`

- **`cli.js` (nouveau)** : `node cli.js providers --list | --connect <nom> | --verify <nom>` — enregistre la clé dans `secrets/<provider>.key` (chmod 600, dossier 700), la retire de `config.json` (remplacée par `apiKeyFile`), ne l'affiche jamais (empreinte sha256 seulement). Sources acceptées : stdin (recommandé Termux), `--key-file`, `apiKeyEnv` (`MISTRAL_API_KEY`), `MISTRAL_API_KEY_FILE`.
- **`server.js`** : résolution de clé `apiKeyEnv > apiKeyFile > apiKey` (`resolveApiKey`), jamais d'affichage. Compatibilité ascendante conservée.
- **`config.example.json`** : provider mistral migre vers `apiKeyEnv`+`apiKeyFile` (plus de clé en clair).
- **`.gitignore`** : `OmniRouteLite/secrets/`, `config.json`, `config.test.json` ignorés.
- **`OmniRouteLite/SECURITY-KEYS.md`** : procédure Android/Termux complète + les 4 états.

## 3. Connexion réelle (Phase 3) — À FAIRE par Lassana (impossible depuis Vibe)

Le sandbox Vibe n'a **pas accès au réseau brut ni au système de fichiers de l'appareil** : l'enregistrement de la clé et la vérification ne peuvent être exécutés que sur l'appareil (Android/Termux ou PC). Procédure exacte dans SECURITY-KEYS.md § « Saisie sécurisée depuis Android ». Résumé :

1. `node cli.js providers --connect mistral` (coller la clé) → état CONFIGURÉ ;
2. `node cli.js providers --verify mistral` (gratuit) → état CONNECTÉ + liste des modèles réels du compte ;
3. choisir le modèle (voir § 5) puis autoriser explicitement une complétion de test → état TESTÉ.

## 4. Tarifs — à re-vérifier sur docs.mistral.ai avant tout budget

Les prix évoluent : toujours re-vérifier la page officielle des tarifs avant tout engagement. Les chiffres de la session du 05/11/2026 figurent dans le rapport de conversation (voir PR de cette branche).

## 5. Recommandation modèle

À l'état CONNECTÉ, la sortie de `--verify` liste les modèles réellement accessibles au compte. Recommandation par défaut : **mistral-small-latest** pour l'usage routine (économie), **mistral-large-latest** pour les tâches complexes OmniBrain — à trancher sur la liste réelle du compte.

## 6. Règles permanentes

- Aucune clé dans GitHub/commits/logs/conversations ; secrets gitignorés ; chmod 600.
- Jamais d'inférence payante sans autorisation explicite de Lassana.
- Jamais d'écriture directe sur main : branche + PR, fusion par Lassana.
- Ne jamais prétendre qu'un état CONNECTÉ/TESTÉ est atteint sans sortie de commande réelle.
