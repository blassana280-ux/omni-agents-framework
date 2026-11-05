# ⚡ OmniRoute Mobile — la passerelle IA d'OmniRoute, native sur Android

Version Android du concept [OmniRoute](https://github.com/diegosouzapw/OmniRoute) (v3.8.50) : **le téléphone devient une passerelle IA** compatible OpenAI, avec fallback multi-providers, cache, compression et dashboard — **app native Kotlin, zéro dépendance externe** (org.json et HttpURLConnection sont intégrés à Android).

## 🔬 Analyse du vrai OmniRoute (base de ce portage)

Le dépôt original est un monolithe **Node.js ≥ 22 + Next.js 16 + React 19 + Electron** (~340 providers, compression RTK+Caveman par modèles ONNX, MCP/A2A, inspecteur MITM, PWA, cli de 500+ scripts). **Node.js 22 ne tourne pas nativement sur Android** — un portage direct est impossible. Ce projet porte donc le **cœur de la valeur d'OmniRoute** en natif :

| Fonctionnalité OmniRoute (v3.8.50) | OmniRoute Mobile v1 |
|---|---|
| API compatible OpenAI (`/v1/chat/completions`) | ✅ identique |
| Auto-fallback multi-providers | ✅ priority + round-robin |
| Mistral / OpenAI / Groq / OpenRouter (dialecte OpenAI) | ✅ |
| Anthropic (Messages API) | ✅ adaptateur natif de conversion |
| Cache de réponses | ✅ clé normalisée + TTL |
| Compression de prompt | ✅ lossless (normalisation des blancs) — pas le RTK+Caveman complet (nécessite ONNX) |
| Dashboard | ✅ UI Compose : stats live, santé providers, testeur |
| Provider sans clé pour tester | ✅ type `mock` intégré |
| Catalogue 340 providers, MITM, MCP/A2A, SSE streaming | ❌ hors périmètre v1 |

## 📱 Ce que fait l'app

1. **UI native** (Jetpack Compose) : démarrer/arrêter la passerelle, stats live (requêtes, cache hits, tokens in/out, tokens économisés), santé par provider, testeur de prompt, éditeur de config JSON
2. **Serveur HTTP local compatible OpenAI** sur `http://<ip-du-téléphone>:8787` — utilisable depuis un PC, Termux, ou un autre téléphone du réseau local :
   - `POST /v1/chat/completions` (Bearer si `gatewayKey` définie)
   - `GET /v1/models` · `GET /stats` · `GET /health`
3. **Pipeline par requête** : cache → compression → routage fallback → provider → stats
4. **Clés API stockées uniquement sur le téléphone** (SharedPreferences privé), jamais sur GitHub

## 🔨 Build (5 minutes)

1. Installer [Android Studio](https://developer.android.com/studio) (PC)
2. `git clone` ce dépôt, ouvrir le dossier `OmniRouteMobile`
3. Laisser Gradle synchroniser (le wrapper est généré à l'ouverture), puis **Build → Build APK**
4. Installer l'APK sur le téléphone (ou brancher en USB et utiliser Run)

**Sans PC :** Termux peut compiler le projet (`pkg install openjdk-17 git && git clone … && ./gradlew assembleDebug`), mais Android Studio reste la voie simple.

## ✅ Vérification

- Logique pure (compression, clés de cache, routage priority/round-robin, adaptateur Anthropic) : **exécutée et validée** avant portage (mêmes algorithmes que ceux validés dans la phase OmniRouteLite)
- Sur Android : sans aucune clé, le provider `mock` répond → « Démarrer », envoyer un message avec `model: mock-1`, le dashboard affiche les stats et `omniroute.cached: true` au 2ᵉ envoi identique
- Limitation honnête : le code Kotlin n'a pas pu être compilé dans l'environnement de création (pas de SDK Android) — le build Android Studio est l'étape de vérification finale

## 🧱 Architecture (ADR-002)

```
app/src/main/java/com/blassana/omniroutemobile/
├── MainActivity.kt          # UI Compose (dashboard + testeur + config)
└── core/
    ├── OmniCore.kt           # logique pure : hash, compression, cache, routage, adaptateurs
    ├── Config.kt             # config JSON (SharedPreferences), Provider/AppConfig
    ├── ProviderClient.kt    # appels HTTP (openai-compatible | anthropic)
    ├── Gateway.kt           # moteur : cache → compression → fallback → stats
    └── GatewayServer.kt     # serveur HTTP brut (ServerSocket), zéro dépendance
```

Choix : pas de service en avant-plan en v1 (la passerelle vit pendant que l'app est ouverte) — extension naturelle : `ForegroundService` pour un fonctionnement en arrière-plan.

## 📄 Licence

MIT — inspiré de [OmniRoute](https://github.com/diegosouzapw/OmniRoute) de diegosouzapw. Construit par l'escouade agency-agents de blassana280-ux.
