# 🔐 Sécurité des clés API — OmniRouteLite (ADR-SEC-KEYS)

**Objectif** : connecter un fournisseur (ex. Mistral) sans jamais exposer de clé — ni dans le dépôt GitHub, ni dans les commits, ni dans les logs, ni dans une conversation.

## Ordre de résolution d'une clé (server.js et cli.js, identiques)

1. `apiKeyEnv` — variable d'environnement (ex. `MISTRAL_API_KEY`) ;
2. `apiKeyFile` — fichier local `secrets/<provider>.key` (chmod 600, dossier 700) ;
3. `apiKey` en clair dans config.json — hérité pour compatibilité, **déconseillé**.

La clé n'est **jamais** affichée ni journalisée : seuls son empreinte sha256 (12 premiers caractères) et son mode de résolution sont imprimés.

## Saisie sécurisée depuis Android (Termux)

```bash
pkg install nodejs -y
cd omni-agents-framework/OmniRouteLite
cp config.example.json config.json

# Méthode A (recommandée) : stdin — la clé n'apparaît ni dans l'historique shell ni dans git
node cli.js providers --connect mistral
# → collez la clé (console Mistral → API Keys), appuyez sur Entrée

# Méthode B : variable d'environnement (attention : export reste dans l'historique Termux,
# préférez la méthode A ou C)
MISTRAL_API_KEY=<clé> node cli.js providers --connect mistral

# Méthode C : fichier importé depuis le presse-papiers / stockage
node cli.js providers --connect mistral --key-file /sdcard/Download/cle.txt
rm /sdcard/Download/cle.txt   # effacez la copie après import

# Vérification — gratuite (GET /v1/models uniquement, aucune inférence payante)
node cli.js providers --verify mistral

# Démarrage de la passerelle
node server.js   # ⚡ http://127.0.0.1:8787
```

## Ce que fait `--connect`

- valide la clé (non vide, sans espaces) ;
- écrit `secrets/<provider>.key` (chmod **600**, dossier 700) ;
- retire `apiKey` de `config.json` et y inscrit `apiKeyFile` à la place — **aucun secret dans un fichier versionné** (`secrets/` et `config.json` sont gitignorés) ;
- affiche l'empreinte sha256 (jamais la clé) et les permissions réelles du fichier.

## Ce que fait `--verify`

- appelle `GET <baseUrl>/v1/models` avec la clé (coût : **0 €** — aucune inférence) ;
- HTTP 200 → **CONNECTÉ** : liste des modèles disponibles ;
- HTTP 401/403 → clé invalide ou révoquée ;
- erreur réseau → aucune conclusion tirée sur la clé.

## États d'un fournisseur (à ne jamais confondre)

| État | Signification | Preuve |
|---|---|---|
| PRÉPARÉ | code + config prêts, aucune clé enregistrée | `--list` : « PRÉPARÉ » |
| CONFIGURÉ | clé enregistrée localement (env ou fichier 600), non encore testée | sortie de `--connect` |
| CONNECTÉ | authentification vérifiée contre l'API réelle (`--verify` → HTTP 200 + modèles) | sortie de `--verify` |
| TESTÉ | une complétion réelle effectuée (payante — uniquement sur autorisation explicite de Lassana) | réponse API + stats |

## Invariants

- Jamais de clé dans une conversation, un commit, un log ou un dépôt GitHub.
- `secrets/` et `config.json` ignorés par git (`.gitignore` à la racine).
- Permissions minimales : 600 sur le fichier de clé, 700 sur le dossier.
- Rotation de clé : relancer `--connect` (écrase le fichier) puis `--verify`.
- Aucune inférence payante sans autorisation explicite.
