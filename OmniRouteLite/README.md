# ⚡ OmniRouteLite — passerelle IA multi-fournisseurs, zéro dépendance

Passerelle d'API IA **réellement fonctionnelle**, inspirée d'OmniRoute, qui tourne telle quelle sur **PC (Windows/macOS/Linux)** et sur **Android (Termux)** — et dont le dashboard s'ouvre dans n'importe quel navigateur, y compris celui de votre téléphone.

**Aucune dépendance npm. Node.js ≥ 18 suffit.**

## ✨ Fonctionnalités

| Fonction | Détail |
|---|---|
| API compatible OpenAI | `POST /v1/chat/completions` — vos outils existants pointent dessus sans modification |
| Multi-fournisseurs | Mistral, OpenAI, Groq, OpenRouter, Anthropic (adaptateur natif), ou tout endpoint compatible OpenAI |
| Routage | `priority` (ordre déclaré, fallback automatique) ou `round-robin` |
| Cache de réponses | Clé normalisée (tolère les différences d'espacement), TTL configurable → vraie économie de tokens |
| Compression de prompt | Normalisation lossless des messages, tokens économisés comptés |
| Dashboard web | Stats live, santé par provider, testeur de prompt intégré |
| Sécurité | Clé gateway optionnelle (Bearer), écoute par défaut sur `127.0.0.1` |
| Mode `mock` | Fournisseur intégré pour tester sans aucune clé API |

## 🚀 Démarrage

```bash
cp config.example.json config.json   # ajoutez vos clés API
node server.js                       # ⚡ OmniRouteLite sur http://127.0.0.1:8787
```

Ouvrez `http://127.0.0.1:8787` → dashboard.

### Android (Termux)

```bash
pkg install nodejs -y
# copiez le dossier du projet, puis :
node server.js
# dashboard sur le téléphone : http://127.0.0.1:8787
# ou depuis un autre appareil du réseau : HOST=0.0.0.0 node server.js
```

### PC : accès depuis le téléphone

```bash
HOST=0.0.0.0 OMNILITE_KEY=une-cle-secrete node server.js
# puis http://<ip-du-pc>:8787 sur le téléphone (définissez une gatewayKey !)
```

## 🔌 Utilisation (compatible OpenAI)

```bash
curl http://127.0.0.1:8787/v1/chat/completions \
  -H "content-type: application/json" \
  -H "authorization: Bearer votre-cle-gateway" \
  -d '{"model":"mistral-large-latest","messages":[{"role":"user","content":"Bonjour !"}]}'
```

Endpoints : `POST /v1/chat/completions` · `GET /v1/models` · `GET /stats` · `GET /health`

## ✅ Tests

```bash
node test.js   # 8 tests E2E : auth, validation, routage, cache, compression, round-robin…
```

## ⚙️ Configuration (`config.json`)

Voir [config.example.json](config.example.json) : providers (`type: openai | anthropic | mock`), `routing.strategy`, `cache`, `compression`, `gatewayKey`, `host`, `port`. Variables d'environnement : `PORT`, `HOST`, `OMNILITE_KEY`, `OMNILITE_CONFIG`.

## 📐 Architecture (ADR-001)

Mono-serveur modulaire : `core.js` (logique pure, testable) + `server.js` (HTTP, fallback, cache) + `public/index.html` (dashboard). **Trade-off assumé** : pas de streaming SSE ni de persistance disque dans ce MVP — décisions réversibles, extension simple par provider.

## 📄 Licence

MIT — inspiré du projet open-source [OmniRoute](https://github.com/diegosouzapw/OmniRoute) (construit dans le cadre du dépôt [agency-agents](https://github.com/blassana280-ux/agency-agents) de blassana280-ux).
